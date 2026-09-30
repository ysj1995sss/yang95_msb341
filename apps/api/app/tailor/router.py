import dataclasses
import base64
import json
import os
import tempfile

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db import get_db
from app.fit.scoring import score_candidate_fit
from app.models import Job, Profile, ResumeFile, ResumeFileVersion, TailoredArtifact, User
from app.schemas.artifact import (
    ArtifactMetadataOut,
    ArtifactValidationOut,
    FinalApplicationReportOut,
    ResumeChangeOut,
    ReviewChangesRequest,
    TailoringRunOut,
    ValidationFindingOut,
)
from app.schemas.tailor import BulletChangeOut, GapItemOut, TailorRequest, TailorResult
from resume_tailorer.artifacts.regeneration import (
    regenerate_docx_artifact,
    regenerate_freeform_artifact,
    validate_manual_text,
)
from app.tailor.serialization import (
    changes_from_json,
    changes_to_json,
    profile_snapshot_hash,
    report_to_json,
    validation_from_json,
    validation_to_json,
)
from app.tailor.storage import TailoringRunStore

from resume_tailorer.models.career_profile import CareerTruthProfile
from resume_tailorer.analyzers.job_analyzer import JobAnalyzer
from resume_tailorer.analyzers.resume_benchmarker import ResumeBenchmarker
from resume_tailorer.analyzers.gap_analyzer import GapAnalyzer, find_unsupported_claims
from resume_tailorer.tailorer.optimizer import ResumeTailoringOptimizer, OptimizationResult
from resume_tailorer.pdf.validator import PDFValidator
from resume_tailorer.diff_generator import DiffGenerator
from resume_tailorer.parsers import ResumeParser
from resume_tailorer.docx_export import run_docx_tailoring_pipeline
from resume_tailorer.artifacts.changes import build_freeform_changes
from resume_tailorer.artifacts.length_control import (
    build_freeform_artifact,
    correct_docx_length_once,
    max_pages_label,
)
from resume_tailorer.artifacts.filenames import safe_artifact_filename
from resume_tailorer.artifacts.models import ChangeDisposition, FidelityMode, ResumeChange
from resume_tailorer.artifacts.report import build_final_report

router = APIRouter(prefix="/tailor", tags=["tailor"])


def _extract_style_hints(resume_file: ResumeFile | None) -> dict | None:
    """Best-effort style hints (bullet char, heading style) from the user's
    stored original resume (spec 001 item 16: preserve resume design). Falls
    back to None (PDFGenerator's own defaults) if there's no stored original
    or it can't be read -- style hints are a presentation nicety, never a
    reason to fail tailoring."""
    if resume_file is None:
        return None
    suffix = os.path.splitext(resume_file.filename)[1].lower() or ".pdf"
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(resume_file.data)
        parser = ResumeParser()
        raw_text = parser.get_raw_text(tmp_path)
        return parser.extract_style_hints(raw_text, file_path=tmp_path)
    except Exception:
        return None
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _b64_if_downloadable(data: bytes | None, validation) -> str | None:
    """The one download rule: a FAIL artifact is never handed out, in any response."""
    if not data or str(getattr(validation, "status", "")) == "FAIL":
        return None
    return base64.b64encode(data).decode("ascii")


def _run_resume_file(db: Session, run) -> "ResumeFile | ResumeFileVersion | None":
    """The exact resume upload a run was created from, even after re-uploads."""
    if run.original_resume_version is None:
        return None
    current = db.get(ResumeFile, run.user_id)
    if current is not None and current.version == run.original_resume_version:
        return current
    return (
        db.query(ResumeFileVersion)
        .filter(
            ResumeFileVersion.user_id == run.user_id,
            ResumeFileVersion.version == run.original_resume_version,
        )
        .one_or_none()
    )


