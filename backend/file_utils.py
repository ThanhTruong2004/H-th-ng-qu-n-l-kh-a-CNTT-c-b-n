import os
import re
from datetime import datetime

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/data/uploads")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/data/outputs")

# --- Single source of truth for allowed file extensions (AUDIT-99 LOG-005) ---
# Consumed by main.py (validation), conversion.py (Word detection, serving).
ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
# Raw "base exam / answer key" uploads: native PDF or Word docs that are
# converted to PDF via LibreOffice before rendering/crop/extract (Phase 18).
ALLOWED_RAW_EXTS = (".pdf", ".doc", ".docx")
# Files LibreOffice can convert to PDF (used by conversion.py).
ALLOWED_WORD_EXTS = (".doc", ".docx")


def ensure_dirs():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)


# AUDIT-27 (Req 2): reject placeholder strings the UI emits when no date is
# selected — these must never leak into the rendered PDF as raw text.
_PLACEHOLDER_RE = re.compile(
    r'^(dd[/-]mm[/-]yyyy|mm[/-]dd[/-]yyyy|yyyy[/-]mm[/-]dd|'
    r'ng[àa]y[_ ]thi|date|__/__/____|____-__-__|'
    r'\u2026/\u2026/\u2026)$',
    re.IGNORECASE
)

_DATE_FORMATS = [
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
]


def format_ngay_thi(value: str) -> str:
    """Normalize ngay_thi into DD/MM/YYYY for the templates.

    Accepts ISO dates (with or without 'T' separator + time), DD/MM/YYYY,
    and DD-MM-YYYY.  Empty / placeholder values return the dotted sentinel
    "…/…/…" for manual writing.  Genuinely invalid strings raise ValueError."""
    if not value or not value.strip():
        return "\u2026/\u2026/\u2026"
    value = value.strip()
    # AUDIT-27: reject placeholder patterns that look like empty templates.
    if _PLACEHOLDER_RE.match(value):
        return "\u2026/\u2026/\u2026"
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    raise ValueError(
        f"Invalid ngay_thi format: '{value}'. "
        "Expected YYYY-MM-DD or DD/MM/YYYY"
    )