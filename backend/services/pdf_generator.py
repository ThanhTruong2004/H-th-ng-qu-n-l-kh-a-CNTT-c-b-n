"""PDF assembly engine for DLU IT Exam Generation (Phase 2).

Renders Jinja2 templates (exam_p1 / answer_key_p1 / answer_key_p4) to PDF via
Playwright Chromium, then stitches the sliced images (Phase 1) with PyMuPDF
(fitz) and injects uniform footers.
"""

import atexit
import io
import os
import queue
import re
import threading
import time
from typing import List, Tuple

import fitz
from PIL import Image
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

from file_utils import UPLOAD_DIR, format_ngay_thi

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
# Dedicated render thread — Playwright sync API is pinned to ONE thread.
# Calls via run_in_threadpool() can land on different anyio pool threads; using
# sync_playwright from a different thread than the one that started it raises
# 'greenlet.error: cannot switch to a different thread'. Routing every render
# through this single worker makes generation deterministic (Phase 13.1).
# ---------------------------------------------------------------------------
_render_queue = queue.Queue()
_render_worker = None
_render_worker_lock = threading.Lock()
_pw = None       # sync Playwright instance (owned by the render thread)
_browser = None  # sync Browser object (owned by the render thread)

# Chromium memory-leak restart (AUDIT-23 Fix 5): the long-lived singleton's
# footprint grows over ~10h uptime (500MB-1GB). Force a clean relaunch every
# hour to bound memory.
_browser_launch_time = 0.0
_BROWSER_MAX_AGE = 3600  # seconds (1 hour)


def _ensure_render_worker():
    global _render_worker
    with _render_worker_lock:
        if _render_worker is not None:
            return
        def _render_loop():
            while True:
                fn, args, kwargs, resp_q = _render_queue.get()
                if fn is None:
                    resp_q.put(None)
                    return
                try:
                    resp_q.put(("ok", fn(*args, **kwargs), None))
                except BaseException as e:  # noqa: BLE001
                    resp_q.put(("err", None, e))
        _render_worker = threading.Thread(
            target=_render_loop, name="pdf-render-worker", daemon=True,
        )
        _render_worker.start()


def _call_render(fn, *args, **kwargs):
    """Submit a render callable to the single worker thread and wait."""
    _ensure_render_worker()
    resp_q = queue.Queue()
    _render_queue.put((fn, args, kwargs, resp_q))
    status, result, exc = resp_q.get()
    if status == "err":
        raise exc
    return result


def _ensure_browser():
    """Return the live browser, launching lazily on first call.

    IMPORTANT: only ever called from the dedicated pdf-render-worker thread —
    never from request/anyio threads."""
    global _pw, _browser, _browser_launch_time
    # AUDIT-23 Fix 5: force a clean relaunch once the current Chromium has
    # been alive for more than an hour (bounded memory regardless of leaks).
    if _browser is not None and time.time() - _browser_launch_time > _BROWSER_MAX_AGE:
        try:
            _browser.close()
        except Exception:
            pass
        _browser = None
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
    _browser_launch_time = time.time()
    return _browser


def shutdown_browser():
    """Tear down the browser on app shutdown (called from the main thread, so
    Playwright errors are swallowed — the process is exiting anyway)."""
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


def _render_inline(template_name, out_path, as_bytes, **ctx):
    """Actual Playwright render — executes only on the dedicated render thread."""
    html = _env().get_template(template_name).render(**ctx)
    browser = _ensure_browser()
    context = browser.new_context()
    page = context.new_page()
    try:
        page.set_content(html, wait_until="load")
        if as_bytes:
            return page.pdf(format="A4", print_background=True,
                            prefer_css_page_size=True)
        page.pdf(path=out_path, format="A4", print_background=True,
                 prefer_css_page_size=True)
        return out_path
    finally:
        page.close()
        context.close()


def render_html_pdf(template_name: str, out_path: str, **ctx) -> str:
    """Render a Jinja2 template to a PDF page. Runs on the dedicated render
    thread (single Chromium process reused across all renders)."""
    return _call_render(_render_inline, template_name, out_path, False, **ctx)


def render_html_pdf_bytes(template_name: str, **ctx) -> bytes:
    """Like render_html_pdf but returns raw PDF bytes (no temp file needed).
    Used by single-pass assembly to avoid writing+reading a temp file."""
    return _call_render(_render_inline, template_name, None, True, **ctx)


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