def get_optimizer() -> ResumeTailoringOptimizer:
    try:
        return ResumeTailoringOptimizer()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _profile_is_too_sparse(profile: CareerTruthProfile) -> bool:
    """
    Safety gate found necessary live (2026-09-22): a real resume that the
    parser under-extracted (empty skills, most bullets dropped) still went
    through the full tailoring pipeline, and with almost nothing real to
    work from, the LLM filled the gap with an invented, specific claim
    instead of refusing. Rather than trust every model to decline
    gracefully when handed a near-empty profile, refuse to call it at all.
    """
    has_skills_or_tools = bool(profile.skills) or bool(profile.tools)
    has_experience_content = any(
        job.responsibilities or job.accomplishments for job in profile.work_experience
    )
    return not has_skills_or_tools and not has_experience_content


def _rebuild_job_context(db: Session, profile: CareerTruthProfile, profile_dict: dict, job_dict: dict):
    """Deterministically re-derive job_analysis/benchmark/gap_report/fit
    from a stored job_snapshot -- no LLM call, pure regex/heuristic +
    evidence matching (Steps 10-12), so this is safe and consistent to
    redo at regenerate time without re-tailoring."""
    job_description = job_dict.get("description", "")
    job_analysis = JobAnalyzer().analyze(job_description)
    benchmark = ResumeBenchmarker().benchmark(profile, job_analysis)
    gap_report = GapAnalyzer().analyze(profile, job_analysis, benchmark)
    fit = score_candidate_fit(profile_dict, job_dict)
    return job_analysis, benchmark, gap_report, fit


def _artifact_out(artifact: TailoredArtifact) -> ArtifactMetadataOut:
    return ArtifactMetadataOut(
        artifact_id=artifact.id,
        run_id=artifact.run_id,
        version=artifact.version,
        kind=artifact.kind,
        filename=artifact.filename,
        mime_type=artifact.mime_type,
        sha256=artifact.sha256,
        size_bytes=artifact.size_bytes,
        created_at=artifact.created_at,
        validation_status=artifact.validation_status,
    )


def _persist_artifacts(
    store: TailoringRunStore, run_id: str, docx_bytes: bytes | None, pdf_bytes: bytes | None,
    validation_status: str, company: str, role: str,
) -> list[TailoredArtifact]:
    saved = []
    if docx_bytes:
        saved.append(
            store.save_artifact(
                run_id, "DOCX", docx_bytes,
                safe_artifact_filename(company, role, store.next_artifact_version(run_id, "DOCX"), "docx"),
                validation_status,
            )
        )
    if pdf_bytes:
        saved.append(
            store.save_artifact(
                run_id, "PDF", pdf_bytes,
                safe_artifact_filename(company, role, store.next_artifact_version(run_id, "PDF"), "pdf"),
                validation_status,
            )
        )
    return saved


def _validation_out(validation) -> ArtifactValidationOut:
    return ArtifactValidationOut(
        status=str(validation.status),
        findings=[
            ValidationFindingOut(
                code=f.code, severity=str(f.severity), category=str(f.category),
                message=f.message, details=dict(f.details),
            )
            for f in validation.findings
        ],
        original_page_count=validation.original_page_count,
        tailored_page_count=validation.tailored_page_count,
    )


def _report_out(report) -> FinalApplicationReportOut:
    return FinalApplicationReportOut(
        company=report.company, role=report.role, candidate_fit=report.candidate_fit,
        fit_breakdown=dict(report.fit_breakdown), original_alignment=report.original_alignment,
        tailored_alignment=report.tailored_alignment, strong_matches=list(report.strong_matches),
        partial_matches=list(report.partial_matches), true_gaps=list(report.true_gaps),
        unsupported_claims=list(report.unsupported_claims), validation=_validation_out(report.validation),
        fidelity_mode=str(report.fidelity_mode), original_page_count=report.original_page_count,
        tailored_page_count=report.tailored_page_count,
        artifacts=[
            ArtifactMetadataOut(
                artifact_id=a.artifact_id, run_id=a.run_id, version=a.version, kind=a.kind,
                filename=a.filename, mime_type=a.mime_type, sha256=a.sha256, size_bytes=a.size_bytes,
                created_at=a.created_at, validation_status=str(a.validation_status),
            )
            for a in report.artifacts
        ],
    )


