"""Render the exact PDF artifact as page images, so the preview shows the
resume's own typography rather than a re-typeset copy."""

from __future__ import annotations

import hashlib
from functools import lru_cache


@lru_cache(maxsize=16)
def _render(digest: str, pdf_bytes: bytes, zoom: float) -> tuple[bytes, ...]:
    try:
        import pymupdf
    except ImportError:  # older PyMuPDF installs only expose `fitz`
        import fitz as pymupdf

    pages = []
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            pages.append(page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).tobytes("png"))
    return tuple(pages)


def pdf_page_images(pdf_bytes: bytes, zoom: float = 1.6) -> tuple[bytes, ...]:
    """PNG bytes for each page. Empty tuple when the PDF can't be rendered."""
    if not pdf_bytes:
        return ()
    try:
        return _render(hashlib.sha256(pdf_bytes).hexdigest(), pdf_bytes, zoom)
    except Exception:
        return ()
