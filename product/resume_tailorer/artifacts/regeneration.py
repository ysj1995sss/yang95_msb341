"""Regenerate a tailoring run's artifact from its REVIEWED change
dispositions -- never by re-invoking the LLM tailorer, which would
produce different, unreviewed text and silently discard a user's
accept/reject/restore/manual-edit decisions (spec 002 section 10).

Lives in product/ (not an API-layer module) because it has zero
dependency on FastAPI/SQLAlchemy -- shared by apps/api's regeneration
endpoint AND the Streamlit review UI (Task 8), matching decision 014's
"one shared pipeline, adapters don't reimplement" principle.
"""

from __future__ import annotations

import io
import os
import tempfile
from typing import Sequence

from docx import Document

from resume_tailorer.artifacts.models import ChangeDisposition, ResumeChange
from resume_tailorer.docx_export.pipeline import DocxTailoringResult, finalize_docx_edits
from resume_tailorer.models.career_profile import CareerTruthProfile
from resume_tailorer.parsers.docx_structure import extract_docx_structure
from resume_tailorer.pdf.generator import PDFGenerator
from resume_tailorer.tailorer.docx_bullet_tailorer import BulletEdit


def final_text_for_change(change: ResumeChange) -> str:
    """The text that should actually appear in a regenerated artifact for
    this change, given its current disposition. REJECTED/RESTORED revert
    to what was already true before tailoring touched it; MANUALLY_EDITED
    uses the user's own (already-validated -- see validate_manual_text)
    text, stored back onto proposed_text once accepted; PENDING/ACCEPTED
    keep the original AI-proposed rewrite."""
    if change.disposition in (ChangeDisposition.REJECTED, ChangeDisposition.RESTORED):
        return change.original_text
    return change.proposed_text


def apply_dispositions_to_text(baseline_text: str, changes: Sequence[ResumeChange]) -> str:
    """Rebuild the full resume text from the ORIGINAL baseline (never from
    a previously-regenerated text) by substituting each change's current
    disposition outcome for its AI-proposed text. Rebuilding from the
    baseline every time (rather than mutating progressively) keeps
    regeneration idempotent regardless of how many times a user flips a
    disposition back and forth."""
    text = baseline_text
    for change in changes:
        if not change.proposed_text or change.proposed_text == change.original_text:
            continue
        final_text = final_text_for_change(change)
        if final_text != change.proposed_text and change.proposed_text in text:
            text = text.replace(change.proposed_text, final_text)
    return text


def regenerate_docx_artifact(
    *,
    original_docx_bytes: bytes,
    changes: Sequence[ResumeChange],
    profile: CareerTruthProfile,
    gap_report,
    convert_to_pdf: bool,
) -> DocxTailoringResult:
    """Reconstruct BulletEdits from stored DOCX changes (source_index is
    the authoritative paragraph index -- see
    docx_export.pipeline.changes_from_bullet_edits) and splice them into a
    FRESH copy of the untouched original bytes. Never touches the
    tailorer."""
    doc = Document(io.BytesIO(original_docx_bytes))
    structure = extract_docx_structure(doc)
    bullets = structure.splice_targets(doc.paragraphs)

    edits = []
    for change in changes:
        if change.source_index is None:
            continue
        final_text = final_text_for_change(change)
        edits.append(
            BulletEdit(
                paragraph_index=change.source_index,
                original_text=change.original_text,
                new_text=final_text,
                changed=final_text != change.original_text,
            )
        )

    return finalize_docx_edits(
        doc=doc,
        structure=structure,
        bullets=bullets,
        edits=edits,
        original_docx_bytes=original_docx_bytes,
        gap_report=gap_report,
        profile=profile,
        convert_to_pdf=convert_to_pdf,
    )


def regenerate_freeform_artifact(
    *,
    baseline_tailored_text: str,
    changes: Sequence[ResumeChange],
    profile: CareerTruthProfile,
    target_length: str,
    style_hints: dict,
    company: str,
    role: str,
) -> tuple[bytes, str]:
    """Rebuild the freeform/PDF-only path's text from reviewed dispositions
    and regenerate a fresh PDF from it. Returns (pdf_bytes, final_text)."""
    final_text = apply_dispositions_to_text(baseline_tailored_text, changes)
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = os.path.join(temp_dir, "regenerated.pdf")
        PDFGenerator().generate(
            final_text,
            profile.name,
            output_path=output_path,
            target_length=target_length,
            style_hints=dict(style_hints or {}),
        )
        with open(output_path, "rb") as f:
            pdf_bytes = f.read()
    return pdf_bytes, final_text


def validate_manual_text(
    original_text: str, manual_text: str, profile: CareerTruthProfile
) -> list[str]:
    """Manual edits must pass the SAME semantic-drift/fabrication/length
    checks an AI-proposed rewrite would (spec 002 section 10) -- reuses
    the existing, already-tested per-pair checks rather than a separate,
    weaker manual-text validator."""
    from resume_tailorer.diff_generator import DiffGenerator
    from resume_tailorer.utils.length_check import bullet_length_delta

    generator = DiffGenerator()
    issues = list(generator.check_semantic_drift(original_text, manual_text))
    issues.extend(generator.check_bullet_pair_fabrication_risk(original_text, manual_text, profile))
    issues.extend(bullet_length_delta(original_text, manual_text))
    return issues
