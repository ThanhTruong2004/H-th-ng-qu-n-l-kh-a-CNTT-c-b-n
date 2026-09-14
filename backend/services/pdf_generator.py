"""PDF assembly engine for DLU IT Exam Generation (Phase 2).

Renders Jinja2 templates (exam_p1 / answer_key_p1 / answer_key_p4) to PDF via
Playwright Chromium, then stitches the sliced images (Phase 1) with PyMuPDF
(fitz) and injects uniform footers.
"""

import atexit
import io
import os
import re
import shutil
import tempfile
from typing import List, Tuple

import fitz
from PIL import Image
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

from file_utils import UPLOAD_DIR

# ---------------------------------------------------------------------------
# Page geometry (A4 in points)
# ---------------------------------------------------------------------------
PAGE_W, PAGE_H = 595.28, 841.89

# Exact institution margins: Top 2cm, Bottom 2cm, Left 3cm, Right 2cm
MARGIN_TOP = 56.7
MARGIN_BOTTOM = 56.7
MARGIN_LEFT = 85.05
MARGIN_RIGHT = 56.7

CONTENT_X0 = MARGIN_LEFT
CONTENT_X1 = PAGE_W - MARGIN_RIGHT
CONTENT_Y0 = MARGIN_TOP
CONTENT_Y1 = PAGE_H - MARGIN_BOTTOM

MODULES_DIR = os.path.join(UPLOAD_DIR, "modules")
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

# ---------------------------------------------------------------------------
# Playwright singleton — one Chromium process for the entire app lifetime.
# Lazy-initialized on first render call (runs in a worker thread with no
# asyncio event loop, so sync_playwright works fine).
# ---------------------------------------------------------------------------
_pw = None      # sync Playwright instance (kept alive)
_browser = None # sync Browser object (reused across render calls)


def _ensure_browser():
    """Return the live browser, launching lazily on first call."""
    global _pw, _browser
    if _browser is not None and _browser.is_connected():
        return _browser
    if _browser is not None:
        try:
            _browser.close()
        except Exception:
            pass
    if _pw is None:
        _pw = sync_playwright().start()
        atexit.register(shutdown_browser)
    _browser = _pw.chromium.launch(
        args=["--no-sandbox", "--disable-setuid-sandbox"],
    )
    return _browser


def shutdown_browser():
    """Tear down the browser on app shutdown."""
    global _pw, _browser
    try:
        if _browser:
            _browser.close()
    except Exception:
        pass
    try:
        if _pw:
            _pw.stop()
    except Exception:
        pass
    _browser = None
    _pw = None


def _env() -> Environment:
    return Environment(loader=FileSystemLoader(TEMPLATE_DIR))


def resolve_fonts():
    reg = os.environ.get("EXAM_FONT_FILE")
    bold = os.environ.get("EXAM_FONT_BOLD_FILE")
    if not reg and os.name == "nt":
        windir = os.environ.get("WINDIR") or r"C:\Windows"
        reg = os.path.join(windir, "Fonts", "times.ttf")
    if not bold and os.name == "nt":
        windir = os.environ.get("WINDIR") or r"C:\Windows"
        bold = os.path.join(windir, "Fonts", "timesbd.ttf")
    if not reg:
        reg = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
    if not bold:
        bold = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
    missing = [p for p in (reg, bold) if not (p and os.path.exists(p))]
    if missing:
        raise RuntimeError("Times New Roman / Liberation Serif font file not found: " + ", ".join(missing))
    return reg, bold


def render_html_pdf(template_name: str, out_path: str, **ctx) -> str:
    """Render a Jinja2 template to a PDF page using the persistent Chromium
    singleton. Only a new page+context is created per call; the browser
    process stays alive for the entire app lifetime."""
    html = _env().get_template(template_name).render(**ctx)
    browser = _ensure_browser()
    context = browser.new_context()
    page = context.new_page()
    try:
        page.set_content(html, wait_until="load")
        page.pdf(path=out_path, format="A4", print_background=True,
                 prefer_css_page_size=True)
    finally:
        page.close()
        context.close()
    return out_path


