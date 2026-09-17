"""
PDF package - text-based resume PDF generation and round-trip validation.

Provides PDFGenerator for producing ATS-readable, text-based PDFs from
tailored resume text, and PDFValidator for the hard-gate round-trip
validation (extract text back out and verify it is readable and
well-formed) required before a generated PDF can ship.
"""

from .generator import PDFGenerator
from .validator import PDFValidator, ValidationResult

__all__ = ["PDFGenerator", "PDFValidator", "ValidationResult"]
