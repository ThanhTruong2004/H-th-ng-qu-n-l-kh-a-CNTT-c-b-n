import asyncio
import base64
import glob
import json
import logging
import os
import re
import shutil
import tempfile
import time
import uuid
import zipfile
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool
import fitz

from database import get_db, init_db
from models import GeneratePdfRequest, DownloadRequest
from file_utils import (
    ensure_dirs, OUTPUT_DIR, UPLOAD_DIR, format_ngay_thi,
    ALLOWED_IMAGE_EXTS, ALLOWED_RAW_EXTS, ALLOWED_WORD_EXTS,
)
from conversion import convert_docx_to_pdf
from services.pdf_generator import (
    MODULES_DIR, build_exam_pdf, build_answer_key_pdf, list_module_images,
    shutdown_browser,
)

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="IT Exam Manager", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _cleanup_orphan_zips() -> int:
    """AUDIT-22 Critical Leak #2: DLU_Exam_*.zip files in OUTPUT_DIR were never
    deleted (each download ZIP is rebuilt on demand from the cached generation
    artifact).  Removes orphans on startup.  Returns the count removed.

    REL-002/REL-003 (AUDIT-99): only ZIPs strictly older than 1 hour are
    touched.  A brand-new ZIP may be mid-stream to a teacher on a slow network
    — deleting it would truncate their download.  Files that vanish between
    glob() and stat() are skipped (another writer just consumed them)."""
    removed = 0
    now = time.time()
    for f in glob.glob(os.path.join(OUTPUT_DIR, "DLU_Exam_*.zip")):
        try:
            age = now - os.path.getmtime(f)
        except OSError:
            # Vanished between glob and stat — nothing to clean, no race bite.
            continue
        # Only delete files older than 1 hour (REL-002/REL-003 race guard).
        if age <= 3600:
            continue
        try:
            os.remove(f)
            removed += 1
        except OSError:
            logger.warning("Could not remove orphan ZIP %s", f)
    return removed


def _cleanup_tmp_leaks() -> int:
    """AUDIT-22 §2.2/2.3: orphaned LibreOffice (lo_conv_*/lo_home_*) and PDF gen
    (pdfgen_exam_*/pdfgen_ak_*) temp dirs left behind by SIGKILL'd processes
    (a `finally` block never runs after `docker kill`). Returns the count.

    AUDIT-99 PORTABILITY-2: resolve the temp root via tempfile.gettempdir()
    instead of a hardcoded Linux "/tmp" — on Windows bare-metal that path does
    not exist, so the function silently no-oped."""
    removed = 0
    tmp_root = Path(tempfile.gettempdir())
    if not tmp_root.is_dir():
        return removed
    for pattern in ("lo_conv_*", "lo_home_*", "pdfgen_exam_*", "pdfgen_ak_*"):
        for d in tmp_root.glob(pattern):
            try:
                shutil.rmtree(d, ignore_errors=True)
                removed += 1
            except OSError:
                logger.warning("Could not remove tmp leak %s", d)
    return removed


async def _wal_checkpoint():
    """AUDIT-22 §2.5: periodic PASSIVE checkpoint keeps the SQLite -wal file
    bounded (the default auto-checkpoint is unreliable under long-lived pool
    read locks). Runs every 10 minutes as a background task."""
    while True:
        await asyncio.sleep(600)
        try:
            conn = get_db()
            try:
                conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
            finally:
                conn.close()
        except Exception:
            logger.exception("WAL checkpoint failed (will retry next cycle)")