def render_html_pdf_bytes(template_name: str, **ctx) -> bytes:
    """Like render_html_pdf but returns raw PDF bytes (no temp file needed).
    Used by single-pass assembly to avoid writing+reading a temp file."""
    html = _env().get_template(template_name).render(**ctx)
    browser = _ensure_browser()
    context = browser.new_context()
    page = context.new_page()
    try:
        page.set_content(html, wait_until="load")
        pdf_bytes = page.pdf(format="A4", print_background=True,
                             prefer_css_page_size=True)
    finally:
        page.close()
        context.close()
    return pdf_bytes


def _compress_image(img_bytes: bytes) -> bytes:
    """Force in-memory JPEG compression at 75% quality to slash embedded image
    size by ~95% vs lossless PNG. Handles RGBA/P-mode images by converting to
    RGB first. Falls back to raw bytes if PIL cannot decode the image."""
    try:
        with Image.open(io.BytesIO(img_bytes)) as pil_img:
            if pil_img.mode in ("RGBA", "P", "LA"):
                pil_img = pil_img.convert("RGB")
            elif pil_img.mode == "CMYK":
                pil_img = pil_img.convert("RGB")
            out_io = io.BytesIO()
            pil_img.save(out_io, format="JPEG", quality=75, optimize=True)
            return out_io.getvalue()
    except Exception:
        return img_bytes


def new_a4(doc: fitz.Document) -> fitz.Page:
    return doc.new_page(width=PAGE_W, height=PAGE_H)


def _register_font(page: fitz.Page, fontfile: str, fontname: str) -> str:
    # insert_font() returns an int xref in PyMuPDF 1.27; the fontname string is
    # what insert_text() needs, and it auto-embeds from fontfile when passed.
    page.insert_font(fontname=fontname, fontfile=fontfile)
    return fontname


_text_width_cache = {}


def _text_width(text: str, fontname: str, fontsize: float, fontfile: str) -> float:
    """Measure rendered text width in points using an off-screen page (accurate
    for embedded TTF fonts, which fitz.get_text_length does not support)."""
    key = (text, fontfile, fontsize)
    if key in _text_width_cache:
        return _text_width_cache[key]
    doc = fitz.open()
    try:
        page = doc.new_page(width=2000, height=60)
        page.insert_text((0, 20), text, fontsize=fontsize, fontname=fontname, fontfile=fontfile)
        data = page.get_text("rawdict")
        spans = [s for b in data["blocks"] for l in b.get("lines", []) for s in l.get("spans", [])]
        w = spans[0]["bbox"][2] - spans[0]["bbox"][0] if spans else 0.0
    finally:
        doc.close()
    _text_width_cache[key] = w
    return w


# Absolute maximum printable image box (Pages 2/3/4 of Exam & Answer Key).
# A4 595.28x841.89; left 3cm = 85.04, right 2cm => max_x = 595.28 - 56.69,
# top 2cm = 56.69, bottom leaves 2cm + footer room => max_y = 780.0.
IMAGE_X0 = 85.04          # 3cm left margin
IMAGE_TOP = 56.69         # 2cm top margin
IMAGE_RIGHT = 538.59      # 595.28 - 2cm right margin
IMAGE_BOTTOM = 780.0      # 2cm bottom margin + footer room
IMAGE_MAX_WIDTH = IMAGE_RIGHT - IMAGE_X0      # 453.55
IMAGE_MAX_HEIGHT = IMAGE_BOTTOM - IMAGE_TOP   # 723.31

# Vertical gap (pt) between two stacked crop images on the same page.
STACK_PADDING = 20.0


