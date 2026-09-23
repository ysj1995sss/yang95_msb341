"""
Single orchestration entry point for the DOCX master-template tailoring
pipeline: extract structure -> tailor bullets -> splice -> convert to PDF
(hard page-count check, degrades gracefully) -> synthesize scoring text so
the existing keyword-alignment scorer / diff generator / fabrication
checker keep working unchanged on DOCX output too.
"""

import io
import os
import tempfile
from dataclasses import dataclass, field

from docx import Document

from resume_tailorer.models import CareerTruthProfile
from resume_tailorer.analyzers.job_analyzer import JobAnalysis
from resume_tailorer.analyzers.gap_analyzer import GapReport
from resume_tailorer.parsers.docx_structure import extract_docx_structure, DocxStructure
from resume_tailorer.tailorer.docx_bullet_tailorer import DocxBulletTailorer, BulletEdit
from resume_tailorer.tailorer.resume_tailorer import _job_header_lines
from resume_tailorer.docx_export.splicer import splice_bullets_into_docx, save_docx
from resume_tailorer.docx_export.converter import convert_docx_to_pdf, DocxConversionUnavailable
from resume_tailorer.docx_export.bullet_checks import bullet_length_delta
from resume_tailorer.pdf.validator import PDFValidator
from resume_tailorer.diff_generator import DiffGenerator


@dataclass
class DocxTailoringResult:
    docx_bytes: bytes
    tailored_scoring_text: str
    edits: list[BulletEdit] = field(default_factory=list)
    original_page_count: int | None = None
    tailored_page_count: int | None = None
    page_count_preserved: bool | None = None
    pdf_bytes: bytes | None = None
    pdf_validation_issues: list[str] = field(default_factory=list)
    conversion_available: bool = False
    bullet_warnings: list[str] = field(default_factory=list)


def run_docx_tailoring_pipeline(
    original_docx_bytes: bytes,
    profile: CareerTruthProfile,
    job_analysis: JobAnalysis,
    gap_report: GapReport,
    bullet_tailorer: DocxBulletTailorer | None = None,
    convert_to_pdf: bool = True,
) -> DocxTailoringResult:
    """
    convert_to_pdf=False skips the docx2pdf round-trip entirely (no page
    count, no pdf_bytes) -- for a caller that only wants tailored content/
    scoring (e.g. generate_pdf=False in the API), matching how the
    PDF-original path also skips PDFGenerator/PDFValidator entirely when no
    file was actually requested, rather than paying for a ~5-10s Word
    automation round trip nobody asked for.
    """
    doc = Document(io.BytesIO(original_docx_bytes))
    structure = extract_docx_structure(doc)
    bullets = structure.splice_targets(doc.paragraphs)

    tailorer = bullet_tailorer or DocxBulletTailorer()
    tailoring_result = tailorer.tailor_bullets(bullets, profile, job_analysis, gap_report)

    warnings = list(tailoring_result.warnings)
    diff_gen = DiffGenerator()
    for edit in tailoring_result.edits:
        if edit.changed:
            warnings.extend(bullet_length_delta(edit.original_text, edit.new_text))
            warnings.extend(
                diff_gen.check_bullet_pair_fabrication_risk(
                    edit.original_text, edit.new_text, profile
                )
            )

    spliced_doc = splice_bullets_into_docx(doc, tailoring_result.edits)

    with tempfile.TemporaryDirectory() as tmp_dir:
        original_path = os.path.join(tmp_dir, "original.docx")
        tailored_docx_path = os.path.join(tmp_dir, "tailored.docx")
        original_pdf_path = os.path.join(tmp_dir, "original.pdf")
        tailored_pdf_path = os.path.join(tmp_dir, "tailored.pdf")

        with open(original_path, "wb") as f:
            f.write(original_docx_bytes)
        save_docx(spliced_doc, tailored_docx_path)

        conversion_available = False
        original_page_count = None
        tailored_page_count = None
        pdf_bytes = None
        pdf_validation_issues: list[str] = []
        if convert_to_pdf:
            conversion_available = True
            try:
                convert_docx_to_pdf(original_path, original_pdf_path)
                convert_docx_to_pdf(tailored_docx_path, tailored_pdf_path)
                tailored_validation = PDFValidator().validate(tailored_pdf_path, target_length="preserve")
                original_validation = PDFValidator().validate(original_pdf_path, target_length="preserve")
                pdf_validation_issues = tailored_validation.issues
                original_page_count = original_validation.page_count
                tailored_page_count = tailored_validation.page_count
                with open(tailored_pdf_path, "rb") as f:
                    pdf_bytes = f.read()
            except DocxConversionUnavailable as exc:
                conversion_available = False
                warnings.append(str(exc))

        with open(tailored_docx_path, "rb") as f:
            docx_bytes = f.read()

    page_count_preserved = (
        original_page_count == tailored_page_count
        if original_page_count is not None and tailored_page_count is not None
        else None
    )
    if page_count_preserved is False:
        warnings.append(
            f"Page count changed: {original_page_count} -> {tailored_page_count}."
        )

    scoring_text = _synthesize_scoring_text(profile, structure, tailoring_result.edits)

    return DocxTailoringResult(
        docx_bytes=docx_bytes,
        tailored_scoring_text=scoring_text,
        edits=tailoring_result.edits,
        original_page_count=original_page_count,
        tailored_page_count=tailored_page_count,
        page_count_preserved=page_count_preserved,
        pdf_bytes=pdf_bytes,
        pdf_validation_issues=pdf_validation_issues,
        conversion_available=conversion_available,
        bullet_warnings=warnings,
    )