@app.on_event("startup")
async def startup():
    init_db()
    ensure_dirs()
    os.makedirs(os.path.join(UPLOAD_DIR, "modules"), exist_ok=True)

    # --- Storage hygiene on startup (Phase 19 / AUDIT-22 §4) ---
    try:
        # 1. Clean stale generation artifacts (PDFs older than 1 hour)
        cleanup_old_generations(GENERATIONS_DIR, max_age_seconds=3600)

        # 2. Clean orphaned ZIP downloads (files matching DLU_Exam_*.zip)
        zips = _cleanup_orphan_zips()

        # 3+4. Clean orphaned LibreOffice + PDF-gen temp dirs from crashes
        tmp_leaks = _cleanup_tmp_leaks()

        # 5. Periodic WAL checkpoint (every 10 minutes)
        asyncio.create_task(_wal_checkpoint())

        logger.info(
            "startup hygiene: pruned generations, %d orphan ZIP(s), %d tmp leak(s); WAL checkpoint task running",
            zips, tmp_leaks,
        )
    except Exception:
        logger.exception("startup hygiene cleanup failed (non-fatal)")


@app.on_event("shutdown")
async def shutdown():
    shutdown_browser()

@app.get("/api/health")
async def health():
    return {"status": "ok"}


# AUDIT-99 LOG-005: extension definitions live in file_utils.py (single source
# of truth); imported above. MODULE_FILE_CATEGORIES semantically describes the
# three section types used by module storage/serving.
MODULE_FILE_CATEGORIES = ("word", "excel", "ppt")
MODULE_SERVE_EXTS = set(ALLOWED_IMAGE_EXTS) | set(ALLOWED_RAW_EXTS) | {".xlsx", ".xls", ".pptx"}


def _needs_word_conversion(filename: str) -> bool:
    return (filename or "").lower().endswith(ALLOWED_WORD_EXTS)


def page_to_data_url(pdf_bytes: bytes, page_index: int) -> str:
    """Render a single PDF page to a Base64 JPEG data URL (for the frontend
    interactive cropper). Uses JPEG at 3x scale for fast network transfer."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:  # AUDIT-24 CV-1
        raise HTTPException(status_code=400, detail="Corrupted or unreadable PDF")
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
    (Word/Excel/PPT rubrics).

    Accepts .doc/.docx inputs; Word documents are converted to PDF on the fly
    via LibreOffice before rendering (Phase 18 Req 3)."""
    result = {}

    async def _to_pdf(upload: UploadFile) -> bytes:
        data = await upload.read()
        if _needs_word_conversion(upload.filename or ""):
            logger.info("Converting Word '%s' to PDF for page rendering", upload.filename)
            data = await convert_docx_to_pdf(data, upload.filename)
        return data

    if exam_raw_pdf and exam_raw_pdf.filename:
        data = await _to_pdf(exam_raw_pdf)
        result["exam"] = [page_to_data_url(data, i) for i in (1, 2, 3)]
    if answer_key_raw_pdf and answer_key_raw_pdf.filename:
        data = await _to_pdf(answer_key_raw_pdf)
        result["answer"] = [page_to_data_url(data, i) for i in (0, 1, 2)]
    if not result:
        raise HTTPException(status_code=400, detail="Provide exam_raw_pdf and/or answer_key_raw_pdf")
    return result


MODULE_ID_PATTERN = re.compile(r"[A-Za-z0-9_\-]+")


def _sanitize_module_id(module_id: str) -> str:
    """Sanitize a module_id before it is used in any filesystem path.

    Strips the input, then reduces it to its basename so values like
    '../x' or '..\\x' can never escape MODULES_DIR. Finally requires a strict
    [A-Za-z0-9_-] charset, rejecting everything else (path traversal
    hardening / Logic Bug 11)."""
    module_id = module_id.strip()
    module_id = os.path.basename(module_id)
    if not module_id or not MODULE_ID_PATTERN.fullmatch(module_id):
        raise HTTPException(status_code=400, detail="Invalid module_id")
    return module_id


