import base64
import os
import re
import shutil
import time
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
import fitz

from database import get_db, init_db
from models import GeneratePdfRequest
from file_utils import (
    ensure_dirs, OUTPUT_DIR, UPLOAD_DIR
)
from services.pdf_generator import (
    MODULES_DIR, build_exam_pdf, build_answer_key_pdf, list_module_images,
    shutdown_browser,
)

app = FastAPI(title="IT Exam Manager", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    init_db()
    ensure_dirs()
    os.makedirs(os.path.join(UPLOAD_DIR, "modules"), exist_ok=True)


@app.on_event("shutdown")
async def shutdown():
    shutdown_browser()

@app.get("/api/health")
async def health():
    return {"status": "ok"}


ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def _format_ngay_thi(value: str) -> str:
    """Normalize ngay_thi (YYYY-MM-DD) -> DD/MM/YYYY for the templates."""
    if not value:
        return ""
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return value


def page_to_data_url(pdf_bytes: bytes, page_index: int) -> str:
    """Render a single PDF page to a Base64 JPEG data URL (for the frontend
    interactive cropper). Uses JPEG at 3x scale for fast network transfer."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        if page_index >= len(doc):
            raise HTTPException(status_code=400, detail=f"PDF has only {len(doc)} pages, cannot access page {page_index + 1}")
        page = doc[page_index]
        pix = page.get_pixmap(matrix=fitz.Matrix(3.0, 3.0))
        jpeg = pix.tobytes("jpeg")
        return "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()
    finally:
        doc.close()


@app.post("/api/modules/pages")
async def render_module_pages(
    exam_raw_pdf: UploadFile = File(None),
    answer_key_raw_pdf: UploadFile = File(None),
):
    """Render the pages the frontend cropper needs:
    exam pages 2-4 (Word/Excel/PPT previews) and answer key pages 1-3
    (Word/Excel/PPT rubrics)."""
    result = {}
    if exam_raw_pdf and exam_raw_pdf.filename:
        data = await exam_raw_pdf.read()
        result["exam"] = [page_to_data_url(data, i) for i in (1, 2, 3)]
    if answer_key_raw_pdf and answer_key_raw_pdf.filename:
        data = await answer_key_raw_pdf.read()
        result["answer"] = [page_to_data_url(data, i) for i in (0, 1, 2)]
    if not result:
        raise HTTPException(status_code=400, detail="Provide exam_raw_pdf and/or answer_key_raw_pdf")
    return result


ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


@app.post("/api/modules/ingest")
async def ingest_module(
    module_id: str = Form(...),
    exam_raw_pdf: UploadFile = File(...),
    answer_key_raw_pdf: UploadFile = File(...),
    word_assets: Optional[List[UploadFile]] = File(None),
    excel_raw_file: UploadFile = File(...),
    ppt_raw_file: UploadFile = File(...),
    word_preview: Optional[List[UploadFile]] = File(None),
    excel_preview: Optional[List[UploadFile]] = File(None),
    ppt_preview: Optional[List[UploadFile]] = File(None),
    word_rubric: Optional[List[UploadFile]] = File(None),
    excel_rubric: Optional[List[UploadFile]] = File(None),
    ppt_rubric: Optional[List[UploadFile]] = File(None),
):
    module_id = module_id.strip()
    if not module_id:
        raise HTTPException(status_code=400, detail="module_id is required")

    if not exam_raw_pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="exam_raw_pdf must be a .pdf file")
    if not answer_key_raw_pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="answer_key_raw_pdf must be a .pdf file")
    if not excel_raw_file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="excel_raw_file must be a .xlsx/.xls file")
    if not ppt_raw_file.filename.lower().endswith(".pptx"):
        raise HTTPException(status_code=400, detail="ppt_raw_file must be a .pptx file")

    db = get_db()
    try:
        existing = db.execute("SELECT id FROM modules WHERE module_id=?", (module_id,)).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail=f"module_id '{module_id}' already exists")
    finally:
        db.close()

    exam_bytes = await exam_raw_pdf.read()
    answer_bytes = await answer_key_raw_pdf.read()

    if len(exam_bytes) == 0:
        raise HTTPException(status_code=400, detail="exam_raw_pdf is empty")
    if len(answer_bytes) == 0:
        raise HTTPException(status_code=400, detail="answer_key_raw_pdf is empty")

    word_dir = os.path.join(MODULES_DIR, "word", module_id)
    excel_dir = os.path.join(MODULES_DIR, "excel", module_id)
    ppt_dir = os.path.join(MODULES_DIR, "ppt", module_id)
    module_root = os.path.join(MODULES_DIR, module_id)

    for d in [word_dir, excel_dir, ppt_dir, module_root]:
        os.makedirs(d, exist_ok=True)

    try:
        exam_pdf_path = os.path.join(module_root, exam_raw_pdf.filename)
        with open(exam_pdf_path, "wb") as f:
            f.write(exam_bytes)

        answer_pdf_path = os.path.join(module_root, answer_key_raw_pdf.filename)
        with open(answer_pdf_path, "wb") as f:
            f.write(answer_bytes)

        excel_bytes = await excel_raw_file.read()
        excel_path = os.path.join(excel_dir, "dlm_raw.xlsx")
        with open(excel_path, "wb") as f:
            f.write(excel_bytes)

        ppt_bytes = await ppt_raw_file.read()
        ppt_path = os.path.join(ppt_dir, "dlm.pptx")
        with open(ppt_path, "wb") as f:
            f.write(ppt_bytes)

        if word_assets:
            for asset in word_assets:
                asset_ext = Path(asset.filename).suffix.lower()
                if asset_ext in ALLOWED_IMAGE_EXTS:
                    asset_bytes = await asset.read()
                    asset_path = os.path.join(word_dir, asset.filename)
                    with open(asset_path, "wb") as f:
                        f.write(asset_bytes)

        crop_slots = [
            ("word_preview", word_dir, "preview"),
            ("excel_preview", excel_dir, "preview"),
            ("ppt_preview", ppt_dir, "preview"),
            ("word_rubric", word_dir, "rubric"),
            ("excel_rubric", excel_dir, "rubric"),
            ("ppt_rubric", ppt_dir, "rubric"),
        ]
        for field_name, target_dir, prefix in crop_slots:
            uploads: Optional[List[UploadFile]] = locals().get(field_name) or []
            for i, upload in enumerate(uploads):
                if not upload or not upload.filename:
                    continue
                if not upload.filename.lower().endswith(".png"):
                    raise HTTPException(status_code=400, detail=f"{field_name} must be a .png file")
                crop_bytes = await upload.read()
                # MULTI-CROP: each additional PNG for the same section gets an
                # incremented suffix so the PDF engine can stack them in order.
                save_name = f"{prefix}_{i}.png"
                with open(os.path.join(target_dir, save_name), "wb") as f:
                    f.write(crop_bytes)

    except HTTPException:
        raise
    except Exception as e:
        for d in [word_dir, excel_dir, ppt_dir, module_root]:
            if os.path.exists(d):
                import shutil
                shutil.rmtree(d, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")

    db = get_db()
    try:
        cursor = db.execute(
            """INSERT INTO modules (module_id, exam_pdf_path, answer_key_pdf_path)
               VALUES (?, ?, ?)""",
            (module_id, exam_pdf_path, answer_pdf_path)
        )
        db.commit()
        return {"id": cursor.lastrowid, "module_id": module_id, "message": f"Module '{module_id}' ingested successfully"}
    except Exception as e:
        db.rollback()
        for d in [word_dir, excel_dir, ppt_dir, module_root]:
            if os.path.exists(d):
                import shutil
                shutil.rmtree(d, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Phase 2: PDF Generation & Preview Pipeline
# ---------------------------------------------------------------------------
PREVIEW_BASE = os.path.join(OUTPUT_DIR, "preview")
MA_DE_PATTERN = re.compile(r"^[A-Za-z0-9_\-]+$")


def _validate_ma_de(ma_de: str) -> str:
    ma_de = ma_de.strip()
    if not ma_de or not MA_DE_PATTERN.fullmatch(ma_de):
        raise HTTPException(status_code=400, detail="ma_de must contain only letters, digits, '_' or '-'")
    return ma_de


def resolve_module_selection(req: GeneratePdfRequest):
    db = get_db()
    try:
        if req.random:
            row = db.execute("SELECT id, module_id FROM modules ORDER BY RANDOM() LIMIT 1").fetchone()
            if not row:
                raise HTTPException(status_code=400, detail="No modules available. Upload a module first.")
            mids = {"word": row["module_id"], "excel": row["module_id"], "ppt": row["module_id"]}
        else:
            ids = {
                "word": req.word_module_id,
                "excel": req.excel_module_id,
                "ppt": req.ppt_module_id,
            }
            if not all(ids.values()):
                raise HTTPException(status_code=400, detail="Select word/excel/ppt modules (or enable Random).")
            mids = {}
            for cat, mid in ids.items():
                row = db.execute("SELECT module_id FROM modules WHERE id=?", (mid,)).fetchone()
                if not row:
                    raise HTTPException(status_code=400, detail=f"Module id {mid} not found ({cat})")
                mids[cat] = row["module_id"]
    finally:
        db.close()

    selection = {}
    for cat in ("word", "excel", "ppt"):
        mid = mids[cat]
        cat_dir = os.path.join(MODULES_DIR, cat, mid)
        if not os.path.isdir(cat_dir):
            raise HTTPException(status_code=500, detail=f"Files missing for module '{mid}' ({cat} folder)")
        selection[cat] = {"module_id": mid, "dir": cat_dir}
    return selection


def cleanup_old_previews(max_age_seconds: int = 3600):
    if not os.path.isdir(PREVIEW_BASE):
        return
    now = time.time()
    for name in os.listdir(PREVIEW_BASE):
        p = os.path.join(PREVIEW_BASE, name)
        if os.path.isdir(p) and now - os.path.getmtime(p) > max_age_seconds:
            shutil.rmtree(p, ignore_errors=True)


@app.get("/api/modules")
async def list_modules():
    db = get_db()
    try:
        rows = db.execute("SELECT id, module_id, created_at FROM modules ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


@app.delete("/api/modules/{module_id}")
async def delete_module(module_id: str):
    module_id = module_id.strip()
    if not re.fullmatch(r"[A-Za-z0-9_\-]+", module_id):
        raise HTTPException(status_code=400, detail="Invalid module_id")

    db = get_db()
    try:
        row = db.execute("SELECT id FROM modules WHERE module_id=?", (module_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Module '{module_id}' not found")
        db.execute("DELETE FROM modules WHERE module_id=?", (module_id,))
        db.commit()
    finally:
        db.close()

    for d in [
        os.path.join(MODULES_DIR, "word", module_id),
        os.path.join(MODULES_DIR, "excel", module_id),
        os.path.join(MODULES_DIR, "ppt", module_id),
        os.path.join(MODULES_DIR, module_id),
    ]:
        if os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)

    return {"message": f"Module '{module_id}' deleted successfully"}


@app.post("/api/generate/preview")
async def generate_preview(req: GeneratePdfRequest):
    ma_de = _validate_ma_de(req.ma_de)
    selection = resolve_module_selection(req)

    token = uuid.uuid4().hex[:12]
    pdir = os.path.join(PREVIEW_BASE, token)
    os.makedirs(pdir, exist_ok=True)

    exam_path = os.path.join(pdir, f"Official_Exam_{ma_de}.pdf")
    answer_path = os.path.join(pdir, f"Answer_Key_{ma_de}.pdf")

    try:
        ngay_thi_fmt = _format_ngay_thi(req.ngay_thi)
        await run_in_threadpool(build_exam_pdf, selection, ma_de, ngay_thi_fmt, exam_path)
        await run_in_threadpool(build_answer_key_pdf, selection, ma_de, req.can_bo_ra_de, answer_path, ngay_thi=ngay_thi_fmt)
    except Exception as e:
        shutil.rmtree(pdir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

    cleanup_old_previews()
    return {
        "exam_url": f"/api/preview/{token}/exam",
        "answer_key_url": f"/api/preview/{token}/answer_key",
    }


@app.get("/api/preview/{token}/{kind}")
async def get_preview_pdf(token: str, kind: str):
    if kind not in ("exam", "answer_key"):
        raise HTTPException(status_code=400, detail="kind must be 'exam' or 'answer_key'")
    if not re.fullmatch(r"[A-Za-z0-9]+", token):
        raise HTTPException(status_code=400, detail="Invalid preview token")

    pdir = os.path.join(PREVIEW_BASE, token)
    if not os.path.isdir(pdir):
        raise HTTPException(status_code=404, detail="Preview not found")

    prefix = "Official_Exam" if kind == "exam" else "Answer_Key"
    matches = [f for f in os.listdir(pdir) if f.startswith(prefix) and f.endswith(".pdf")]
    if not matches:
        raise HTTPException(status_code=404, detail="Preview file not found")

    match = os.path.join(pdir, matches[0])
    return FileResponse(path=match, media_type="application/pdf", filename=matches[0])


@app.post("/api/generate/download")
async def generate_download(req: GeneratePdfRequest):
    ma_de = _validate_ma_de(req.ma_de)
    selection = resolve_module_selection(req)

    outdir = os.path.join(OUTPUT_DIR, "generated_pdf")
    os.makedirs(outdir, exist_ok=True)
    token = uuid.uuid4().hex[:8]
    task_dir = os.path.join(outdir, token)
    os.makedirs(task_dir, exist_ok=True)

    try:
        exam_path = os.path.join(task_dir, f"Official_Exam_{ma_de}.pdf")
        answer_path = os.path.join(task_dir, f"Answer_Key_{ma_de}.pdf")
        ngay_thi_fmt = _format_ngay_thi(req.ngay_thi)
        await run_in_threadpool(build_exam_pdf, selection, ma_de, ngay_thi_fmt, exam_path)
        await run_in_threadpool(build_answer_key_pdf, selection, ma_de, req.can_bo_ra_de, answer_path, ngay_thi=ngay_thi_fmt)

        zip_name = f"DLU_Exam_{ma_de}.zip"
        zip_path = os.path.join(outdir, zip_name)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(exam_path, arcname=f"MaDe_{ma_de.upper()}.pdf")
            zf.write(answer_path, arcname=f"DapAn_{ma_de.upper()}.pdf")

            excel_raw = os.path.join(selection["excel"]["dir"], "dlm_raw.xlsx")
            if os.path.exists(excel_raw):
                zf.write(excel_raw, arcname=f"DLM_{ma_de.upper()}.xlsx")

            ppt_raw = os.path.join(selection["ppt"]["dir"], "dlm.pptx")
            if os.path.exists(ppt_raw):
                zf.write(ppt_raw, arcname="DLM.pptx")

            for asset in list_module_images(selection["word"]["dir"]):
                zf.write(asset, arcname=os.path.basename(asset))

        shutil.rmtree(task_dir, ignore_errors=True)
        return FileResponse(
            path=zip_path,
            filename=zip_name,
            media_type="application/zip",
        )
    finally:
        if os.path.isdir(task_dir):
            shutil.rmtree(task_dir, ignore_errors=True)