def get_image_fit_size(img_path: str, top: float = IMAGE_TOP,
                       bottom: float = IMAGE_BOTTOM) -> Tuple[float, float]:
    """Compute the TIGHT, TOP-ANCHORED bounding box (w, h) for an image inside
    the printable box, preserving aspect ratio:

        box_ratio = max_width / max_height
        if img_ratio >= box_ratio:  final_w = max_width;  final_h = max_width / img_ratio
        else:                       final_h = max_height; final_w = max_height * img_ratio

    Returning the size lets callers paginate BEFORE inserting (multi-crop)."""
    if not img_path or not os.path.exists(img_path):
        return 0.0, 0.0
    with open(img_path, "rb") as f:
        img_bytes = f.read()
    pix = fitz.Pixmap(img_bytes)
    img_w, img_h = pix.width, pix.height
    pix = None

    max_width = IMAGE_RIGHT - IMAGE_X0
    max_height = bottom - top
    img_ratio = img_w / img_h
    box_ratio = max_width / max_height
    if img_ratio >= box_ratio:
        final_w = max_width
        final_h = max_width / img_ratio
    else:
        final_h = max_height
        final_w = max_height * img_ratio
    return final_w, final_h


def embed_image_fit(page: fitz.Page, img_path: str, top: float = IMAGE_TOP,
                    bottom: float = IMAGE_BOTTOM) -> float:
    """Insert a single cropped image with a TIGHT, TOP-ANCHORED rectangle.

    PyMuPDF never auto-centers (no keep_proportion) — the image fills the tight
    rect exactly, anchored to the top-left margin. Returns the Y after image."""
    final_w, final_h = get_image_fit_size(img_path, top=top, bottom=bottom)
    if final_w <= 0 or final_h <= 0:
        return top
    with open(img_path, "rb") as f:
        raw_bytes = f.read()
    img_bytes = _compress_image(raw_bytes)
    tight_rect = fitz.Rect(IMAGE_X0, top, IMAGE_X0 + final_w, top + final_h)
    page.insert_image(tight_rect, stream=img_bytes)
    return top + final_h


def stack_images(doc: fitz.Document, page: fitz.Page, img_paths,
                 top: float = IMAGE_TOP, bottom: float = IMAGE_BOTTOM,
                 padding: float = STACK_PADDING):
    """PHASE 8 MAX-WIDTH-FIRST STACKING with SMART PAGINATION.

    Rewritten from the old window-ratio fit (which could SQUASH an image into
    a microscopic dot when it was inserted near the bottom of a page). Every
    image is now:

        1. Scaled to fill the maximum horizontal width (453.55pt).
        2. Reduced to one page ONLY if it is taller than a full A4 page.
        3. Inserted on a NEW page if it cannot fit in the REMAINING space
           (guard: never break when already at the top of a fresh page).
        4. Top-anchored, keep_proportion, at 85.04 with 20pt padding after.

    Returns (last_page, current_y) where current_y is the Y right after the
    last placed image (image bottom + padding)."""
    max_w = IMAGE_RIGHT - IMAGE_X0                 # 453.55
    max_h_full_page = IMAGE_BOTTOM - IMAGE_TOP     # 723.31
    current_y = top
    for img_path in img_paths:
        if not os.path.exists(img_path):
            continue
        with open(img_path, "rb") as f:
            raw_bytes = f.read()
        img_bytes = _compress_image(raw_bytes)
        pix = fitz.Pixmap(img_bytes)
        img_w, img_h = pix.width, pix.height
        pix = None                                 # free memory

        # 1. Base scale: force the image to fill the maximum horizontal width
        scale = max_w / img_w
        final_w = max_w
        final_h = img_h * scale

        # 2. Safety check: an absurdly tall image is reduced to fit one page
        if final_h > max_h_full_page:
            scale = max_h_full_page / img_h
            final_h = max_h_full_page
            final_w = img_w * scale

        # 3. Smart Page Break BEFORE inserting: break if it does not fit in
        #    the remaining space and we are not already at the top of a page
        if current_y + final_h > bottom and current_y > 80.0:
            page = new_a4(doc)
            current_y = IMAGE_TOP                   # reset to top margin

        # 4. Insert image (top-anchored, max width, keep_proportion)
        rect = fitz.Rect(IMAGE_X0, current_y,
                         IMAGE_X0 + final_w, current_y + final_h)
        page.insert_image(rect, stream=img_bytes, keep_proportion=True)

        # 5. Advance Y cursor (20pt padding between stacked images)
        current_y += final_h + padding
    return page, current_y


