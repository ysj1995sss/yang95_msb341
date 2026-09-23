"""
The ONLY function in the entire DOCX master-template pipeline that touches
Microsoft Word. Every other module (structure extraction, LLM tailoring,
splicing, length/fabrication checks) is pure Python + python-docx object
manipulation and needs no Word installation to test. Confirmed live
(2026-09-22) that docx2pdf's Word COM automation works fine both on the
main thread and from a worker thread (FastAPI's sync-endpoint threadpool),
so no extra CoInitialize/CoUninitialize wrapping was needed on this
machine -- if that ever changes on a different environment, this is the
one place to add it.
"""

import time

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


def convert_docx_to_pdf(docx_path: str, pdf_path: str) -> None:
    try:
        from docx2pdf import convert
    except ImportError as exc:
        raise DocxConversionUnavailable(
            "docx2pdf is not installed; DOCX-to-PDF conversion is unavailable."
        ) from exc

    last_error: Exception | None = None
    for attempt in range(_MAX_ATTEMPTS):
        if attempt > 0:
            time.sleep(_RETRY_DELAY_SECONDS)
        try:
            convert(docx_path, pdf_path)
            return
        except Exception as exc:
            last_error = exc

    raise DocxConversionUnavailable(f"DOCX-to-PDF conversion failed: {last_error}") from last_error
