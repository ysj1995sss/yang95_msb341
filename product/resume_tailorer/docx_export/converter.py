"""
DOCX to PDF, the only step in the DOCX master-template pipeline that needs an
office suite. Every other module (structure extraction, LLM tailoring, splicing,
length/fabrication checks) is pure Python + python-docx.

Two converters, tried in order:
1. Microsoft Word through docx2pdf, on Windows and macOS where Word exists.
2. LibreOffice (`soffice --headless`), everywhere else, which is how the Linux
   server (Streamlit Community Cloud) converts: `packages.txt` installs it with
   metric-compatible fonts (decision 027). Before this, a Word resume produced no
   PDF there, so it could never be handed to Apply.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# docx2pdf's convert() calls word.Quit() after each conversion, then the
# NEXT convert() call's win32com.client.Dispatch("Word.Application")
# reconnects to that same Word process via the Running Object Table before
# it has fully torn down -- confirmed live (2026-09-22) by direct, reliable
# reproduction: two convert() calls back-to-back in the same process fail
# the second time with `AttributeError: Open.SaveAs` every time, and adding
# a short delay between them reliably fixes it every time. This pipeline
# always converts an original and a tailored doc back-to-back per request,
# so a retry-with-delay is a real, warranted fix here (a genuine async
# COM-cleanup race), not a band-aid for unexplained behavior.
_RETRY_DELAY_SECONDS = 2.0
_MAX_ATTEMPTS = 2


class DocxConversionUnavailable(RuntimeError):
    """Raised when docx2pdf isn't installed, or the underlying Word/
    AppleScript automation fails (no Word installed, COM error, running on
    Linux, etc.) -- callers treat this as "PDF/page-count verification
    unavailable," never as a reason to fail the whole tailoring request."""


_LIBREOFFICE_TIMEOUT_SECONDS = 120
_WINDOWS_SOFFICE = (
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
)


def _word_platform() -> bool:
    return sys.platform in ("win32", "darwin")


def _soffice() -> str | None:
    found = shutil.which("soffice") or shutil.which("libreoffice")
    if found:
        return found
    return next((p for p in _WINDOWS_SOFFICE if os.path.isfile(p)), None)


def convert_docx_to_pdf(docx_path: str, pdf_path: str) -> None:
    """Word where it exists, otherwise LibreOffice. Raises DocxConversionUnavailable
    only when neither can convert."""
    word_error: Exception | None = None
    if _word_platform():
        try:
            _convert_with_word(docx_path, pdf_path)
            return
        except DocxConversionUnavailable as exc:
            word_error = exc
    soffice = _soffice()
    if soffice is None:
        raise word_error or DocxConversionUnavailable(
            "No converter for Word files here: install LibreOffice (packages.txt on Streamlit Cloud)."
        )
    _convert_with_libreoffice(soffice, docx_path, pdf_path)


def _convert_with_libreoffice(soffice: str, docx_path: str, pdf_path: str) -> None:
    with tempfile.TemporaryDirectory() as work:
        # A private profile per call: concurrent sessions would otherwise fight over one lock.
        profile = Path(work, "profile").as_uri()
        out_dir = Path(work, "out")
        command = [soffice, "--headless", "--norestore", f"-env:UserInstallation={profile}",
                   "--convert-to", "pdf", "--outdir", str(out_dir), str(docx_path)]
        try:
            result = subprocess.run(command, capture_output=True, text=True,
                                    timeout=_LIBREOFFICE_TIMEOUT_SECONDS, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise DocxConversionUnavailable(f"LibreOffice could not convert the resume: {exc}") from exc
        produced = out_dir / (Path(docx_path).stem + ".pdf")
        if not produced.is_file():
            detail = (result.stderr or result.stdout or "no output").strip()[:200]
            raise DocxConversionUnavailable(f"LibreOffice could not convert the resume: {detail}")
        shutil.move(str(produced), pdf_path)


def _convert_with_word(docx_path: str, pdf_path: str) -> None:
    try:
        from docx2pdf import convert
    except ImportError as exc:
        raise DocxConversionUnavailable(
            "docx2pdf is not installed; DOCX-to-PDF conversion is unavailable."
        ) from exc

    # Word automation (COM) must be initialized on the thread that uses it.
    # Found live (2026-09-30): the first build worked, but a rebuild triggered
    # from a Streamlit callback ran on another thread and failed with
    # "CoInitialize has not been called". Harmless when already initialized.
    try:
        import pythoncom
    except ImportError:
        pythoncom = None
    if pythoncom is not None:
        pythoncom.CoInitialize()
    try:
        last_error: Exception | None = None
        for attempt in range(_MAX_ATTEMPTS):
            if attempt > 0:
                time.sleep(_RETRY_DELAY_SECONDS)
            try:
                convert(docx_path, pdf_path)
                return
            except Exception as exc:
                last_error = exc
    finally:
        if pythoncom is not None:
            pythoncom.CoUninitialize()

    raise DocxConversionUnavailable(f"DOCX-to-PDF conversion failed: {last_error}") from last_error