# ---------------------------------------------------------------------------
# Footers
# ---------------------------------------------------------------------------
FOOTER_Y = PAGE_H - 42  # inside bottom margin


def add_exam_footer(page: fitz.Page, ma_de: str, page_no: int, total_pages: int,
                    reg_f: str, bold_f: str):
    """Left = Trang {page}/{total_pages}, Right = {ma_de} (bold)."""
    fn = _register_font(page, bold_f, "tnrb")
    fs = 10
    left_txt = f"Trang {page_no}/{total_pages}"
    right_txt = ma_de
    w_right = _text_width(right_txt, fn, fs, bold_f)
    page.insert_text((MARGIN_LEFT, FOOTER_Y), left_txt, fontname=fn, fontsize=fs)
    page.insert_text((CONTENT_X1 - w_right, FOOTER_Y), right_txt, fontname=fn, fontsize=fs)


def add_answer_key_footer(page: fitz.Page, ma_de: str, page_no: int, total_pages: int,
                          reg_f: str, bold_f: str):
    """Centered = Trang {page}/{total_pages} – Đáp án MÃ ĐỀ: {ma_de} (bold)."""
    fn = _register_font(page, bold_f, "tnrb")
    fs = 10
    txt = f"Trang {page_no}/{total_pages} \u2013 \u0110\u00e1p \u00e1n M\u00c3 \u0110\u1ec0: {ma_de}"
    w = _text_width(txt, fn, fs, bold_f)
    page.insert_text((PAGE_W / 2 - w / 2, FOOTER_Y), txt, fontname=fn, fontsize=fs)


def _insert_html_page(doc: fitz.Document, tmpdir: str, template_name: str,
                      out_index: int, **ctx) -> fitz.Page:
    """Render HTML via Playwright and append its (single) page into `doc`."""
    p_path = os.path.join(tmpdir, f"page_{out_index}.pdf")
    render_html_pdf(template_name, p_path, **ctx)
    src = fitz.open(p_path)
    doc.insert_pdf(src)
    count = src.page_count
    src.close()
    return doc[doc.page_count - 1]


def _insert_html_then_overlay(doc: fitz.Document, tmpdir: str, template_name: str,
                              img_path: str, overlay_rect, **ctx) -> fitz.Page:
    page = _insert_html_page(doc, tmpdir, template_name, doc.page_count + 1, **ctx)
    embed_image_centered(page, img_path, overlay_rect)
    return page


def _replace_first_page(doc: fitz.Document, tmpdir: str, template_name: str,
                        **ctx) -> None:
    """PASS-2 helper: re-render a single-page HTML template and swap it in as
    the document's first page.

    Used for DYNAMIC PAGINATION: the exam instruction page shows the total
    page count, which is only known AFTER all images are stacked and the
    document structure is final — so we render page 1 twice (placeholder,
    then re-render with the real count)."""
    p_path = os.path.join(tmpdir, "page_1_pass2.pdf")
    render_html_pdf(template_name, p_path, **ctx)
    src = fitz.open(p_path)
    try:
        if doc.page_count:
            doc.delete_page(0)
        doc.insert_pdf(src, start_at=0)
    finally:
        src.close()


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------
def build_exam_pdf(selection, ma_de: str, ngay_thi: str, out_path: str) -> str:
    """Assemble the 4-page exam PDF in a SINGLE Playwright render.

    Strategy: build all image-only pages first (Word/Excel/PPT previews + end
    marker) into a temp document to determine the final page count, then
    render the instruction page (exam_p1.html) exactly ONCE with the correct
    total_pages, and merge."""
    reg_f, bold_f = resolve_fonts()
    tmpdir = tempfile.mkdtemp(prefix="pdfgen_exam_")
    try:
        # ---- Pass 1: image pages only (no HTML renders) ----
        img_doc = fitz.open()
        last_page = None
        current_y = IMAGE_TOP
        for cat in ("word", "excel", "ppt"):
            page = new_a4(img_doc)
            previews = list_section_images(selection[cat]["dir"], "preview")
            last_page, current_y = stack_images(img_doc, page, previews)

        _add_exam_end_marker(img_doc, last_page, reg_f, bold_f, top_y=current_y)

        total_pages = 1 + img_doc.page_count   # +1 for instruction page

        # ---- Pass 2: render instruction page ONCE with correct count ----
        p1_pdf = render_html_pdf_bytes("exam_p1.html",
                                       ngay_thi=ngay_thi, ma_de=ma_de,
                                       tong_so_trang=total_pages)
        p1_doc = fitz.open(stream=p1_pdf, filetype="pdf")

        # ---- Merge: instruction page + image pages ----
        doc = fitz.open()
        doc.insert_pdf(p1_doc)
        p1_doc.close()
        doc.insert_pdf(img_doc)
        img_doc.close()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    # Delayed footer injection (document structure is final)
    total_pages = doc.page_count
    for i, page in enumerate(doc, start=1):
        add_exam_footer(page, ma_de, i, total_pages, reg_f, bold_f)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    doc.save(out_path, garbage=3, deflate=True)
    doc.close()
    return out_path


