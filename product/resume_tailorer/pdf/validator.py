"""
PDF Validator — round-trip validation hard gate.

Per the MVP's global constraints, generated resume PDFs must be text-based
and ATS-readable. This validator extracts text back out of a generated PDF
(round-trip) and checks that:

1. Text is actually extractable (non-empty) — confirms the PDF is not
   image-based.
2. Page count is reasonable for a resume (1-2 pages for MVP); more is
   flagged as an issue, not silently accepted.
3. The extracted text isn't dominated by garbage/control characters,
   which would indicate corruption or a broken encoding.

This is a HARD GATE: if generation produces a broken PDF, validate()
must return passed=False with details in `issues`, so the caller can
regenerate rather than ship it.
"""

import os
import re
from dataclasses import dataclass, field

from pypdf import PdfReader


@dataclass
class ValidationResult:
    """Result of validating a generated PDF."""

    passed: bool
    page_count: int
    extracted_text: str
    issues: list = field(default_factory=list)


class PDFValidator:
    """Validates generated resume PDFs via round-trip text extraction."""

    MIN_TEXT_LENGTH = 50
    # Fraction of extracted characters that must be "normal" (alnum,
    # whitespace, or common punctuation) for the text to be considered
    # readable rather than garbage/corrupted.
    MIN_READABLE_RATIO = 0.85

    TARGET_LENGTH_MAX_PAGES = {
        "1_page": 1,
        "2_page": 2,
        "preserve": 10,
    }

    def __init__(self, max_pages: int = 2):
        # Vestigial: the page limit is now resolved entirely from
        # target_length via TARGET_LENGTH_MAX_PAGES. Kept so existing
        # callers doing PDFValidator(max_pages=N) keep working.
        self.max_pages = max_pages

    def validate(self, pdf_path: str, target_length: str = "1_page") -> ValidationResult:
        """
        Validate a generated PDF via round-trip text extraction.

        Args:
            pdf_path: Path to the PDF file to validate.
            target_length: One of "1_page" (default), "2_page", "preserve".
                Determines the page-count limit used for the overflow check.
                Must be one of those three values; any other string raises
                ValueError (matching PDFGenerator's behavior) rather than
                silently falling back to a default limit.

        Returns:
            ValidationResult with passed/page_count/extracted_text/issues.

        Raises:
            ValueError: If target_length is not a recognized value.
        """
        if target_length not in self.TARGET_LENGTH_MAX_PAGES:
            raise ValueError(
                f"Unknown target_length '{target_length}'. "
                f"Must be one of: {list(self.TARGET_LENGTH_MAX_PAGES.keys())}"
            )
        effective_max_pages = self.TARGET_LENGTH_MAX_PAGES[target_length]
        issues = []

        if not pdf_path or not os.path.exists(pdf_path):
            return ValidationResult(
                passed=False,
                page_count=0,
                extracted_text="",
                issues=[f"File not found: {pdf_path}"],
            )

        try:
            reader = PdfReader(pdf_path)
        except Exception as exc:
            return ValidationResult(
                passed=False,
                page_count=0,
                extracted_text="",
                issues=[f"Could not open PDF (corrupt or invalid file): {exc}"],
            )

        page_count = len(reader.pages)

        if page_count == 0:
            issues.append("PDF has 0 pages.")
            return ValidationResult(
                passed=False, page_count=0, extracted_text="", issues=issues
            )

        extracted_text = ""
        for page in reader.pages:
            try:
                extracted_text += (page.extract_text() or "") + "\n"
            except Exception as exc:
                issues.append(f"Failed to extract text from a page: {exc}")

        stripped = extracted_text.strip()

        # Check 1: text must be extractable (not empty / not image-based)
        if not stripped:
            issues.append(
                "No extractable text found — PDF may be image-based or empty, "
                "which is not ATS-readable."
            )
        elif len(stripped) < self.MIN_TEXT_LENGTH:
            issues.append(
                f"Extracted text is too short ({len(stripped)} chars) to be a "
                "credible resume — possible corruption."
            )

        # Check 2: page count reasonable for MVP (1-2 pages)
        if page_count > effective_max_pages:
            issues.append(
                f"PDF has {page_count} pages, exceeding the MVP target of "
                f"{effective_max_pages} page(s)."
            )

        # Check 3: no obvious corruption — extracted text shouldn't be
        # dominated by garbage/control characters.
        if stripped and not self._is_readable(stripped):
            issues.append(
                "Extracted text appears to be garbage/corrupted (dominated by "
                "non-readable characters)."
            )

        passed = len(issues) == 0

        return ValidationResult(
            passed=passed,
            page_count=page_count,
            extracted_text=extracted_text,
            issues=issues,
        )

    def _is_readable(self, text: str) -> bool:
        """Heuristic: most characters should be alphanumeric, whitespace,
        or common punctuation. A PDF with corrupted text extraction tends
        to produce a high proportion of control characters or symbol soup.
        """
        if not text:
            return False

        normal_pattern = re.compile(r"[A-Za-z0-9\s.,;:!?'\"()/@\-&%$#+]")
        normal_count = len(normal_pattern.findall(text))
        ratio = normal_count / len(text)
        return ratio >= self.MIN_READABLE_RATIO