def _compress_image_cached(img_bytes: bytes, img_path: str, cache: dict) -> bytes:
    """Compress with a per-build dictionary cache keyed by file path (PERF-002).

    The same cropped image can be processed more than once during one assembly
    (stacking / fit embedding). Reusing the compressed bytes avoids repeatedly
    running the JPEG encoder on identical data. If `cache` is None the original
    (uncached) behaviour is preserved."""
    if cache is None:
        return _compress_image(img_bytes)
    cached = cache.get(img_path)
    if cached is None:
        cached = _compress_image(img_bytes)
        cache[img_path] = cached
    return cached


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
                    bottom: float = IMAGE_BOTTOM, cache: dict = None) -> float:
    """Insert a single cropped image with a TIGHT, TOP-ANCHORED rectangle.

    PyMuPDF never auto-centers (no keep_proportion) — the image fills the tight
    rect exactly, anchored to the top-left margin. Returns the Y after image."""
    final_w, final_h = get_image_fit_size(img_path, top=top, bottom=bottom)
    if final_w <= 0 or final_h <= 0:
        return top
    with open(img_path, "rb") as f:
        raw_bytes = f.read()
    img_bytes = _compress_image_cached(raw_bytes, img_path, cache)
    tight_rect = fitz.Rect(IMAGE_X0, top, IMAGE_X0 + final_w, top + final_h)
    page.insert_image(tight_rect, stream=img_bytes)
    return top + final_h


def stack_images(doc: fitz.Document, page: fitz.Page, img_paths,
                 top: float = IMAGE_TOP, bottom: float = IMAGE_BOTTOM,
                 padding: float = STACK_PADDING, cache: dict = None,
                 max_w_override: float = None):
    """PHASE 8 MAX-WIDTH-FIRST STACKING with SMART PAGINATION.

    Rewritten from the old window-ratio fit (which could SQUASH an image into
    a microscopic dot when it was inserted near the bottom of a page). Every
    image is now:

        1. Scaled to fill the maximum horizontal width (453.55pt).
        2. Reduced to one page ONLY if it is taller than a full A4 page.
        3. Inserted on a NEW page if it cannot fit in the REMAINING space
           (guard: never break when already at the top of a fresh page).
        4. Top-anchored, keep_proportion, at 85.04 with 20pt padding after.

    AUDIT-25 (Req 3): `max_w_override` lets callers widen the stacking box
    (e.g. answer-key rubrics expanding to a 0.5cm right margin). Falls back to
    the standard printable width when None.

    Returns (last_page, current_y) where current_y is the Y right after the
    last placed image (image bottom + padding)."""
    max_w = max_w_override or (IMAGE_RIGHT - IMAGE_X0)   # 453.55 default
    max_h_full_page = IMAGE_BOTTOM - IMAGE_TOP     # 723.31
    current_y = top
    for img_path in img_paths:
        if not os.path.exists(img_path):
            continue
        with open(img_path, "rb") as f:
            raw_bytes = f.read()
        img_bytes = _compress_image_cached(raw_bytes, img_path, cache)
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


def _render_html_src(template_name: str, out_index: int, **ctx) -> fitz.Document:
    """Render an HTML template to a fully in-memory source document.

    No temp file is written — the Playwright render returns raw bytes which are
    opened via fitz.open(stream=...) (Phase 19 removes the unused tmpdir disk
    I/O; byte-for-byte identical to the old write-then-read path). The caller
    keeps this document open until AFTER the final save (Phase 13.1)."""
    p_bytes = render_html_pdf_bytes(template_name, **ctx)
    return fitz.open(stream=p_bytes, filetype="pdf")


def _insert_html_page(doc: fitz.Document, template_name: str,
                      out_index: int, srcs: list = None, **ctx) -> fitz.Page:
    """Render HTML via Playwright and append its (single) page into `doc`.

    If `srcs` (a list) is provided the source document is appended to it so the
    caller can close it AFTER `doc` has been saved — preventing stream
    corruption from a premature `close()` (Phase 13.1). Otherwise the source is
    closed immediately (legacy callers)."""
    src = _render_html_src(template_name, out_index, **ctx)
    if srcs is not None:
        srcs.append(src)
    try:
        doc.insert_pdf(src)
    except Exception:
        if srcs is None:
            src.close()
        raise
    if srcs is None:
        src.close()
    return doc[doc.page_count - 1]


def _insert_html_then_overlay(doc: fitz.Document, template_name: str,
                              img_path: str, overlay_rect, **ctx) -> fitz.Page:
    page = _insert_html_page(doc, template_name, doc.page_count + 1, **ctx)
    embed_image_centered(page, img_path, overlay_rect)
    return page