def write_file_sync(path: str, data: bytes) -> None:
    """Blocking file write — executed via run_in_threadpool (PERF-004) so the
    asyncio event loop is never blocked by disk I/O."""
    with open(path, "wb") as f:
        f.write(data)


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
    module_id = _sanitize_module_id(module_id)

    if not module_id:
        raise HTTPException(status_code=400, detail="module_id is required")

    if not exam_raw_pdf.filename.lower().endswith(ALLOWED_RAW_EXTS):
        raise HTTPException(status_code=400, detail="exam_raw_pdf must be a .pdf/.doc/.docx file")
    if not answer_key_raw_pdf.filename.lower().endswith(ALLOWED_RAW_EXTS):
        raise HTTPException(status_code=400, detail="answer_key_raw_pdf must be a .pdf/.doc/.docx file")
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

    async def _to_pdf_bytes(upload: UploadFile, field: str) -> tuple:
        """Read a raw exam/answer upload, converting Word to PDF if needed."""
        data = await upload.read()
        fname = upload.filename or f"{field}.pdf"
        if len(data) == 0:
            raise HTTPException(status_code=400, detail=f"{field} is empty")
        if _needs_word_conversion(fname):
            logger.info("Converting Word %s '%s' -> PDF via LibreOffice", field, fname)
            try:
                data = await convert_docx_to_pdf(data, fname)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Cannot convert {field} Word document to PDF: {e}")
            save_name = os.path.splitext(fname)[0] + ".pdf"
        else:
            save_name = fname
        return data, save_name

    exam_bytes, exam_save_name = await _to_pdf_bytes(exam_raw_pdf, "exam_raw_pdf")
    answer_bytes, answer_save_name = await _to_pdf_bytes(answer_key_raw_pdf, "answer_key_raw_pdf")

    word_dir = os.path.join(MODULES_DIR, "word", module_id)
    excel_dir = os.path.join(MODULES_DIR, "excel", module_id)
    ppt_dir = os.path.join(MODULES_DIR, "ppt", module_id)
    module_root = os.path.join(MODULES_DIR, module_id)

    for d in [word_dir, excel_dir, ppt_dir, module_root]:
        os.makedirs(d, exist_ok=True)

    try:
        exam_pdf_path = os.path.join(module_root, exam_save_name)
        await run_in_threadpool(write_file_sync, exam_pdf_path, exam_bytes)

        answer_pdf_path = os.path.join(module_root, answer_save_name)
        await run_in_threadpool(write_file_sync, answer_pdf_path, answer_bytes)

        excel_bytes = await excel_raw_file.read()
        excel_path = os.path.join(excel_dir, "dlm_raw.xlsx")
        await run_in_threadpool(write_file_sync, excel_path, excel_bytes)

        ppt_bytes = await ppt_raw_file.read()
        ppt_path = os.path.join(ppt_dir, "dlm.pptx")
        await run_in_threadpool(write_file_sync, ppt_path, ppt_bytes)

        if word_assets:
            for asset in word_assets:
                asset_ext = Path(asset.filename).suffix.lower()
                if asset_ext in ALLOWED_IMAGE_EXTS:
                    asset_bytes = await asset.read()
                    asset_path = os.path.join(word_dir, asset.filename)
                    await run_in_threadpool(write_file_sync, asset_path, asset_bytes)

        # Explicit mapping — no locals() reflection (Logic Bug 11 fix).
        # (field_name, target_dir, prefix, uploads)
        crop_slots = [
            ("word_preview", word_dir, "preview", word_preview),
            ("excel_preview", excel_dir, "preview", excel_preview),
            ("ppt_preview", ppt_dir, "preview", ppt_preview),
            ("word_rubric", word_dir, "rubric", word_rubric),
            ("excel_rubric", excel_dir, "rubric", excel_rubric),
            ("ppt_rubric", ppt_dir, "rubric", ppt_rubric),
        ]
        for field_name, target_dir, prefix, uploads in crop_slots:
            uploads = uploads or []
            for i, upload in enumerate(uploads):
                if not upload or not upload.filename:
                    continue
                if not upload.filename.lower().endswith(".png"):
                    raise HTTPException(status_code=400, detail=f"{field_name} must be a .png file")
                crop_bytes = await upload.read()
                # MULTI-CROP: each additional PNG for the same section gets an
                # incremented suffix so the PDF engine can stack them in order.
                save_name = f"{prefix}_{i}.png"
                await run_in_threadpool(
                    write_file_sync, os.path.join(target_dir, save_name), crop_bytes)

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
# Phase 13: Single Generation Artifact (P0) — generate EXACTLY ONCE, then
# preview & download both consume the same cached artifact.
# ---------------------------------------------------------------------------
GENERATIONS_DIR = os.path.join(OUTPUT_DIR, "generations")
GENERATION_ID_PATTERN = re.compile(r"[a-f0-9]{32}")
MA_DE_PATTERN = re.compile(r"^[A-Za-z0-9_\-]+$")