def _add_exam_end_marker(doc: fitz.Document, page: fitz.Page, reg_f: str,
                         bold_f: str, top_y: float = 700.0):
    """Draw the closing marker (line, -HẾT-, note) below the last stacked
    preview image. Offsets from the content bottom match Phase 4.5:
    line +24pt, "-HẾT-" +48pt, note +74pt. If the note would cross the bottom
    margin, a new page is created and the marker is placed at the fixed spot."""
    bfn = _register_font(page, bold_f, "tnrb")
    rfn = _register_font(page, reg_f, "tnr")

    # top_y already includes the trailing stack padding -> true content bottom.
    content_bottom = max(top_y - STACK_PADDING, IMAGE_TOP)
    if content_bottom + 74.0 > IMAGE_BOTTOM:
        page = new_a4(doc)
        bfn = _register_font(page, bold_f, "tnrb")
        rfn = _register_font(page, reg_f, "tnr")
        line_y, end_y, note_y = 724.0, 748.0, 774.0
    else:
        line_y = content_bottom + 24.0
        end_y = content_bottom + 48.0
        note_y = content_bottom + 74.0

    page.draw_line(fitz.Point(CONTENT_X0, line_y), fitz.Point(CONTENT_X1, line_y),
                   color=(0, 0, 0), width=1)

    end_txt = "-H\u1ebeT-"
    fs = 14
    w = _text_width(end_txt, bfn, fs, bold_f)
    page.insert_text((PAGE_W / 2 - w / 2, end_y), end_txt, fontname=bfn, fontsize=fs)

    note = "L\u01b0u \u00fd: Th\u00ed sinh n\u1ed9p l\u1ea1i \u0111\u1ec1 b\u00e0i tr\u01b0\u1edbc khi ra kh\u1ecfi ph\u00f2ng thi."
    fs2 = 11.0
    w2 = _text_width(note, rfn, fs2, reg_f)
    page.insert_text((PAGE_W / 2 - w2 / 2, note_y), note, fontname=rfn, fontsize=fs2, color=(0, 0, 0))


