from pydantic import BaseModel
from typing import Optional

class GeneratePdfRequest(BaseModel):
    ngay_thi: str
    ma_de: str
    can_bo_ra_de: str = "Trương Việt Hoa"
    random: bool = False
    word_module_id: Optional[int] = None
    excel_module_id: Optional[int] = None
    ppt_module_id: Optional[int] = None