def _validate_ma_de(ma_de: str) -> str:
    ma_de = ma_de.strip()
    if not ma_de or not MA_DE_PATTERN.fullmatch(ma_de):
        raise HTTPException(status_code=400, detail="ma_de must contain only letters, digits, '_' or '-'")
    return ma_de


def _validate_generation_id(generation_id: str) -> str:
    generation_id = generation_id.strip()
    if not GENERATION_ID_PATTERN.fullmatch(generation_id):
        raise HTTPException(status_code=400, detail="Invalid generation_id")
    return generation_id


def resolve_module_selection(req: GeneratePdfRequest):
    db = get_db()
    try:
        if req.random:
            # MIX-AND-MATCH: draw an INDEPENDENT random module per category so
            # the exam combines Word + Excel + PPT selections, not one module
            # repeated across all three.
            mids = {}
            for cat in ("word", "excel", "ppt"):
                row = db.execute("SELECT module_id FROM modules ORDER BY RANDOM() LIMIT 1").fetchone()
                if not row:
                    raise HTTPException(status_code=400, detail="No modules available. Upload a module first.")
                mids[cat] = row["module_id"]
            logger.info(
                "Module selection mode=Random word=%s excel=%s ppt=%s",
                mids["word"], mids["excel"], mids["ppt"],
            )
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
            logger.info(
                "Module selection mode=Manual ids=%s word=%s excel=%s ppt=%s",
                ids, mids["word"], mids["excel"], mids["ppt"],
            )
    finally:
        db.close()

    return selection_from_module_ids(mids)


def selection_from_module_ids(mids):
    """Build the selection dict consumed by the PDF engine from a mapping of
    {cat: module_id}, verifying the on-disk module folders exist."""
    selection = {}
    for cat in ("word", "excel", "ppt"):
        mid = mids[cat]
        cat_dir = os.path.join(MODULES_DIR, cat, mid)
        if not os.path.isdir(cat_dir):
            raise HTTPException(status_code=500, detail=f"Files missing for module '{mid}' ({cat} folder)")
        selection[cat] = {"module_id": mid, "dir": cat_dir}
    return selection