def build_answer_key_pdf(selection, ma_de: str, can_bo_ra_de: str, out_path: str, ngay_thi: str = "") -> str:
    reg_f, bold_f = resolve_fonts()
    doc = fitz.open()
    tmpdir = tempfile.mkdtemp(prefix="pdfgen_ak_")
    try:
        # Page 1: exact HTML header + fixed Windows rubric table (Phase 6).
        _insert_html_page(
            doc, tmpdir, "answer_key_p1.html", doc.page_count + 1,
            ma_de=ma_de, ngay_thi=ngay_thi,
        )

        # PHASE 7 (Req 2): the rubric table ends around y=350, so CONTINUE
        # stacking rubric crops on the SAME page from y=400 instead of forcing
        # a fresh page (removes the massive white gap). Strict order:
        # word_rubric -> excel_rubric -> ppt_rubric, tight bounding box for
        # EVERY image, smart page breaks (reset Y to 56.69 on overflow).
        current_page = doc[0]
        current_y = 400.0
        for cat in ("word", "excel", "ppt"):
            rubrics = list_section_images(selection[cat]["dir"], "rubric")
            current_page, current_y = stack_images(doc, current_page, rubrics,
                                                   top=current_y)

        # PHASE 7 (Req 4): signature below the last rubric, >=80pt guaranteed.
        current_page, current_y = _add_answer_key_signature(
            doc, current_page, can_bo_ra_de, reg_f, top_y=current_y)

        # PHASE 7 (Req 1+3): cleaned Appendix (title ONLY — zero instructions),
        # word preview image(s) inserted directly below the title at y=120,
        # tight bounding box, maximized within the printable box.
        _insert_html_page(doc, tmpdir, "answer_key_p4.html", doc.page_count + 1)
        appendix_page = doc[doc.page_count - 1]
        word_previews = list_section_images(selection["word"]["dir"], "preview")
        if word_previews:
            stack_images(doc, appendix_page, word_previews, top=120.0)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    # DELAYED footer injection: document structure is final at this point.
    total_pages = doc.page_count
    for i, page in enumerate(doc, start=1):
        add_answer_key_footer(page, ma_de, i, total_pages, reg_f, bold_f)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    doc.save(out_path, garbage=3, deflate=True)
    doc.close()
    return out_path


def _add_answer_key_signature(doc: fitz.Document, page: fitz.Page, can_bo_ra_de: str,
                              reg_f: str, top_y: float):
    """PHASE 7 (Req 4): signature block after the last rubric image.

    Guarantees at least 80pt of free space below the content (a fresh page is
    created otherwise), then draws the signature at 13pt Times New Roman:

        (350, top_y + 40)   -> "Cán bộ ra đáp án"
        (350, top_y + 100)  -> {can_bo_ra_de}
    """
    # The 80pt minimum check; the name line at +40+60 actually needs 100pt,
    # so the stricter bound guarantees nothing clips the bottom margin.
    if top_y + 100.0 > IMAGE_BOTTOM:
        page = new_a4(doc)
        top_y = IMAGE_TOP
    rfn = _register_font(page, reg_f, "tnr")
    fs = 13
    sig_y = top_y + 40.0
    page.insert_text((350.0, sig_y), "C\u00e1n b\u1ed9 ra \u0111\u00e1p \u00e1n",
                     fontname=rfn, fontsize=fs, color=(0, 0, 0))
    if can_bo_ra_de:
        page.insert_text((350.0, sig_y + 60.0), can_bo_ra_de,
                         fontname=rfn, fontsize=fs, color=(0, 0, 0))
    return page, sig_y + 60.0


def list_section_images(cat_dir: str, prefix: str) -> List[str]:
    """Return cropped images for a section directory, in crop order.

    Matches both the legacy single-crop file (`preview.png` / `rubric.png`)
    and the Phase-5 multi-crop files (`preview_0.png`, `preview_1.png`, ...),
    ordering numbered files by their numeric index."""
    out = []
    if not os.path.isdir(cat_dir):
        return out
    pattern = re.compile(rf"^{re.escape(prefix)}(?:_(\d+))?\.png$", re.IGNORECASE)
    for name in os.listdir(cat_dir):
        m = pattern.match(name)
        if not m:
            continue
        idx = int(m.group(1)) if m.group(1) else -1
        out.append((idx, os.path.join(cat_dir, name)))
    out.sort(key=lambda t: t[0])
    return [path for _, path in out]


def list_module_images(module_word_dir: str):
    """Return uploaded Word asset images (excludes generated preview/rubric)."""
    out = []
    if not os.path.isdir(module_word_dir):
        return out
    for name in sorted(os.listdir(module_word_dir)):
        lower = name.lower()
        if lower.startswith("preview") or lower.startswith("rubric"):
            continue
        if os.path.splitext(name)[1].lower() in IMAGE_EXTS:
            out.append(os.path.join(module_word_dir, name))
    return out