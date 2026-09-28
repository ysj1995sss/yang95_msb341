"""Deterministic render and geometry comparison for resume PDFs."""

from __future__ import annotations

from itertools import combinations

import fitz

from resume_tailorer.artifacts.models import (
    FindingCategory,
    FindingSeverity,
    ValidationFinding,
)


_PIXEL_THRESHOLD = 16
_MAX_OUTSIDE_DIFF_RATIO = 0.0025
_EDIT_PADDING = 3.0


def _failure(code: str, message: str, **details) -> ValidationFinding:
    return ValidationFinding(code, FindingSeverity.FAIL, FindingCategory.VISUAL, message, details)


def _inside_edit(x: int, y: int, regions: list[tuple[float, float, float, float]]) -> bool:
    return any(
        left - _EDIT_PADDING <= x <= right + _EDIT_PADDING
        and top - _EDIT_PADDING <= y <= bottom + _EDIT_PADDING
        for left, top, right, bottom in regions
    )


def _geometry_findings(page: fitz.Page, page_index: int) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    page_rect = page.rect
    blocks = [fitz.Rect(block[:4]) for block in page.get_text("blocks") if block[4].strip()]
    if any(not page_rect.contains(block) for block in blocks):
        findings.append(_failure("CLIPPED_TEXT", "Text extends outside the PDF page bounds.",
                                 page=page_index + 1))
    for first, second in combinations(blocks, 2):
        overlap = first & second
        if overlap.get_area() > 1.0:
            findings.append(_failure("TEXT_OVERLAP", "Text blocks overlap in the rendered PDF.",
                                     page=page_index + 1))
            break
    return findings

def compare_pdf_renders(
    original_pdf_path: str,
    tailored_pdf_path: str,
    edited_regions: list[tuple[float, float, float, float]],
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    with fitz.open(original_pdf_path) as original, fitz.open(tailored_pdf_path) as tailored:
        if len(original) != len(tailored):
            return [_failure("PAGE_COUNT_CHANGED", "The rendered PDF page count changed.",
                             original=len(original), tailored=len(tailored))]

        for page_index, (original_page, tailored_page) in enumerate(zip(original, tailored)):
            if (
                abs(original_page.rect.width - tailored_page.rect.width) > 0.5
                or abs(original_page.rect.height - tailored_page.rect.height) > 0.5
            ):
                findings.append(_failure("PAGE_DIMENSIONS_CHANGED",
                                         "The rendered PDF page dimensions changed.",
                                         page=page_index + 1))
                continue

            findings.extend(_geometry_findings(tailored_page, page_index))
            original_pix = original_page.get_pixmap(colorspace=fitz.csGRAY, alpha=False)
            tailored_pix = tailored_page.get_pixmap(colorspace=fitz.csGRAY, alpha=False)
            if (original_pix.width, original_pix.height) != (tailored_pix.width, tailored_pix.height):
                findings.append(_failure("PAGE_DIMENSIONS_CHANGED",
                                         "Rendered page pixel dimensions changed.",
                                         page=page_index + 1))
                continue

            outside_differences = 0
            for offset, (old, new) in enumerate(zip(original_pix.samples, tailored_pix.samples)):
                if abs(old - new) <= _PIXEL_THRESHOLD:
                    continue
                x = offset % original_pix.width
                y = offset // original_pix.width
                if not _inside_edit(x, y, edited_regions):
                    outside_differences += 1
            total_pixels = original_pix.width * original_pix.height
            ratio = outside_differences / total_pixels if total_pixels else 0.0
            if ratio > _MAX_OUTSIDE_DIFF_RATIO:
                findings.append(_failure("LAYOUT_DRIFT_OUTSIDE_EDIT",
                                         "Rendered differences extend beyond approved edit regions.",
                                         page=page_index + 1,
                                         outside_diff_ratio=ratio))
    return findings
