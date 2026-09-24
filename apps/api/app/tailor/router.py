import base64
import json
import os
import tempfile

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db import get_db
from app.fit.scoring import score_candidate_fit
from app.models import Job, Profile, ResumeFile, User
from app.schemas.tailor import BulletChangeOut, GapItemOut, TailorRequest, TailorResult

from resume_tailorer.models.career_profile import CareerTruthProfile
from resume_tailorer.analyzers.job_analyzer import JobAnalyzer
from resume_tailorer.analyzers.resume_benchmarker import ResumeBenchmarker
from resume_tailorer.analyzers.gap_analyzer import GapAnalyzer, find_unsupported_claims
from resume_tailorer.tailorer.optimizer import ResumeTailoringOptimizer, OptimizationResult
from resume_tailorer.pdf.generator import PDFGenerator
from resume_tailorer.pdf.validator import PDFValidator
from resume_tailorer.diff_generator import DiffGenerator
from resume_tailorer.parsers import ResumeParser
from resume_tailorer.docx_export import run_docx_tailoring_pipeline

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
        # Passing tmp_path (not just raw_text) lets this also detect the
        # original's page count and font family directly from the PDF
        # structure, so "preserve" length actually means "same length as
        # what the user uploaded" and the output uses a similar font family
        # -- not just bullet style/heading emphasis from the text alone.
        return parser.extract_style_hints(raw_text, file_path=tmp_path)
    except Exception:
        return None
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def get_optimizer() -> ResumeTailoringOptimizer:
    try:
        return ResumeTailoringOptimizer()
    except ValueError as exc:
        # No LLM_MODEL / LLM_API_KEY configured -- fail clearly, not with a 500.
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

    # Spec 001 item 8/19: Candidate Fit (actual background vs. job) is
    # distinct from Resume Match (how well the CURRENT resume communicates
    # it) -- reuses the same weighted scorer already validated in
    # app.jobs.router, rather than reimplementing fit scoring here.
    fit = score_candidate_fit(profile_dict, job_dict)
    candidate_fit_score = fit["score"] if fit["score"] > 0 else None

    resume_file = db.get(ResumeFile, user.id)
    # DOCX originals go through the master-template splice pipeline (edits
    # the original's own paragraphs in place, preserving fonts/margins/
    # layout exactly) instead of a from-scratch reportlab PDF -- see
    # decisions/006 (and resume_tailorer.docx_export). PDF-only originals
    # have no editable structure to preserve, so they keep the existing
    # freeform-rewrite pipeline unchanged. `body.conservative` is simply
    # not read on the DOCX branch -- splicing into existing paragraphs has
    # no "full rewrite" mode to toggle in the first place.
    use_docx_pipeline = (
        resume_file is not None
        and os.path.splitext(resume_file.filename)[1].lower() == ".docx"
    )

    docx_result = None
    if use_docx_pipeline:
        docx_result = run_docx_tailoring_pipeline(
            resume_file.data, profile, job_analysis, gap_report, convert_to_pdf=body.generate_pdf
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
    else:
        initial_tailored = optimizer.tailorer.tailor(
            profile, job_analysis, gap_report, conservative=body.conservative
        )
        result = optimizer.optimize(
            profile, job_analysis, initial_tailored, gap_report, conservative=body.conservative
        )

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

    if use_docx_pipeline:
        docx_base64 = base64.b64encode(docx_result.docx_bytes).decode("ascii")
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
        if body.generate_pdf and docx_result.pdf_bytes:
            pdf_base64 = base64.b64encode(docx_result.pdf_bytes).decode("ascii")
    elif body.generate_pdf:
        pdf_path = None
        try:
            style_hints = _extract_style_hints(resume_file)
            # Resolve "preserve" to the concrete 1_page/2_page preset once so
            # PDFValidator enforces the SAME page limit generate() targeted,
            # rather than "preserve"'s own lenient fallback ceiling.
            effective_length = PDFGenerator.resolve_target_length(body.target_length, style_hints)
            pdf_path = PDFGenerator().generate(
                result.tailored_resume,
                profile.name,
                target_length=body.target_length,
                style_hints=style_hints,
            )
            validation = PDFValidator().validate(pdf_path, target_length=effective_length)
            pdf_issues = validation.issues
            if validation.passed:
                with open(pdf_path, "rb") as f:
                    pdf_base64 = base64.b64encode(f.read()).decode("ascii")
        finally:
            if pdf_path and os.path.exists(pdf_path):
                os.remove(pdf_path)

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
    )
