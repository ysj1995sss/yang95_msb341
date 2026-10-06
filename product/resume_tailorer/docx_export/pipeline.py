"""
Single orchestration entry point for the DOCX master-template tailoring
pipeline: extract structure -> tailor bullets -> splice -> convert to PDF
(hard page-count check, degrades gracefully) -> synthesize scoring text so
the existing keyword-alignment scorer / diff generator / fabrication
checker keep working unchanged on DOCX output too.
"""

import io
import os
import re
import tempfile
from dataclasses import dataclass, field, replace

from docx import Document

from resume_tailorer.models import CareerTruthProfile
from resume_tailorer.analyzers.job_analyzer import JobAnalysis
from resume_tailorer.analyzers.gap_analyzer import EvidenceLevel, GapCategory, GapReport
from resume_tailorer.analyzers.requirement_review import RequirementReview, unshown_targets
from resume_tailorer.parsers.docx_structure import Bullet, extract_docx_structure, DocxStructure
from resume_tailorer.tailorer.docx_bullet_tailorer import DocxBulletTailorer, BulletEdit, BulletTailoringResult
from resume_tailorer.tailorer.resume_tailorer import _job_header_lines
from resume_tailorer.docx_export.splicer import splice_bullets_into_docx, save_docx
from resume_tailorer.docx_export.converter import convert_docx_to_pdf, DocxConversionUnavailable
from resume_tailorer.pdf.readability import check_readability, expected_for_docx
from resume_tailorer.pdf.validator import PDFValidator, findings_from_pdf_issues
from resume_tailorer.utils.scoring import qualification_match_ratio
from resume_tailorer.artifacts.models import (
    ArtifactValidation,
    ChangeCategory,
    FindingCategory,
    FindingSeverity,
    ResumeChange,
    ValidationFinding,
    ValidationStatus,
)
from resume_tailorer.docx_export.layout_signature import (
    capture_layout_signature,
    compare_layout_signatures,
)
from resume_tailorer.docx_export.splicer import inline_formatting_findings


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
    # Problem 7's self-check: raw counts plus a flag for when tailoring
    # looks suspiciously shallow given how much addressable evidence the
    # gap report found -- surfaced as a warning for a human to review, not
    # an automatic retry (this LLM backend is flaky enough that a second
    # blind pass isn't guaranteed to do better, and doubles latency/cost
    # for every request).
    bullets_evaluated: int = 0
    bullets_changed: int = 0
    bullets_rejected: int = 0
    addressable_requirements: int = 0
    tailoring_seems_shallow: bool = False
    changes: list[ResumeChange] = field(default_factory=list)
    validation: ArtifactValidation = field(
        default_factory=lambda: ArtifactValidation.from_findings([])
    )
    target_notes: dict[str, str] = field(default_factory=dict)


def changes_from_bullet_edits(
    edits: list[BulletEdit],
    bullets: list[Bullet],
    gap_report: GapReport,
) -> list[ResumeChange]:
    """Build traceable DOCX changes from exact paragraph pairings."""
    bullets_by_index = {bullet.paragraph_index: bullet for bullet in bullets}
    changes: list[ResumeChange] = []
    for edit in edits:
        if not edit.changed and not edit.rejected_reason:
            continue
        bullet = bullets_by_index.get(edit.paragraph_index)
        if bullet is None:
            continue
        gap = _best_gap_for_edit(edit, gap_report)
        rejected = bool(edit.rejected_reason)
        category = (
            ChangeCategory.REJECTED
            if rejected
            else ChangeCategory.COMPETENCY_CHANGED
            if bullet.section == "competencies"
            else ChangeCategory.REPHRASED
        )
        changes.append(
            ResumeChange(
                change_id=f"paragraph:{edit.paragraph_index}",
                section=bullet.section,
                source_index=edit.paragraph_index,
                original_text=edit.original_text,
                proposed_text=edit.new_text,
                category=category,
                reason=(
                    edit.rejected_reason
                    or "Matches verified job language while preserving the original claim."
                ),
                job_requirement=gap.requirement if gap else "",
                evidence_source="career_truth_profile" if gap else "original_resume",
                evidence_text=gap.candidate_evidence if gap else edit.original_text,
                validation_status=(ValidationStatus.FAIL if rejected else ValidationStatus.PASS),
            )
        )
    return changes