def _replace_first_page(doc: fitz.Document, template_name: str, **ctx) -> None:
    """PASS-2 helper: re-render a single-page HTML template and swap it in as
    the document's first page.

    Used for DYNAMIC PAGINATION: the exam instruction page shows the total
    page count, which is only known AFTER all images are stacked and the
    document structure is final — so we render page 1 twice (placeholder,
    then re-render with the real count)."""
    src = _render_html_src(template_name, 0, **ctx)
    try:
        if doc.page_count:
            doc.delete_page(0)
        doc.insert_pdf(src, start_at=0)
    finally:
        src.close()


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------
def build_exam_pdf(selection, ma_de: str, ngay_thi: str, out_path: str,
                   compression_cache: dict = None) -> str:
    """Assemble the 4-page exam PDF in a SINGLE Playwright render.

    Strategy: build all image-only pages first (Word/Excel/PPT previews + end
    marker) into a temp document to determine the final page count, then
    render the instruction page (exam_p1.html) exactly ONCE with the correct
    total_pages, and merge.

    Phase 13.1 lifecycle: img_doc and p1_doc stay OPEN until AFTER
    doc.save() completes — closing a source document before the main save can
    drop its internal stream references and render images as blue/blank boxes.
    """
    reg_f, bold_f = resolve_fonts()
    img_doc = fitz.open()       # source doc — closed ONLY after final save
    doc = fitz.open()           # final container doc
    p1_doc = None               # source doc — closed ONLY after final save
    cache = compression_cache if compression_cache is not None else {}  # PERF-002
    try:
        # ---- Pass 1: image pages only (no HTML renders) ----
        last_page = None
        current_y = IMAGE_TOP
        for cat in ("word", "excel", "ppt"):
            page = new_a4(img_doc)
            previews = list_section_images(selection[cat]["dir"], "preview")
            last_page, current_y = stack_images(img_doc, page, previews, cache=cache)

            # AUDIT-27 (Req 1): inject the exam-scope "LƯU Ý" note immediately
            # below the Word section's preview images.  Use insert_htmlbox to
            # support <b>, <u>, and <li> formatting (plain insert_textbox
            # cannot render rich text).
            if cat == "word":
                note_html = (
                    '<p style="margin:0; font-size:11pt;">'
                    '<b><u>Lưu ý:</u></b>'
                    '</p>'
                    '<ul style="margin:4pt 0 0 0; padding-left:18pt; font-size:11pt;">'
                    '<li>Thí sinh làm bài trên 1 trang A4, font chữ Times New Roman, cỡ chữ 13.</li>'
                    '<li>Lề giấy trên, dưới, phải: 1,5cm; trái: 3cm</li>'
                    '</ul>'
                )
                note_y = current_y + 24.0
                note_rect = fitz.Rect(MARGIN_LEFT, note_y, IMAGE_RIGHT, note_y + 80)
                last_page.insert_htmlbox(
                    note_rect,
                    note_html,
                    css="body { font-family: tiro; font-size: 11pt; color: black; text-align: left; }",
                )

        _add_exam_end_marker(img_doc, last_page, reg_f, bold_f, top_y=current_y)

        total_pages = 1 + img_doc.page_count   # +1 for instruction page

        # ---- Pass 2: render instruction page ONCE with correct count ----
        p1_pdf = render_html_pdf_bytes("exam_p1.html",
                                       ngay_thi=ngay_thi, ma_de=ma_de,
                                       tong_so_trang=total_pages)
        p1_doc = fitz.open(stream=p1_pdf, filetype="pdf")

        # ---- Merge: instruction page + image pages ----
        doc.insert_pdf(p1_doc)
        doc.insert_pdf(img_doc)

        # Delayed footer injection (document structure is final)
        total_pages = doc.page_count
        for i, page in enumerate(doc, start=1):
            add_exam_footer(page, ma_de, i, total_pages, reg_f, bold_f)

        # Save the MAIN document FIRST — sources may only close afterwards.
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        doc.save(out_path, garbage=3, deflate=True)
        return out_path
    finally:
        if p1_doc is not None:
            p1_doc.close()
        img_doc.close()
        doc.close()


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


