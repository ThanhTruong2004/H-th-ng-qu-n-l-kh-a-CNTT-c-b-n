import asyncio
import os
import shutil
import tempfile
from pathlib import Path

from file_utils import ALLOWED_WORD_EXTS

# Limit to 3 concurrent LibreOffice processes to prevent OOM under heavy
# concurrent Word uploads (AUDIT-23 Fix 4). Each LO instance consumes
# ~800MB RAM; 20 concurrent = 16GB which would crash the server.
_lo_semaphore = asyncio.Semaphore(3)


async def convert_docx_to_pdf(docx_bytes: bytes, original_filename: str = "document.docx") -> bytes:
    """Convert a Microsoft Word document (.doc/.docx) to PDF bytes.

    Drives `libreoffice --headless --convert-to pdf` via asyncio subprocess so
    the event loop is never blocked while LibreOffice spins up. The input is
    written to a temp file (keeping the original extension so LibreOffice picks
    the right import filter) and the converted PDF is read back to bytes.
    """
    async with _lo_semaphore:
        if not docx_bytes:
            raise ValueError("Empty document bytes")
        suffix = Path(original_filename or "document.docx").suffix.lower() or ".docx"
        if suffix not in ALLOWED_WORD_EXTS:
            # Not a Word document — return as-is (caller should normally not send
            # PDFs here, but be tolerant).
            return docx_bytes

        tmp_dir = tempfile.mkdtemp(prefix="lo_conv_")
        home_dir = tempfile.mkdtemp(prefix="lo_home_")
        tmp_in = os.path.join(tmp_dir, "input" + suffix)
        try:
            with open(tmp_in, "wb") as f:
                f.write(docx_bytes)

            cmd = [
                "libreoffice",
                "--headless",
                "--norestore",
                "--nologo",
                f"-env:UserInstallation=file://{home_dir}/profile",
                "--convert-to", "pdf",
                "--outdir", tmp_dir,
                tmp_in,
            ]
            env = {**os.environ, "HOME": home_dir}
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                raise RuntimeError("LibreOffice conversion timed out after 120s")

            if proc.returncode != 0:
                details = (stderr or b"").decode("utf-8", errors="replace").strip()
                raise RuntimeError(
                    f"LibreOffice conversion failed (rc={proc.returncode}): {details or 'unknown error'}"
                )

            out_pdf = os.path.join(tmp_dir, "input.pdf")
            if not os.path.isfile(out_pdf):
                raise RuntimeError("LibreOffice did not produce a PDF output")
            with open(out_pdf, "rb") as f:
                pdf_bytes = f.read()
            # AUDIT-24 LE-5: LibreOffice's --convert-to emits a valid PDF even
            # for an empty/corrupt Word file. A sub-1000-byte "successful" PDF
            # is degenerate — reject it so the downstream cropper never chokes.
            if len(pdf_bytes) < 1000:
                raise ValueError("Word document appears to be empty or corrupted")
            return pdf_bytes
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            shutil.rmtree(home_dir, ignore_errors=True)