def write_generation_manifest(pdir: str, ma_de: str, can_bo_ra_de: str, mids) -> None:
    manifest = {
        "ma_de": ma_de,
        "can_bo_ra_de": can_bo_ra_de,
        "modules": mids,
    }
    with open(os.path.join(pdir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False)


def read_generation_manifest(pdir: str):
    mpath = os.path.join(pdir, "manifest.json")
    if not os.path.isfile(mpath):
        raise HTTPException(status_code=404, detail="Generation manifest not found")
    try:
        with open(mpath, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Corrupt generation manifest: {str(e)}")
    if not isinstance(manifest, dict) or "modules" not in manifest:
        raise HTTPException(status_code=500, detail="Corrupt generation manifest")
    return manifest


def cleanup_old_generations(gen_dir: str = None, max_age_seconds: int = 3600):
    """Remove generation artifacts older than max_age_seconds.

    Runs as a FastAPI background task (Req 3) so it never blocks the request
    thread. `gen_dir` defaults to GENERATIONS_DIR when omitted."""
    target = gen_dir or GENERATIONS_DIR
    if not os.path.isdir(target):
        return
    now = time.time()
    for name in os.listdir(target):
        p = os.path.join(target, name)
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


@app.get("/api/modules/{module_id}")
async def get_module_detail(module_id: str):
    """Phase 18 (Req 2): return module metadata plus filesystem-scanned lists of
    crop image URLs (word/excel/ppt × preview/rubric) and word asset URLs."""
    module_id = _sanitize_module_id(module_id)

    db = get_db()
    try:
        row = db.execute(
            "SELECT id, module_id, created_at FROM modules WHERE module_id=?", (module_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Module '{module_id}' not found")
        detail = dict(row)
    finally:
        db.close()

    crops = {
        "word_preview": [], "excel_preview": [], "ppt_preview": [],
        "word_rubric": [], "excel_rubric": [], "ppt_rubric": [],
    }
    word_assets = []
    for cat in MODULE_FILE_CATEGORIES:
        cat_dir = os.path.join(MODULES_DIR, cat, module_id)
        if not os.path.isdir(cat_dir):
            continue
        for fname in sorted(os.listdir(cat_dir)):
            fpath = os.path.join(cat_dir, fname)
            if not os.path.isfile(fpath):
                continue
            low = fname.lower()
            if low.startswith("preview_") or low.startswith("rubric_"):
                kind = "preview" if low.startswith("preview_") else "rubric"
                crops[f"{cat}_{kind}"].append(f"/api/modules/{module_id}/files/{cat}/{fname}")
            elif Path(fname).suffix.lower() in ALLOWED_IMAGE_EXTS:
                if cat == "word":
                    word_assets.append(f"/api/modules/{module_id}/files/{cat}/{fname}")

    detail["crops"] = crops
    detail["word_assets"] = word_assets
    return detail


@app.get("/api/modules/{module_id}/files/{category}/{filename}")
async def get_module_file(module_id: str, category: str, filename: str):
    """Phase 18 (Req 2): serve a module asset (crop image / word asset / raw
    source) as FileResponse so the frontend can render it in the detail modal.
    Category + filename are strictly validated to prevent path traversal."""
    module_id = _sanitize_module_id(module_id)
    if category not in MODULE_FILE_CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid category")
    filename = os.path.basename(filename)
    if not filename or filename != os.path.basename(filename):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if Path(filename).suffix.lower() not in MODULE_SERVE_EXTS:
        raise HTTPException(status_code=400, detail="Invalid file type")

    fpath = os.path.join(MODULES_DIR, category, module_id, filename)
    if not os.path.isfile(fpath):
        raise HTTPException(status_code=404, detail="Module file not found")
    return FileResponse(fpath)


@app.delete("/api/modules/{module_id}")
async def delete_module(module_id: str):
    # Path traversal hardening: reduce to a bare basename + strict charset so
    # module_id can never escape MODULES_DIR when used in shutil.rmtree.
    module_id = _sanitize_module_id(module_id)

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
async def generate_preview(req: GeneratePdfRequest, background_tasks: BackgroundTasks):
    """Generate the exam + answer PDFs EXACTLY ONCE and persist them as a
    single 'Generation Artifact'. Both the preview and the ZIP download later
    consume this artifact, so what you preview is byte-for-byte what you get."""
    ma_de = _validate_ma_de(req.ma_de)
    selection = resolve_module_selection(req)
    mids = {cat: sel["module_id"] for cat, sel in selection.items()}

    generation_id = uuid.uuid4().hex
    pdir = os.path.join(GENERATIONS_DIR, generation_id)
    os.makedirs(pdir, exist_ok=True)

    exam_path = os.path.join(pdir, "exam.pdf")
    answer_path = os.path.join(pdir, "answer_key.pdf")

    try:
        ngay_thi_fmt = format_ngay_thi(req.ngay_thi)
        await run_in_threadpool(build_exam_pdf, selection, ma_de, ngay_thi_fmt, exam_path)
        await run_in_threadpool(build_answer_key_pdf, selection, ma_de, req.can_bo_ra_de, answer_path, ngay_thi=ngay_thi_fmt)
        write_generation_manifest(pdir, ma_de, req.can_bo_ra_de, mids)
    except Exception as e:
        logger.exception("PDF generation failed for generation_id=%s ma_de=%s", generation_id, ma_de)
        shutil.rmtree(pdir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")

    # Deferred housekeeping: runs after the response is sent (Req 3), so old
    # artifacts are pruned without blocking the request thread.
    background_tasks.add_task(cleanup_old_generations, GENERATIONS_DIR)
    return {
        "generation_id": generation_id,
        "exam_url": f"/api/generations/{generation_id}/exam.pdf",
        "answer_url": f"/api/generations/{generation_id}/answer_key.pdf",
    }


@app.get("/api/generations/{generation_id}/{filename}")
async def get_generation_pdf(generation_id: str, filename: str):
    """Serve a generation artifact PDF for INLINE browser display — never a
    download. Phase 13.1 hotfix (R1)."""
    if filename not in ("exam.pdf", "answer_key.pdf"):
        raise HTTPException(status_code=400, detail="filename must be 'exam.pdf' or 'answer_key.pdf'")
    generation_id = _validate_generation_id(generation_id)

    pdir = os.path.join(GENERATIONS_DIR, generation_id)
    fpath = os.path.join(pdir, filename)
    if not os.path.isfile(fpath):
        raise HTTPException(status_code=404, detail="Generation file not found")

    return FileResponse(
        fpath,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


def iter_file(path: str):
    """Stream a file from disk in 64KB chunks — ASP ends never balloons the
    whole ZIP into memory (AUDIT-23 Fix 6 / Req 4)."""
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            yield chunk


def _remove_file_quietly(path: str):
    """Best-effort file removal used by download cleanup (AUDIT-24 CV-4)."""
    try:
        os.remove(path)
    except OSError:
        pass


@app.post("/api/generate/download")
async def generate_download(req: DownloadRequest, background_tasks: BackgroundTasks):
    """Package the ALREADY-GENERATED artifact into a ZIP. This endpoint never
    regenerates PDFs — it locates the cached generation by ID and renames the
    files according to the delivery format, then bundles the module assets."""
    ma_de = _validate_ma_de(req.ma_de)
    generation_id = _validate_generation_id(req.generation_id)

    pdir = os.path.join(GENERATIONS_DIR, generation_id)
    if not os.path.isdir(pdir):
        raise HTTPException(status_code=404, detail="Generation not found — hãy bấm Xem Trước trước khi tải ZIP")

    exam_path = os.path.join(pdir, "exam.pdf")
    answer_path = os.path.join(pdir, "answer_key.pdf")
    if not os.path.isfile(exam_path) or not os.path.isfile(answer_path):
        raise HTTPException(status_code=404, detail="Generation artifact incomplete")

    manifest = read_generation_manifest(pdir)
    if manifest.get("ma_de", "").strip() != ma_de:
        raise HTTPException(status_code=400, detail="ma_de does not match this generation")

    selection = selection_from_module_ids(manifest["modules"])

    zip_name = f"DLU_Exam_{ma_de}_{generation_id[:8]}.zip"
    zip_path = os.path.join(OUTPUT_DIR, zip_name)
    tmp_zip_path = zip_path + ".tmp"  # AUDIT-24 CV-2: never expose a half-written ZIP
    try:
        with zipfile.ZipFile(tmp_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
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
        # Atomic rename: concurrent readers only ever see a complete ZIP.
        os.replace(tmp_zip_path, zip_path)
    except Exception:
        if os.path.exists(tmp_zip_path):
            os.remove(tmp_zip_path)
        raise

    # AUDIT-24 CV-4: Content-Length lets the browser render a download
    # progress bar on slow networks.
    headers = {
        "Content-Disposition": f'attachment; filename="{zip_name}"',
        "Content-Length": str(os.path.getsize(zip_path)),
    }

    # AUDIT-24 CV-4: schedule deletion AFTER streaming finishes so repeated
    # downloads of the same generation regenerate a fresh ZIP instead of
    # accumulating disk usage in OUTPUT_DIR.
    background_tasks.add_task(_remove_file_quietly, zip_path)

    return StreamingResponse(
        iter_file(zip_path),
        media_type="application/zip",
        headers=headers,
    )
