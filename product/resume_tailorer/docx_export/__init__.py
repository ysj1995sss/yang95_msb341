"""
DOCX master-template export pipeline: splices LLM-tailored bullet text
into the ORIGINAL uploaded .docx's own paragraphs (never regenerates a
document from scratch), then converts to PDF for a human-readable file and
a hard page-count check. See pipeline.py for the single entry point.
"""

from .pipeline import run_docx_tailoring_pipeline, DocxTailoringResult
from .converter import DocxConversionUnavailable

__all__ = ["run_docx_tailoring_pipeline", "DocxTailoringResult", "DocxConversionUnavailable"]
