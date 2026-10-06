"""Tailoring, outside any UI (spec 009): run the pipeline for one job and rebuild the
artifact from the user's decisions. Moved unchanged out of pages/5_Tailor.py so the
Streamlit page and the workspace API run exactly the same steps (spec 002, decisions
006/014/021/022): a DOCX resume goes through the master-template splice pipeline,
anything else through the freeform path; review decisions are applied locally and
never re-run the model.

`session` is the Streamlit session state or the API's per-request equivalent: the
confirmed Career Profile in it is what tailoring uses, and the validated artifact is
handed to Apply through it.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import replace
from typing import Any, Callable, MutableMapping, Optional

from resume_tailorer.analyzers import GapAnalyzer, JobAnalyzer, ResumeBenchmarker
from resume_tailorer.analyzers.gap_analyzer import find_unsupported_claims
from resume_tailorer.analyzers.requirement_review import build_review, with_resume
from resume_tailorer.artifacts.changes import build_freeform_changes
from resume_tailorer.artifacts.length_control import (
    build_freeform_artifact,
    correct_docx_length_once,
    max_pages_label,
)
from resume_tailorer.artifacts.models import ChangeDisposition, FidelityMode
from resume_tailorer.artifacts.regeneration import (
    regenerate_docx_artifact,
    regenerate_freeform_artifact,
    validate_manual_text,
)
from resume_tailorer.artifacts.report import build_final_report
from resume_tailorer.docx_export import run_docx_tailoring_pipeline
from resume_tailorer.parsers import ResumeParser
from resume_tailorer.pdf.validator import PDFValidator
from resume_tailorer.docx_export.profile_sync import sync_docx_to_profile
from resume_tailorer.session_profile import FACT_VAULT, RESUME_UPLOAD, set_career_profile
from resume_tailorer.tailorer import ResumeTailorer, ResumeTailoringOptimizer
from resume_tailorer.tailorer.docx_bullet_tailorer import DocxBulletTailorer
from resume_tailorer.tailoring_session import publish_artifact_handoff

TARGET_LENGTHS = {"1 page": "1_page", "2 pages": "2_page"}


class TailoringError(RuntimeError):
    """A failure to show the user as is (the message is already plain language)."""


def run_tailoring(
    session: MutableMapping[str, Any],
    *,
    original_bytes: bytes,
    filename: str,
    job_description: str,
    pending: dict,
    llm,
    target_length: str = "preserve",
    conservative: bool = False,
    progress: Callable[[str], None] = lambda message: None,
    provenance: Optional[dict] = None,
    career_profile=None,
) -> dict:
    """Tailor one resume to one job. Returns the review state (and hands a passing
    artifact to Apply through `session`). Raises TailoringError with a plain message.

    `provenance` is the Career Profile's per-fact confirmation state, passed when the resume is
    the Career Profile's own; facts still only "from resume" are then never tailoring targets
    (spec 010). A one-off file has none, and its facts count as the person's own.

    `career_profile` (spec 011): the Career Profile, passed with the Career Profile's own resume.
    Tailoring then uses its facts, with every edit, instead of re-reading the file; a Word file is
    first brought up to date with it (profile_sync), so its layout is kept."""
    if not (job_description or "").strip():
        raise TailoringError("Add the job description first: choose a job in Jobs, or paste one.")
    suffix = os.path.splitext(filename)[1].lower()
    is_docx = suffix == ".docx"
    fd, resume_path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(original_bytes)
        progress("Reading your resume")
        parser = ResumeParser()
        sync_summary = ""
        if career_profile is None:
            profile = set_career_profile(session, parser.parse(resume_path), RESUME_UPLOAD)
            review_profile = profile
        elif is_docx:
            progress("Bringing your Career Profile into your Word file")
            sync = sync_docx_to_profile(original_bytes, career_profile)
            if sync.has_blockers:
                detail = "; ".join(f"{item.field}: {item.reason}" for item in sync.fields if item.blocking)
                raise TailoringError(
                    f"Your Word file could not be safely synced: {detail}. "
                    "Edit the Word file or use a rebuilt layout."
                )
            original_bytes = sync.docx_bytes
            sync_summary = sync.summary
            set_career_profile(session, career_profile, FACT_VAULT)  # the session keeps the real profile
            profile = sync.aligned_profile  # the file's role order, for the bullet tailorer only
            review_profile = career_profile  # in the Career Profile's own order, so paths match provenance
        else:
            profile = set_career_profile(session, career_profile, FACT_VAULT)
            review_profile = career_profile
        try:
            raw_resume_text = parser.get_raw_text(resume_path)
        except ValueError:
            raw_resume_text = ""
        style_hints = parser.extract_style_hints(raw_resume_text, file_path=resume_path)

        progress("Reading the job description")
        job_analysis = JobAnalyzer().analyze(job_description)
        benchmark = ResumeBenchmarker().benchmark(profile, job_analysis)
        gap_report = GapAnalyzer().analyze(profile, job_analysis, benchmark)
        review = build_review(job_analysis, review_profile, provenance=provenance, posting=job_description)

        progress("Writing and checking changes (about a minute)")
        baseline_text = ""
        target_notes: dict = {}
        if is_docx:
            docx_result = run_docx_tailoring_pipeline(
                original_bytes, profile, job_analysis, gap_report,
                bullet_tailorer=DocxBulletTailorer(llm=llm), convert_to_pdf=True, review=review,
            )
            target_notes = dict(docx_result.target_notes)  # kept across the length correction
            docx_result = correct_docx_length_once(
                original_docx_bytes=original_bytes, docx_result=docx_result,
                profile=profile, gap_report=gap_report, llm=llm,
            )
            tailored_text = docx_result.tailored_scoring_text
            tailored_alignment, _m, _x = ResumeTailoringOptimizer._score_resume(tailored_text, job_analysis, profile)
            changes = list(docx_result.changes)
            validation = docx_result.validation
            docx_bytes, pdf_bytes = docx_result.docx_bytes, docx_result.pdf_bytes
            fidelity_mode = FidelityMode.PRESERVED
        else:
            initial = ResumeTailorer(llm=llm).tailor(profile, job_analysis, gap_report, conservative=conservative,
                                                     review=review)
            optimization = ResumeTailoringOptimizer(llm=llm).optimize(
                profile, job_analysis, initial, gap_report, conservative=conservative, review=review
            )
            tailored_text = optimization.tailored_resume
            tailored_alignment = optimization.final_score
            changes = build_freeform_changes(profile, tailored_text, gap_report, review=review)
            pdf_bytes, validation, tailored_text, changes, _attempts = build_freeform_artifact(
                tailored_text=tailored_text, changes=changes, profile=profile,
                target_length=target_length, style_hints=style_hints, llm=llm,
            )
            baseline_text = tailored_text
            docx_bytes = None
            fidelity_mode = FidelityMode.RECONSTRUCTED
    except TailoringError:
        raise
    except RuntimeError as exc:
        raise TailoringError(f"{exc} Try again in a minute.") from exc
    except Exception as exc:
        raise TailoringError(f"Tailoring didn't finish: {exc}. Your profile and job are unchanged; try again.") from exc
    finally:
        try:
            os.remove(resume_path)
        except OSError:
            pass

    fit = (pending.get("candidate_fit") or {}).get("overall_fit")
    candidate_fit = fit / 100 if isinstance(fit, (int, float)) else None
    report = build_final_report(
        candidate_fit=candidate_fit,
        fit_breakdown={},
        original_alignment=benchmark.original_match_score,
        tailored_alignment=tailored_alignment,
        gap_report=gap_report,
        validation=validation,
        artifacts=(),
        company=pending.get("company", ""),
        role=pending.get("title") or "Target Role",
        fidelity_mode=fidelity_mode,
        unsupported_claims=find_unsupported_claims(gap_report, tailored_text),
    )
    state = {
        "source_kind": "DOCX" if is_docx else "PDF",
        "original_bytes": original_bytes,
        "baseline_text": baseline_text,
        "target_length": target_length,
        "style_hints": style_hints,
        "profile": profile,
        "gap_report": gap_report,
        "job_analysis": job_analysis,
        "original_alignment": benchmark.original_match_score,
        "requirement_review": with_resume(review, tailored_text),
        "sync_summary": sync_summary,
        "target_notes": target_notes,
        "candidate_fit": candidate_fit,
        "company": pending.get("company", ""),
        "role": pending.get("title", ""),
        "fidelity_mode": fidelity_mode,
        "changes": changes,
        "dispositions": {},
        "manual_texts": {},
        "decided": set(),
        "dirty": False,
        "tailored_text": tailored_text,
        "validation": validation,
        "docx_bytes": docx_bytes,
        "pdf_bytes": pdf_bytes,
        "report": report,
        "candidate_name": profile.name,
        "reviewed": False,
        "version": 1,
    }
    publish_artifact_handoff(
        session, pdf_bytes=pdf_bytes, validation_status=validation.status.value,
        tailored_alignment=tailored_alignment, version=1, folder=session.get("artifacts_dir"),
    )
    return state


def regenerate(session: MutableMapping[str, Any], state: dict) -> None:
    """Apply the current per-change decisions and rebuild the artifact, updating `state`.
    Never re-invokes the model, so the output is exactly what the user decided (spec 002
    section 10). Raises TailoringError when a manual edit is empty or unverifiable."""
    updated_changes = []
    for change in state["changes"]:
        disposition = ChangeDisposition(state["dispositions"].get(change.change_id, str(change.disposition)))
        manual_text: Optional[str] = None
        if disposition == ChangeDisposition.MANUALLY_EDITED:
            manual_text = state["manual_texts"].get(change.change_id, "").strip()
            if not manual_text:
                raise TailoringError(
                    f"Your edit for '{change.original_text[:40]}…' is empty. Write the text or keep the original."
                )
            issues = validate_manual_text(change.original_text, manual_text, state["profile"],
                                          state.get("requirement_review"))
            if issues:
                raise TailoringError(
                    f"Your edit for '{change.original_text[:40]}…' adds something we can't verify: " + "; ".join(issues)
                )
        # proposed_text stays the model's untouched proposal so the freeform
        # path can still find it in the baseline text (ResumeChange.manual_text).
        updated_changes.append(replace(change, disposition=disposition, manual_text=manual_text))

    profile = state["profile"]
    gap_report = state["gap_report"]
    if state["source_kind"] == "DOCX":
        result = regenerate_docx_artifact(
            original_docx_bytes=state["original_bytes"], changes=updated_changes,
            profile=profile, gap_report=gap_report, convert_to_pdf=True,
        )
        tailored_text = result.tailored_scoring_text
        validation = result.validation
        docx_bytes = result.docx_bytes
        pdf_bytes = result.pdf_bytes
    else:
        try:
            pdf_bytes, tailored_text = regenerate_freeform_artifact(
                baseline_tailored_text=state["baseline_text"], changes=updated_changes, profile=profile,
                target_length=state["target_length"], style_hints=state["style_hints"] or {}, company="", role="",
            )
        except ValueError as exc:
            raise TailoringError(str(exc)) from exc
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        try:
            validation = PDFValidator().validate_artifact(
                tmp_path, profile=profile, expected_page_count=None, accepted_changes=updated_changes,
                target_length=max_pages_label(state["target_length"], state["style_hints"]),
                tailored_text=tailored_text,
            )
        finally:
            os.remove(tmp_path)
        docx_bytes = None

    unsupported_claims = find_unsupported_claims(gap_report, tailored_text)
    tailored_alignment, _matched, _missing = ResumeTailoringOptimizer._score_resume(
        tailored_text, state["job_analysis"], profile
    )
    report = build_final_report(
        candidate_fit=state.get("candidate_fit"),
        fit_breakdown={},
        original_alignment=state["original_alignment"],
        tailored_alignment=tailored_alignment,
        gap_report=gap_report,
        validation=validation,
        artifacts=(),
        company=state.get("company", ""),
        role=state.get("role") or "Target Role",
        fidelity_mode=state["fidelity_mode"],
        unsupported_claims=unsupported_claims,
    )
    if state.get("requirement_review") is not None:
        state["requirement_review"] = with_resume(state["requirement_review"], tailored_text)
    state.update(
        changes=updated_changes,
        tailored_text=tailored_text,
        validation=validation,
        docx_bytes=docx_bytes,
        pdf_bytes=pdf_bytes,
        report=report,
        reviewed=True,
        dirty=False,
        version=state.get("version", 1) + 1,
    )
    publish_artifact_handoff(
        session, pdf_bytes=pdf_bytes, validation_status=validation.status.value,
        tailored_alignment=tailored_alignment, version=state["version"], folder=session.get("artifacts_dir"),
    )