def build_answer_key_pdf(selection, ma_de: str, can_bo_ra_de: str, out_path: str,
                         ngay_thi: str = "", compression_cache: dict = None) -> str:
    """Assemble the answer-key PDF.

    Phase 13.1 lifecycle: every Playwright-rendered source document (the
    answer_key_p1 and answer_key_p4 pages) stays OPEN until AFTER doc.save()
    completes so no internal image/stream references are dropped early."""
    # AUDIT-26 (Req 2): explicitly format the date before rendering so the
    # answer key header always shows DD/MM/YYYY regardless of input format.
    ngay_thi = format_ngay_thi(ngay_thi) if ngay_thi else ""
    reg_f, bold_f = resolve_fonts()
    doc = fitz.open()           # final container doc
    html_sources = []           # source docs — closed ONLY after final save
    cache = compression_cache if compression_cache is not None else {}  # PERF-002
    try:
        # Page 1: exact HTML header + fixed Windows rubric table (Phase 6).
        _insert_html_page(
            doc, "answer_key_p1.html", doc.page_count + 1,
            html_sources, ma_de=ma_de, ngay_thi=ngay_thi,
        )

        # AUDIT-27 (Req 3): measure the rendered HTML page so rubrics start
        # exactly where the fixed Windows rubric table ends.  Filter out
        # invisible page-level bounding boxes so only real content drives Y.
        html_page = doc[0]
        blocks = html_page.get_text("blocks")

        CONTENT_TOP = 56.69
        FOOTER_ZONE = PAGE_H - 80
        visible_blocks = [
            b for b in blocks
            if b[3] < FOOTER_ZONE and b[1] >= CONTENT_TOP - 10 and b[4].strip()
        ]

        if visible_blocks:
            content_bottom_y = max(b[3] for b in visible_blocks)
        else:
            content_bottom_y = 380.0

        # Clamp strictly so rubrics never force a jump to page 2 initially.
        current_y = min(content_bottom_y + 20.0, 500.0)
        current_page = doc[0]

        # Strict order: word_rubric -> excel_rubric -> ppt_rubric, tight
        # bounding box for EVERY image, smart page breaks (reset Y to 56.69 on
        # overflow).
        # AUDIT-25 (Req 3): rubrics expand to 0.5cm right margin (tighter layout).
        RUBRIC_RIGHT = PAGE_W - 28.35      # 0.5cm right margin
        for cat in ("word", "excel", "ppt"):
            rubrics = list_section_images(selection[cat]["dir"], "rubric")
            current_page, current_y = stack_images(doc, current_page, rubrics,
                                                   top=current_y, padding=8.0,
                                                   cache=cache,
                                                   max_w_override=RUBRIC_RIGHT - IMAGE_X0)

        # PHASE 7 (Req 4): signature below the last rubric, >=80pt guaranteed.
        current_page, current_y = _add_answer_key_signature(
            doc, current_page, can_bo_ra_de, reg_f, bold_f, top_y=current_y)

        # PHASE 7 (Req 1+3): cleaned Appendix (title ONLY — zero instructions),
        # word preview image(s) inserted directly below the title at y=120,
        # tight bounding box, maximized within the printable box.
        _insert_html_page(doc, "answer_key_p4.html", doc.page_count + 1,
                          html_sources)
        appendix_page = doc[doc.page_count - 1]
        word_previews = list_section_images(selection["word"]["dir"], "preview")
        if word_previews:
            stack_images(doc, appendix_page, word_previews, top=120.0, cache=cache)

        # DELAYED footer injection: document structure is final at this point.
        total_pages = doc.page_count
        for i, page in enumerate(doc, start=1):
            add_answer_key_footer(page, ma_de, i, total_pages, reg_f, bold_f)

        # Save the MAIN document FIRST — sources may only close afterwards.
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        doc.save(out_path, garbage=3, deflate=True)
        return out_path
    finally:
        for src in html_sources:
            src.close()
        doc.close()


def _add_answer_key_signature(doc: fitz.Document, page: fitz.Page, can_bo_ra_de: str,
                              reg_f: str, bold_f: str, top_y: float):
    """PHASE 7 (Req 4) + AUDIT-27 (Req 4): signature block after the last
    rubric image.  110pt signing gap, name in regular weight.

    Layout guarantee: at least 180pt free space below `top_y`, otherwise a
    fresh page is created.

        (350, top_y + 50)    -> "Cán bộ ra đáp án"  (regular)
        (350, top_y + 160)   -> {can_bo_ra_de}       (regular, 110pt gap)
    """
    # AUDIT-27 Req 4: 180pt = 50 (label) + 110 (signing gap) + 20 (trailing)
    # so the physical signature never clips the bottom margin.
    if top_y + 180.0 > IMAGE_BOTTOM:
        page = new_a4(doc)
        top_y = IMAGE_TOP

    rfn = _register_font(page, reg_f, "tnr")
    fs = 13

    label_y = top_y + 50.0
    page.insert_text((350.0, label_y), "C\u00e1n b\u1ed9 ra \u0111\u00e1p \u00e1n",
                     fontname=rfn, fontsize=fs, color=(0, 0, 0))

    if can_bo_ra_de:
        # AUDIT-27 Req 4: name uses regular font (rfn) for visual consistency
        # with the label, at an expanded 110pt physical signing gap.
        name_y = label_y + 110.0
        page.insert_text((350.0, name_y), can_bo_ra_de,
                         fontname=rfn, fontsize=fs, color=(0, 0, 0))
        return page, name_y + 20.0
    return page, label_y + 20.0


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