def _synthesize_scoring_text(
    profile: CareerTruthProfile, structure: DocxStructure, edits: list[BulletEdit]
) -> str:
    """
    Build a flat resume-shaped text string purely so the EXISTING
    optimizer._score_resume / DiffGenerator.generate_diff /
    find_unsupported_claims -- none of which are DOCX-aware -- keep working
    unchanged. This text is NEVER exported to the user; only docx_bytes /
    pdf_bytes are. Bullet text and order come directly from `edits` in
    DOCUMENT order (paragraph_index order within each job), never from
    profile.work_experience[i].responsibilities/accomplishments -- those
    two lists are split by category and can lose the original interleaved
    order, so positional pairing against them could silently mismatch
    bullets on a job with responsibilities and accomplishments interleaved.
    """
    edit_by_index = {e.paragraph_index: e for e in edits}
    lines: list[str] = []

    if structure.summary_paragraph_indices:
        lines.append("PROFESSIONAL SUMMARY")
        for idx in structure.summary_paragraph_indices:
            text = edit_by_index[idx].new_text if idx in edit_by_index else ""
            if text:
                lines.append(text)
        lines.append("")

    if profile.education:
        lines.append("EDUCATION")
        for edu in profile.education:
            lines.append(f"{edu.institution} | {edu.year}")
            degree_line = f"{edu.degree} in {edu.field}" if edu.field else edu.degree
            lines.append(degree_line)
            for note in edu.notes:
                lines.append(f"- {note}")
        lines.append("")

    if len(structure.jobs) == len(profile.work_experience):
        lines.append("WORK EXPERIENCE")
        for job_index, job_block in enumerate(structure.jobs):
            job = profile.work_experience[job_index]
            lines.extend(_job_header_lines(job))
            for idx in job_block.bullet_paragraph_indices:
                text = edit_by_index[idx].new_text if idx in edit_by_index else ""
                if text:
                    lines.append(f"- {text}")
            lines.append("")
    else:
        # Job-block count disagrees with the profile's -- fall back to
        # headers-only (from the profile, which is still trustworthy) with
        # no bullet substitution, rather than risk indexing out of range or
        # silently pairing a job's bullets to the wrong job's header.
        lines.append("WORK EXPERIENCE")
        for job in profile.work_experience:
            lines.extend(_job_header_lines(job))
            for resp in job.responsibilities:
                lines.append(f"- {resp}")
            for acc in job.accomplishments:
                lines.append(f"- {acc}")
            lines.append("")

    if profile.skills:
        lines.append("SKILLS")
        lines.append(", ".join(profile.skills))
        lines.append("")

    if profile.tools:
        lines.append("TOOLS & PLATFORMS")
        lines.append(", ".join(profile.tools))
        lines.append("")

    if profile.certifications:
        lines.append("CERTIFICATIONS")
        for cert in profile.certifications:
            lines.append(f"- {cert}")
        lines.append("")

    return "\n".join(lines)