def _change_out(change: ResumeChange) -> ResumeChangeOut:
    return ResumeChangeOut(
        change_id=change.change_id, section=change.section, source_index=change.source_index,
        original_text=change.original_text, proposed_text=change.proposed_text,
        category=str(change.category), reason=change.reason, job_requirement=change.job_requirement,
        evidence_source=change.evidence_source, evidence_text=change.evidence_text,
        validation_status=str(change.validation_status), disposition=str(change.disposition),
        manual_text=change.manual_text,
    )


@router.post("/preview", response_model=TailorResult)
def tailor_preview(
    body: TailorRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    optimizer: ResumeTailoringOptimizer = Depends(get_optimizer),
):
    profile_row = db.get(Profile, user.id)
    if not profile_row:
        raise HTTPException(status_code=400, detail="Upload a resume before tailoring.")
    profile_dict = json.loads(profile_row.data_json)
    profile = CareerTruthProfile.from_dict(profile_dict)

    if _profile_is_too_sparse(profile):
        raise HTTPException(
            status_code=422,
            detail=(
                "Your profile has no skills and no work experience details -- there isn't "
                "enough real information to tailor a resume honestly. Review it with "
                "GET /profile and fix any missing sections with PUT /profile, then try again."
            ),
        )

    job_description = body.job_description
    job_dict: dict = {"description": job_description}
    if body.job_id:
        job_row = db.get(Job, body.job_id)
        if not job_row:
            raise HTTPException(status_code=404, detail="Job not found")
        job_dict = json.loads(job_row.data_json)
        job_description = job_dict.get("description", "")
    if not job_description:
        raise HTTPException(
            status_code=400,
            detail="Provide job_description, or a job_id for a captured job with a description.",
        )

    job_analysis = JobAnalyzer().analyze(job_description)
    benchmark = ResumeBenchmarker().benchmark(profile, job_analysis)
    gap_report = GapAnalyzer().analyze(profile, job_analysis, benchmark)

    fit = score_candidate_fit(profile_dict, job_dict)
    candidate_fit_score = fit["score"] or None

    resume_file = db.get(ResumeFile, user.id)
    use_docx_pipeline = (
        resume_file is not None
        and os.path.splitext(resume_file.filename)[1].lower() == ".docx"
    )

    company = job_dict.get("company", "") or ""
    role = job_dict.get("title", "") or job_dict.get("role", "") or ""
    baseline_tailored_text = ""

    docx_result = None
    changes: list[ResumeChange] = []
    if use_docx_pipeline:
        docx_result = run_docx_tailoring_pipeline(
            resume_file.data, profile, job_analysis, gap_report, convert_to_pdf=body.generate_pdf
        )
        docx_result = correct_docx_length_once(
            original_docx_bytes=resume_file.data, docx_result=docx_result, profile=profile,
            gap_report=gap_report, llm=getattr(optimizer.tailorer, "llm", None),
        )
        score, matched, missing = optimizer._score_resume(
            docx_result.tailored_scoring_text, job_analysis, profile
        )
        result = OptimizationResult(
            tailored_resume=docx_result.tailored_scoring_text,
            final_score=score,
            iterations=1,
            ceiling_reached=False,
            missing_qualifications=missing,
        )
        changes = list(docx_result.changes)
        fidelity_mode = FidelityMode.PRESERVED
        artifact_validation = docx_result.validation
    else:
        initial_tailored = optimizer.tailorer.tailor(
            profile, job_analysis, gap_report, conservative=body.conservative
        )
        result = optimizer.optimize(
            profile, job_analysis, initial_tailored, gap_report, conservative=body.conservative
        )
        changes = build_freeform_changes(profile, result.tailored_resume, gap_report)
        fidelity_mode = FidelityMode.RECONSTRUCTED

        # Always generate+validate through the shared gate (reportlab-only, no
        # Word dependency) so report/validation/artifact fields are always
        # real; the legacy pdf_base64 field stays gated on body.generate_pdf.
        # An over-length result gets one condensation repair.
        style_hints = _extract_style_hints(resume_file)
        pdf_artifact_bytes, artifact_validation, repaired_text, changes, _attempts = build_freeform_artifact(
            tailored_text=result.tailored_resume, changes=changes, profile=profile,
            target_length=body.target_length, style_hints=style_hints,
            llm=getattr(optimizer.tailorer, "llm", None),
        )
        if repaired_text != result.tailored_resume:
            score, _matched, missing = optimizer._score_resume(repaired_text, job_analysis, profile)
            result = dataclasses.replace(
                result, tailored_resume=repaired_text, final_score=score, missing_qualifications=missing,
            )
        baseline_tailored_text = result.tailored_resume

    diff_report = DiffGenerator().generate_diff(profile, result.tailored_resume)
    unsupported_claims = find_unsupported_claims(gap_report, result.tailored_resume)

    pdf_base64 = None
    pdf_issues: list[str] = []
    docx_base64 = None
    docx_conversion_available = None
    original_page_count = None
    tailored_page_count = None
    page_count_preserved = None
    bullet_warnings: list[str] = []
    bullets_evaluated = 0
    bullets_changed = 0
    bullets_rejected = 0
    addressable_requirements = 0
    tailoring_seems_shallow = False
    docx_bytes_for_artifact = None
    pdf_bytes_for_artifact = None

    if use_docx_pipeline:
        docx_base64 = _b64_if_downloadable(docx_result.docx_bytes, artifact_validation)
        docx_conversion_available = docx_result.conversion_available
        original_page_count = docx_result.original_page_count
        tailored_page_count = docx_result.tailored_page_count
        page_count_preserved = docx_result.page_count_preserved
        bullet_warnings = docx_result.bullet_warnings
        pdf_issues = docx_result.pdf_validation_issues
        bullets_evaluated = docx_result.bullets_evaluated
        bullets_changed = docx_result.bullets_changed
        bullets_rejected = docx_result.bullets_rejected
        addressable_requirements = docx_result.addressable_requirements
        tailoring_seems_shallow = docx_result.tailoring_seems_shallow
        docx_bytes_for_artifact = docx_result.docx_bytes
        if body.generate_pdf and docx_result.pdf_bytes:
            pdf_base64 = _b64_if_downloadable(docx_result.pdf_bytes, artifact_validation)
            pdf_bytes_for_artifact = docx_result.pdf_bytes
    else:
        pdf_bytes_for_artifact = pdf_artifact_bytes
        if body.generate_pdf:
            pdf_base64 = _b64_if_downloadable(pdf_artifact_bytes, artifact_validation)

    # Persist the run + generated artifacts (Steps 16-20, spec 002).
    store = TailoringRunStore(db)
    run = store.create_run(
        user_id=user.id,
        original_resume_id=resume_file.id if resume_file else None,
        original_resume_version=resume_file.version if resume_file else None,
        profile_snapshot_hash=profile_snapshot_hash(profile_dict),
        profile_snapshot=profile_dict,
        job_snapshot=job_dict,
        request_options=body.model_dump(),
        candidate_fit=fit,
        proposed_changes=changes_to_json(changes),
        validation=validation_to_json(artifact_validation),
        baseline_tailored_text=baseline_tailored_text,
        source_kind="DOCX" if use_docx_pipeline else "PDF",
    )
    saved_artifacts = _persist_artifacts(
        store, run.id, docx_bytes_for_artifact, pdf_bytes_for_artifact,
        str(artifact_validation.status), company, role,
    )

    # build_final_report's `artifacts` param expects
    # resume_tailorer.artifacts.models.ArtifactMetadata instances -- build
    # them from the just-saved storage rows.
    from resume_tailorer.artifacts.models import ArtifactMetadata as _ArtifactMetadata
    from resume_tailorer.artifacts.models import ValidationStatus as _ValidationStatus

    report_artifacts = tuple(
        _ArtifactMetadata(
            artifact_id=a.id, run_id=a.run_id, version=a.version, kind=a.kind,
            filename=a.filename, mime_type=a.mime_type, sha256=a.sha256, size_bytes=a.size_bytes,
            created_at=a.created_at, validation_status=_ValidationStatus(a.validation_status),
        )
        for a in saved_artifacts
    )
    report = build_final_report(
        candidate_fit=candidate_fit_score,
        fit_breakdown=fit.get("breakdown", {}),
        original_alignment=benchmark.original_match_score,
        tailored_alignment=result.final_score,
        gap_report=gap_report,
        validation=artifact_validation,
        artifacts=report_artifacts,
        company=company,
        role=role or "Target Role",
        fidelity_mode=fidelity_mode,
        unsupported_claims=unsupported_claims,
    )
    store.update_run(run, report=report_to_json(report))

    return TailorResult(
        candidate_fit_score=candidate_fit_score,
        original_match_score=benchmark.original_match_score,
        tailored_resume=result.tailored_resume,
        final_score=result.final_score,
        iterations=result.iterations,
        ceiling_reached=result.ceiling_reached,
        missing_qualifications=result.missing_qualifications,
        gap_summary=gap_report.summary,
        gaps=[
            GapItemOut(
                requirement=item.requirement,
                category=item.category.name,
                reason=item.reason,
                evidence=item.candidate_evidence,
            )
            for item in gap_report.items
        ],
        changes=[
            BulletChangeOut(
                original=change.original,
                tailored=change.tailored,
                change_type=change.change_type,
                reasoning=change.reasoning,
            )
            for change in diff_report.changes
        ],
        fabrication_risk_issues=diff_report.issues,
        unsupported_claims_added=unsupported_claims,
        pdf_base64=pdf_base64,
        pdf_issues=pdf_issues,
        docx_base64=docx_base64,
        original_page_count=original_page_count,
        tailored_page_count=tailored_page_count,
        page_count_preserved=page_count_preserved,
        docx_conversion_available=docx_conversion_available,
        bullet_warnings=bullet_warnings,
        bullets_evaluated=bullets_evaluated,
        bullets_changed=bullets_changed,
        bullets_rejected=bullets_rejected,
        addressable_requirements=addressable_requirements,
        tailoring_seems_shallow=tailoring_seems_shallow,
        run_id=run.id,
        report=_report_out(report),
        validation=_validation_out(artifact_validation),
        resume_changes=[_change_out(c) for c in changes],
        artifacts=[_artifact_out(a) for a in saved_artifacts],
    )


