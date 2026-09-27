"""Soft (non-blocking) per-bullet checks for the DOCX splice pipeline.

bullet_length_delta itself now lives in utils/length_check.py, shared with
the freeform/PDF tailoring path's diff_generator.py -- re-exported here so
existing callers/imports of this module keep working unchanged.
"""

from resume_tailorer.utils.length_check import bullet_length_delta

__all__ = ["bullet_length_delta"]
