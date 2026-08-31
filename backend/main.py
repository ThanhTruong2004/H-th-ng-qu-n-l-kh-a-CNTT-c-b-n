import os
import random
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from database import get_db, init_db
from models import ExamSetOut, GenerateRequest, GenerateResponse, StatsResponse
from file_utils import (
    ensure_dirs, detect_category, is_criteria_file,
    save_upload, delete_file, merge_criteria_files, package_exam_set,
    OUTPUT_DIR
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

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    db = get_db()
    try:
        word_count = db.execute("SELECT COUNT(*) FROM exam_sets WHERE category='word'").fetchone()[0]
        excel_count = db.execute("SELECT COUNT(*) FROM exam_sets WHERE category='excel'").fetchone()[0]
        powerpoint_count = db.execute("SELECT COUNT(*) FROM exam_sets WHERE category='powerpoint'").fetchone()[0]
        return StatsResponse(
            word_count=word_count,
            excel_count=excel_count,
            powerpoint_count=powerpoint_count,
            total=word_count + excel_count + powerpoint_count
        )
    finally:
        db.close()

@app.get("/api/sets")
async def list_sets(category: Optional[str] = None):
    db = get_db()
    try:
        if category:
            rows = db.execute(
                "SELECT * FROM exam_sets WHERE category=? ORDER BY created_at DESC",
                (category,)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM exam_sets ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()

@app.post("/api/sets/upload")
async def upload_set(
    exam: UploadFile = File(...),
    criteria: UploadFile = File(...),
    name: str = Form("")
):
    exam_category = detect_category(exam.filename)
    if not exam_category:
        raise HTTPException(status_code=400, detail=f"Unsupported exam file type. Accepted: .docx, .xlsx, .xls, .pptx")

    if not is_criteria_file(criteria.filename):
        raise HTTPException(status_code=400, detail="Criteria file must be .xlsx format")

    exam_bytes = await exam.read()
    criteria_bytes = await criteria.read()

    if len(exam_bytes) == 0:
        raise HTTPException(status_code=400, detail="Exam file is empty")
    if len(criteria_bytes) == 0:
        raise HTTPException(status_code=400, detail="Criteria file is empty")

    exam_path = save_upload(exam_bytes, exam.filename, exam_category)
    criteria_path = save_upload(criteria_bytes, criteria.filename, f"{exam_category}_criteria")

    set_name = name.strip() if name and name.strip() else Path(exam.filename).stem

    db = get_db()
    try:
        cursor = db.execute(
            """INSERT INTO exam_sets (name, category, exam_filename, exam_path, criteria_filename, criteria_path)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (set_name, exam_category, exam.filename, exam_path, criteria.filename, criteria_path)
        )
        db.commit()
        new_id = cursor.lastrowid
        return {"id": new_id, "message": f"Exam set uploaded successfully as '{exam_category}' category"}
    except Exception as e:
        db.rollback()
        delete_file(exam_path)
        delete_file(criteria_path)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.delete("/api/sets/{set_id}")
async def delete_set(set_id: int):
    db = get_db()
    try:
        row = db.execute("SELECT * FROM exam_sets WHERE id=?", (set_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Exam set not found")
        delete_file(row["exam_path"])
        delete_file(row["criteria_path"])
        db.execute("DELETE FROM exam_sets WHERE id=?", (set_id,))
        db.commit()
        return {"message": "Exam set deleted"}
    finally:
        db.close()

@app.post("/api/generate")
async def generate_exam(request: GenerateRequest):
    if request.count < 1:
        raise HTTPException(status_code=400, detail="Count must be at least 1")

    db = get_db()
    try:
        words = db.execute("SELECT * FROM exam_sets WHERE category='word'").fetchall()
        excels = db.execute("SELECT * FROM exam_sets WHERE category='excel'").fetchall()
        ppts = db.execute("SELECT * FROM exam_sets WHERE category='powerpoint'").fetchall()

        if not words:
            raise HTTPException(status_code=400, detail="No Word (.docx) exams available. Upload at least one.")
        if not excels:
            raise HTTPException(status_code=400, detail="No Excel (.xlsx) exams available. Upload at least one.")
        if not ppts:
            raise HTTPException(status_code=400, detail="No PowerPoint (.pptx) exams available. Upload at least one.")

        results = []
        for _ in range(request.count):
            w = random.choice(words)
            e = random.choice(excels)
            p = random.choice(ppts)

            criteria_paths = [w["criteria_path"], e["criteria_path"], p["criteria_path"]]
            exam_paths = [w["exam_path"], e["exam_path"], p["exam_path"]]
            exam_names = [w["exam_filename"], e["exam_filename"], p["exam_filename"]]

            import uuid
            temp_criteria = os.path.join(OUTPUT_DIR, f"merged_{uuid.uuid4().hex[:8]}.xlsx")
            merge_criteria_files(criteria_paths, temp_criteria)

            zip_path = package_exam_set(exam_paths, exam_names, temp_criteria, OUTPUT_DIR)

            cursor = db.execute(
                """INSERT INTO generated_exams (set_name, exam_word_id, exam_excel_id, exam_powerpoint_id, output_filename, output_path)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (f"Generated Set", w["id"], e["id"], p["id"], os.path.basename(zip_path), zip_path)
            )
            db.commit()

            results.append({
                "id": cursor.lastrowid,
                "filename": os.path.basename(zip_path),
                "word_exam": w["name"],
                "excel_exam": e["name"],
                "ppt_exam": p["name"]
            })

        return {"sets": results, "count": len(results)}
    finally:
        db.close()

@app.get("/api/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/zip"
    )

@app.delete("/api/generated/{gen_id}")
async def delete_generated(gen_id: int):
    db = get_db()
    try:
        row = db.execute("SELECT * FROM generated_exams WHERE id=?", (gen_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Generated exam not found")
        delete_file(row["output_path"])
        db.execute("DELETE FROM generated_exams WHERE id=?", (gen_id,))
        db.commit()
        return {"message": "Generated exam deleted"}
    finally:
        db.close()

@app.get("/api/generated")
async def list_generated():
    db = get_db()
    try:
        rows = db.execute(
            """SELECT ge.*, 
                      w.name as word_name, e.name as excel_name, p.name as ppt_name
               FROM generated_exams ge
               LEFT JOIN exam_sets w ON ge.exam_word_id = w.id
               LEFT JOIN exam_sets e ON ge.exam_excel_id = e.id
               LEFT JOIN exam_sets p ON ge.exam_powerpoint_id = p.id
               ORDER BY ge.created_at DESC"""
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()