@router.get("/runs/{run_id}", response_model=TailoringRunOut)
def get_run(run_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    store = TailoringRunStore(db)
    run = store.get_owned_run(run_id, user.id)
    if run is None:
        raise HTTPException(status_code=404, detail="Tailoring run not found")

    changes = changes_from_json(json.loads(run.reviewed_changes_json))
    validation = validation_from_json(json.loads(run.validation_json))
    report_data = json.loads(run.report_json) if run.report_json and run.report_json != "{}" else None
    artifacts = (
        db.query(TailoredArtifact)
        .filter(TailoredArtifact.run_id == run.id, TailoredArtifact.user_id == user.id)
        .all()
    )
    return TailoringRunOut(
        run_id=run.id,
        state=run.state,
        report=_report_from_json(report_data, validation) if report_data else _empty_report_out(validation),
        changes=[_change_out(c) for c in changes],
        validation=_validation_out(validation),
        artifacts=[_artifact_out(a) for a in artifacts],
    )


def _empty_report_out(validation) -> FinalApplicationReportOut:
    return FinalApplicationReportOut(
        company="", role="", candidate_fit=None, fit_breakdown={}, original_alignment=0.0,
        tailored_alignment=0.0, validation=_validation_out(validation), fidelity_mode="RECONSTRUCTED",
        original_page_count=validation.original_page_count, tailored_page_count=validation.tailored_page_count,
    )


def _report_from_json(data: dict, validation) -> FinalApplicationReportOut:
    return FinalApplicationReportOut(
        company=data.get("company", ""), role=data.get("role", ""),
        candidate_fit=data.get("candidate_fit"), fit_breakdown=data.get("fit_breakdown", {}),
        original_alignment=data.get("original_alignment", 0.0),
        tailored_alignment=data.get("tailored_alignment", 0.0),
        strong_matches=data.get("strong_matches", []), partial_matches=data.get("partial_matches", []),
        true_gaps=data.get("true_gaps", []), unsupported_claims=data.get("unsupported_claims", []),
        validation=_validation_out(validation), fidelity_mode=data.get("fidelity_mode", "RECONSTRUCTED"),
        original_page_count=data.get("original_page_count"), tailored_page_count=data.get("tailored_page_count"),
        artifacts=data.get("artifacts", []),
    )


@router.patch("/runs/{run_id}/changes")
def review_changes(
    run_id: str, body: ReviewChangesRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    store = TailoringRunStore(db)
    run = store.get_owned_run(run_id, user.id)
    if run is None:
        raise HTTPException(status_code=404, detail="Tailoring run not found")

    changes = changes_from_json(json.loads(run.reviewed_changes_json))
    by_id = {c.change_id: c for c in changes}

    unknown = [item.change_id for item in body.changes if item.change_id not in by_id]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown change_id(s): {unknown}")
    seen = set()
    duplicates = set()
    for item in body.changes:
        if item.change_id in seen:
            duplicates.add(item.change_id)
        seen.add(item.change_id)
    if duplicates:
        raise HTTPException(status_code=400, detail=f"Duplicate change_id(s): {sorted(duplicates)}")

    # Validate manual edits against the profile THIS RUN was proposed
    # against, not whatever the live profile looks like now -- a PUT
    # /profile edit between preview and review must not change what
    # validate_manual_text considers grounded.
    profile = CareerTruthProfile.from_dict(json.loads(run.profile_snapshot_json))

    updated: dict[str, ResumeChange] = {}
    for item in body.changes:
        try:
            disposition = ChangeDisposition(item.disposition)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown disposition: {item.disposition}")
        change = by_id[item.change_id]
        manual_text = None
        if disposition is ChangeDisposition.MANUALLY_EDITED:
            if not item.manual_text:
                raise HTTPException(status_code=400, detail="manual_text is required for MANUALLY_EDITED")
            issues = validate_manual_text(change.original_text, item.manual_text, profile)
            if issues:
                raise HTTPException(
                    status_code=400,
                    detail={"message": "Manual edit failed safety checks", "issues": issues},
                )
            manual_text = item.manual_text
        updated[item.change_id] = ResumeChange(
            change_id=change.change_id, section=change.section, source_index=change.source_index,
            # proposed_text is left as the AI's original proposal -- never
            # overwritten -- so regenerate_freeform_artifact can still find
            # it verbatim in the run's baseline text. See ResumeChange.manual_text.
            original_text=change.original_text, proposed_text=change.proposed_text, category=change.category,
            reason=change.reason, job_requirement=change.job_requirement,
            evidence_source=change.evidence_source, evidence_text=change.evidence_text,
            validation_status=change.validation_status, disposition=disposition, manual_text=manual_text,
        )

    final_changes = [updated.get(c.change_id, c) for c in changes]
    store.update_run(run, reviewed_changes=changes_to_json(final_changes), state="REVIEWED")
    return {"run_id": run.id, "state": "REVIEWED", "changes": [_change_out(c).model_dump() for c in final_changes]}


@router.post("/runs/{run_id}/regenerate", response_model=TailorResult)
def regenerate(run_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    store = TailoringRunStore(db)
    run = store.get_owned_run(run_id, user.id)
    if run is None:
        raise HTTPException(status_code=404, detail="Tailoring run not found")

    # Regenerate against the EXACT profile this run was proposed against
    # (the immutable snapshot), never a fresh `db.get(Profile, ...)` --
    # otherwise a PUT /profile edit made between preview and regenerate
    # would silently re-splice/re-validate already-reviewed changes
    # against a different profile than the one that produced them.
    profile_dict = json.loads(run.profile_snapshot_json)
    profile = CareerTruthProfile.from_dict(profile_dict)
    job_dict = json.loads(run.job_snapshot_json)
    job_analysis, benchmark, gap_report, fit = _rebuild_job_context(db, profile, profile_dict, job_dict)

    changes = changes_from_json(json.loads(run.reviewed_changes_json))
    request_options = json.loads(run.request_options_json)
    company = job_dict.get("company", "") or ""
    role = job_dict.get("title", "") or job_dict.get("role", "") or ""

    is_docx = run.source_kind == "DOCX"
    resume_file = _run_resume_file(db, run)

    if is_docx:
        if resume_file is None:
            raise HTTPException(
                status_code=409,
                detail="The exact resume this run was created from is no longer available.",
            )
        docx_result = regenerate_docx_artifact(
            original_docx_bytes=resume_file.data, changes=changes, profile=profile,
            gap_report=gap_report, convert_to_pdf=bool(request_options.get("generate_pdf")),
        )
        tailored_resume = docx_result.tailored_scoring_text
        validation = docx_result.validation
        docx_bytes = docx_result.docx_bytes
        pdf_bytes = docx_result.pdf_bytes
        fidelity_mode = FidelityMode.PRESERVED
    else:
        style_hints = _extract_style_hints(resume_file)
        pdf_bytes, tailored_resume = regenerate_freeform_artifact(
            baseline_tailored_text=run.baseline_tailored_text, changes=changes, profile=profile,
            target_length=request_options.get("target_length", "preserve"),
            style_hints=style_hints or {}, company=company, role=role,
        )
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        try:
            validation = PDFValidator().validate_artifact(
                tmp_path, profile=profile, expected_page_count=None, accepted_changes=changes,
                target_length=max_pages_label(request_options.get("target_length", "preserve"), style_hints),
            )
        finally:
            os.remove(tmp_path)
        docx_bytes = None
        fidelity_mode = FidelityMode.RECONSTRUCTED

    unsupported_claims = find_unsupported_claims(gap_report, tailored_resume)
    tailored_alignment, _matched, missing_qualifications = ResumeTailoringOptimizer._score_resume(
        tailored_resume, job_analysis, profile
    )
    saved_artifacts = _persist_artifacts(
        store, run.id, docx_bytes, pdf_bytes, str(validation.status), company, role,
    )
    report = build_final_report(
        candidate_fit=fit["score"] or None,
        fit_breakdown=fit.get("breakdown", {}),
        original_alignment=benchmark.original_match_score,
        tailored_alignment=tailored_alignment,
        gap_report=gap_report,
        validation=validation,
        artifacts=(),
        company=company,
        role=role or "Target Role",
        fidelity_mode=fidelity_mode,
        unsupported_claims=unsupported_claims,
    )
    new_state = "VALIDATED" if str(validation.status) != "FAIL" else "FAILED"
    store.update_run(run, validation=validation_to_json(validation), report=report_to_json(report), state=new_state)

    diff_report = DiffGenerator().generate_diff(profile, tailored_resume)

    return TailorResult(
        candidate_fit_score=fit["score"] or None,
        original_match_score=benchmark.original_match_score,
        tailored_resume=tailored_resume,
        final_score=tailored_alignment,
        iterations=1,
        ceiling_reached=False,
        missing_qualifications=missing_qualifications,
        gap_summary=gap_report.summary,
        gaps=[
            GapItemOut(requirement=i.requirement, category=i.category.name, reason=i.reason, evidence=i.candidate_evidence)
            for i in gap_report.items
        ],
        changes=[
            BulletChangeOut(original=c.original, tailored=c.tailored, change_type=c.change_type, reasoning=c.reasoning)
            for c in diff_report.changes
        ],
        fabrication_risk_issues=diff_report.issues,
        unsupported_claims_added=unsupported_claims,
        pdf_base64=_b64_if_downloadable(pdf_bytes, validation),
        docx_base64=_b64_if_downloadable(docx_bytes, validation),
        run_id=run.id,
        report=_report_out(report),
        validation=_validation_out(validation),
        resume_changes=[_change_out(c) for c in changes],
        artifacts=[_artifact_out(a) for a in saved_artifacts],
    )


@router.get("/artifacts/{artifact_id}")
def download_artifact(artifact_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    store = TailoringRunStore(db)
    artifact = store.get_owned_artifact(artifact_id, user.id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")

    if artifact.validation_status == "FAIL":
        raise HTTPException(
            status_code=409,
            detail="This artifact failed validation and is not available as an application-ready download.",
        )

    headers = {
        "Content-Disposition": f'attachment; filename="{artifact.filename}"',
        "ETag": artifact.sha256,
        "X-Validation-Status": artifact.validation_status,
    }
    return Response(content=artifact.data, media_type=artifact.mime_type, headers=headers)
