"""One bounded correction pass for resumes that grew past their length.

Only tailored bullets that became longer than their original are touched.
Each is shortened to at most its original length, by the model when one is
available and its output passes the fabrication check, otherwise by falling
back to the original wording, which is verified and known to fit. Fonts and
margins are never changed.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Optional, Sequence

from resume_tailorer.artifacts.models import (
    ArtifactValidation,
    ChangeCategory,
    FindingSeverity,
    ResumeChange,
)
from resume_tailorer.models import CareerTruthProfile

LENGTH_FAILURES = frozenset({"PAGE_COUNT_CHANGED", "PAGE_LIMIT_EXCEEDED"})

_CONDENSE_SYSTEM = (
    "You shorten resume bullets. Keep every fact exactly as stated. Never add, "
    "infer, or change any skill, tool, number, employer, scope, or outcome. "
    "Return only the shortened bullet, with no quotes or commentary."
)


def needs_length_correction(validation: ArtifactValidation) -> bool:
    """True when the only blocking problems are length problems."""
    failures = {f.code for f in validation.findings if f.severity is FindingSeverity.FAIL}
    return bool(failures) and failures <= LENGTH_FAILURES


def condense_bullet(
    original: str, tailored: str, profile: CareerTruthProfile, llm=None
) -> str:
    """A version of `tailored` no longer than `original`, never adding claims."""
    if len(tailored) <= len(original):
        return tailored
    if llm is not None:
        try:
            candidate = llm.complete(
                _CONDENSE_SYSTEM,
                f"Shorten to at most {len(original)} characters:\n{tailored}",
                max_tokens=200,
            ).strip().strip('"').lstrip("-*• ").strip()
        except Exception:
            candidate = ""
        if candidate and len(candidate) <= len(original) and _is_grounded(original, tailored, candidate, profile):
            return candidate
    return original


def _is_grounded(original: str, tailored: str, candidate: str, profile: CareerTruthProfile) -> bool:
    from resume_tailorer.diff_generator import DiffGenerator

    # Words already accepted in the tailored bullet are allowed to remain.
    trusted_original = f"{original} {tailored}"
    return not DiffGenerator().check_bullet_pair_fabrication_risk(trusted_original, candidate, profile)


def condense_grown_changes(
    changes: Sequence[ResumeChange], profile: CareerTruthProfile, llm=None
) -> list[ResumeChange]:
    """Shorten every change whose proposal grew past its original text."""
    condensed = []
    for change in changes:
        grew = change.original_text and change.proposed_text and len(change.proposed_text) > len(change.original_text)
        if not grew:
            condensed.append(change)
            continue
        shorter = condense_bullet(change.original_text, change.proposed_text, profile, llm)
        condensed.append(replace(
            change,
            proposed_text=shorter,
            category=ChangeCategory.UNCHANGED if shorter == change.original_text else change.category,
            reason=(change.reason + " Shortened to keep the resume within its length.").strip(),
        ))
    return condensed


def apply_condensed_text(text: str, before: Sequence[ResumeChange], after: Sequence[ResumeChange]) -> str:
    """Swap each shortened proposal into the freeform text."""
    for old, new in zip(before, after):
        if old.proposed_text != new.proposed_text and old.proposed_text in text:
            text = text.replace(old.proposed_text, new.proposed_text, 1)
    return text


def max_pages_label(target_length: str, style_hints: Optional[dict]) -> str:
    """The validator preset matching the length the user asked for."""
    from resume_tailorer.pdf.generator import PDFGenerator

    return PDFGenerator.resolve_target_length(target_length, style_hints or {})


def build_freeform_artifact(
    *,
    tailored_text: str,
    changes: Sequence[ResumeChange],
    profile: CareerTruthProfile,
    target_length: str,
    style_hints: Optional[dict],
    llm=None,
):
    """Generate and validate the freeform PDF against the requested length,
    with at most one condensation repair. Returns
    (pdf_bytes, validation, final_text, final_changes, attempts)."""
    import os
    import tempfile

    from resume_tailorer.pdf.generator import PDFGenerator
    from resume_tailorer.pdf.validator import PDFValidator

    page_target = max_pages_label(target_length, style_hints)

    def attempt(text: str, attempt_changes: Sequence[ResumeChange]):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "tailored.pdf")
            PDFGenerator().generate(
                text, profile.name, output_path=path,
                target_length=target_length, style_hints=dict(style_hints or {}),
            )
            validation = PDFValidator().validate_artifact(
                path, profile=profile, expected_page_count=None,
                accepted_changes=list(attempt_changes), target_length=page_target,
            )
            with open(path, "rb") as f:
                return f.read(), validation

    pdf_bytes, validation = attempt(tailored_text, changes)
    if not needs_length_correction(validation):
        return pdf_bytes, validation, tailored_text, list(changes), 1

    condensed = condense_grown_changes(changes, profile, llm)
    repaired_text = apply_condensed_text(tailored_text, changes, condensed)
    pdf_bytes, validation = attempt(repaired_text, condensed)
    return pdf_bytes, validation, repaired_text, condensed, 2


def correct_docx_length_once(
    *, original_docx_bytes: bytes, docx_result, profile: CareerTruthProfile, gap_report, llm=None
):
    """If the DOCX grew past its page count, shorten grown bullets and rebuild once."""
    if not needs_length_correction(docx_result.validation):
        return docx_result
    from resume_tailorer.artifacts.regeneration import regenerate_docx_artifact

    condensed = condense_grown_changes(docx_result.changes, profile, llm)
    return regenerate_docx_artifact(
        original_docx_bytes=original_docx_bytes, changes=condensed, profile=profile,
        gap_report=gap_report, convert_to_pdf=True,
    )