def _best_gap_for_edit(edit: BulletEdit, gap_report: GapReport):
    words = set(re.findall(r"[a-z0-9]+", f"{edit.original_text} {edit.new_text}".lower()))
    ranked = []
    for item in gap_report.items:
        gap_words = set(re.findall(r"[a-z0-9]+", f"{item.requirement} {item.candidate_evidence}".lower()))
        ranked.append((len(words & gap_words), item))
    if not ranked:
        return None
    score, item = max(ranked, key=lambda pair: pair[0])
    return item if score else None


def run_docx_tailoring_pipeline(
    original_docx_bytes: bytes,
    profile: CareerTruthProfile,
    job_analysis: JobAnalysis,
    gap_report: GapReport,
    bullet_tailorer: DocxBulletTailorer | None = None,
    convert_to_pdf: bool = True,
    review: RequirementReview | None = None,
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
    # Passed only when there is one, so any bullet tailorer without the argument keeps working.
    review_kwargs = {"review": review} if review is not None else {}
    tailoring_result = tailorer.tailor_bullets(bullets, profile, job_analysis, gap_report, **review_kwargs)

    # Length-cap, semantic-drift, and fabrication-risk checks all now run
    # as HARD rejects inside DocxBulletTailorer._parse_and_validate itself
    # (found live, 2026-09-23: prompt instructions alone weren't reliably
    # followed for any of the three), so an accepted `changed=True` edit
    # here has already passed all of them -- re-running the same checks
    # post-hoc would always return empty and was dead weight.
    warnings = list(tailoring_result.warnings)

    bullets_changed = sum(1 for e in tailoring_result.edits if e.changed)
    addressable_requirements = (
        len(review.targets) if review is not None else
        sum(1 for item in gap_report.items if item.category in (GapCategory.A, GapCategory.B, GapCategory.C))
    )
    # Threshold is deliberately loose (a real signal, not a precise
    # measurement): flag when there's clearly more addressable evidence
    # than the model actually used. Found live (2026-09-23): a real
    # tailoring pass changed exactly 2 bullets while 11 requirements had
    # real evidence elsewhere in the resume -- this would have caught it.
    tailoring_seems_shallow = bullets_changed <= 2 and addressable_requirements > 4

    # Step 14's resume-wide optimization pass: when the first pass looks
    # shallow, identify specific high-priority requirements that have
    # STRONG evidence but are still missing from the tailored bullets, and
    # run ONE bounded second pass focused specifically on those -- rather
    # than either giving up after one shallow attempt, or looping
    # unboundedly against an LLM backend already known to be flaky (same
    # cost/latency reasoning as the bounded repair loop). Only runs when
    # there's something concrete to focus on; a shallow pass with no
    # remaining strong-evidence gaps just means the resume genuinely
    # doesn't have much more truthful room to improve.
    if tailoring_seems_shallow:
        if review is not None:
            # Spec 010: the second pass works only on requirements with confirmed evidence that
            # the tailored bullets still don't show.
            current = " ".join(_apply_edits_to_bullets(bullets, tailoring_result.edits)[i].text
                               for i in range(len(bullets)))
            priority_focus = [f"{r.text} (evidence: \"{r.evidence[0].text}\")"
                              for r in unshown_targets(review, current)][:5]
        else:
            priority_focus = _underrepresented_strong_evidence(gap_report, tailoring_result, structure, bullets)
        if priority_focus:
            updated_bullets = _apply_edits_to_bullets(bullets, tailoring_result.edits)
            second_pass = tailorer.tailor_bullets(
                updated_bullets, profile, job_analysis, gap_report, priority_focus=priority_focus, **review_kwargs
            )
            notes = {**tailoring_result.target_notes, **second_pass.target_notes}
            tailoring_result = _merge_optimization_pass(tailoring_result, second_pass)
            tailoring_result.target_notes = notes
            warnings = list(tailoring_result.warnings)
            bullets_changed = sum(1 for e in tailoring_result.edits if e.changed)
            warnings.append(
                f"Resume-wide optimization pass ran: focused on {len(priority_focus)} "
                "still-underrepresented requirement(s) with strong evidence."
            )

    bullets_changed = sum(1 for e in tailoring_result.edits if e.changed)
    bullets_rejected = sum(1 for e in tailoring_result.edits if e.rejected_reason)
    # Re-check after the possible optimization pass above -- if it
    # genuinely helped, bullets_changed is now higher and this may no
    # longer be shallow; if it found nothing safe to add (or never ran
    # because there was nothing concrete to focus on), the warning still
    # belongs in front of the user.
    tailoring_seems_shallow = bullets_changed <= 2 and addressable_requirements > 4
    if tailoring_seems_shallow:
        warnings.append(
            f"Tailoring may be too shallow: only {bullets_changed} bullet(s) changed while "
            f"{addressable_requirements} job requirements have real evidence in the resume. "
            "Consider reviewing the gap report for evidence the tailoring pass didn't surface."
        )

    result = finalize_docx_edits(
        doc=doc,
        structure=structure,
        bullets=bullets,
        edits=tailoring_result.edits,
        original_docx_bytes=original_docx_bytes,
        gap_report=gap_report,
        profile=profile,
        convert_to_pdf=convert_to_pdf,
        extra_warnings=warnings,
        bullets_evaluated=len(bullets),
        bullets_changed=bullets_changed,
        bullets_rejected=bullets_rejected,
        addressable_requirements=addressable_requirements,
        tailoring_seems_shallow=tailoring_seems_shallow,
    )
    result.target_notes = dict(tailoring_result.target_notes)  # spec 011
    return result


def finalize_docx_edits(
    *,
    doc,
    structure: DocxStructure,
    bullets: list[Bullet],
    edits: list[BulletEdit],
    original_docx_bytes: bytes,
    gap_report: GapReport,
    profile: CareerTruthProfile,
    convert_to_pdf: bool,
    extra_warnings: list[str] | None = None,
    bullets_evaluated: int = 0,
    bullets_changed: int = 0,
    bullets_rejected: int = 0,
    addressable_requirements: int = 0,
    tailoring_seems_shallow: bool = False,
) -> "DocxTailoringResult":
    """
    Splice a KNOWN set of edits into `doc`, convert to PDF, and validate --
    the part of the DOCX pipeline that has nothing to do with calling an
    LLM. Shared by run_docx_tailoring_pipeline (edits come from a fresh
    DocxBulletTailorer pass) and Steps 16-20 regeneration (edits are
    reconstructed from stored, human-reviewed ResumeChange dispositions --
    see apps/api/app/tailor/regeneration.py). Regeneration must never
    re-invoke the tailorer: re-running the LLM would produce different,
    unreviewed text, silently discarding the user's accept/reject/manual-
    edit decisions.
    """
    warnings = list(extra_warnings or [])
    editable_indices = {edit.paragraph_index for edit in edits}
    before_layout = capture_layout_signature(doc, editable_indices)
    structured_findings: list[ValidationFinding] = []
    for edit in edits:
        structured_findings.extend(
            inline_formatting_findings(doc.paragraphs[edit.paragraph_index], edit.changed)
        )
    spliced_doc = splice_bullets_into_docx(doc, edits)
    after_layout = capture_layout_signature(spliced_doc, editable_indices)
    structured_findings.extend(compare_layout_signatures(before_layout, after_layout))

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
                structured_findings.extend(findings_from_pdf_issues(pdf_validation_issues))
                # Spec 010: the finished PDF must read back with your name, email and every
                # bullet, in order (a local check, not an employer's ATS).
                structured_findings.extend(check_readability(
                    tailored_validation.extracted_text, expected_for_docx(profile, [e.new_text for e in edits])
                ))
                original_page_count = original_validation.page_count
                tailored_page_count = tailored_validation.page_count
                with open(tailored_pdf_path, "rb") as f:
                    pdf_bytes = f.read()
            except DocxConversionUnavailable as exc:
                conversion_available = False
                warnings.append(str(exc))
                structured_findings.append(
                    ValidationFinding(
                        "DOCX_CONVERSION_UNAVAILABLE",
                        FindingSeverity.WARNING,
                        FindingCategory.CONVERSION,
                        str(exc),
                    )
                )

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
        structured_findings.append(
            ValidationFinding(
                "PAGE_COUNT_CHANGED",
                FindingSeverity.FAIL,
                FindingCategory.VISUAL,
                f"Page count changed: {original_page_count} -> {tailored_page_count}.",
            )
        )

    scoring_text = _synthesize_scoring_text(profile, structure, edits)

    return DocxTailoringResult(
        docx_bytes=docx_bytes,
        tailored_scoring_text=scoring_text,
        edits=edits,
        original_page_count=original_page_count,
        tailored_page_count=tailored_page_count,
        page_count_preserved=page_count_preserved,
        pdf_bytes=pdf_bytes,
        pdf_validation_issues=pdf_validation_issues,
        conversion_available=conversion_available,
        bullet_warnings=warnings,
        bullets_evaluated=bullets_evaluated,
        bullets_changed=bullets_changed,
        bullets_rejected=bullets_rejected,
        addressable_requirements=addressable_requirements,
        tailoring_seems_shallow=tailoring_seems_shallow,
        changes=changes_from_bullet_edits(edits, bullets, gap_report),
        validation=ArtifactValidation.from_findings(
            structured_findings,
            original_page_count=original_page_count,
            tailored_page_count=tailored_page_count,
            checks_run=("docx_layout", "inline_formatting", "page_count", "pdf_technical", "readability"),
        ),
    )


def _apply_edits_to_bullets(bullets: list[Bullet], edits: list[BulletEdit]) -> list[Bullet]:
    """Build a bullets list reflecting a completed pass's outcome, so a
    following pass builds ON TOP of those changes instead of re-evaluating
    the untouched originals from scratch."""
    edit_by_index = {e.paragraph_index: e for e in edits}
    updated = []
    for bullet in bullets:
        edit = edit_by_index.get(bullet.paragraph_index)
        if edit and edit.changed:
            updated.append(replace(bullet, text=edit.new_text))
        else:
            updated.append(bullet)
    return updated


def _merge_optimization_pass(
    first: BulletTailoringResult, second: BulletTailoringResult
) -> BulletTailoringResult:
    """Second-pass edits replace their bullet's outcome ONLY when the
    second pass made a genuine additional change; original_text always
    stays the true document original (from the first pass), never the
    first pass's own already-tailored text second.original_text would
    otherwise carry. A bullet the second pass tried and rejected still
    surfaces that rejection reason even if the net outcome (unchanged) is
    the same as after the first pass -- useful diagnostic signal."""
    second_by_index = {e.paragraph_index: e for e in second.edits}
    merged: list[BulletEdit] = []
    for first_edit in first.edits:
        second_edit = second_by_index.get(first_edit.paragraph_index)
        if second_edit and second_edit.changed:
            merged.append(BulletEdit(
                paragraph_index=first_edit.paragraph_index,
                original_text=first_edit.original_text,
                new_text=second_edit.new_text,
                changed=True,
                rejected_reason=second_edit.rejected_reason,
            ))
        elif second_edit and second_edit.rejected_reason and not first_edit.changed:
            merged.append(replace(first_edit, rejected_reason=second_edit.rejected_reason))
        else:
            merged.append(first_edit)
    return BulletTailoringResult(edits=merged, warnings=first.warnings + second.warnings)


def _underrepresented_strong_evidence(
    gap_report: GapReport,
    tailoring_result: BulletTailoringResult,
    structure: DocxStructure,
    bullets: list[Bullet],
) -> list[str]:
    """
    Step 14's resume-wide optimization question, answered concretely:
    "which top JD requirements are strongly supported but still poorly
    represented in the final resume?" Requirements with STRONG evidence
    (Category B/C, evidence_level DIRECT_VERIFIED or STRONGLY_SUPPORTED)
    that the first pass's tailored bullets still don't reasonably cover.
    Bounded to 5 so the resulting prompt addition stays small and focused
    rather than dumping the entire gap report back at the model.
    """
    edit_by_index = {e.paragraph_index: e for e in tailoring_result.edits}
    current_text = " ".join(
        edit_by_index[b.paragraph_index].new_text
        if b.paragraph_index in edit_by_index and edit_by_index[b.paragraph_index].changed
        else b.text
        for b in bullets
    )

    candidates = [
        item for item in gap_report.items
        if item.category in (GapCategory.B, GapCategory.C)
        and item.evidence_level in (EvidenceLevel.DIRECT_VERIFIED, EvidenceLevel.STRONGLY_SUPPORTED)
    ]

    focus = [
        item.requirement for item in candidates
        if qualification_match_ratio(current_text, item.requirement) < 0.4
    ]
    return focus[:5]


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
