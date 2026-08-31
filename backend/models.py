from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ExamSetOut(BaseModel):
    id: int
    name: str
    category: str
    exam_filename: str
    criteria_filename: str
    created_at: Optional[str] = None

class GenerateRequest(BaseModel):
    count: int = 1

class GenerateResponse(BaseModel):
    id: int
    filename: str
    message: str

class StatsResponse(BaseModel):
    word_count: int
    excel_count: int
    powerpoint_count: int
    total: int
