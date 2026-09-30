"""
Candidate fit scoring backed by resume_tailorer.CandidateFitScorer (cf-v2).
"""

import re

from resume_tailorer.models.career_profile import CareerTruthProfile
from resume_tailorer.job_search.candidate_fit import CandidateFitScorer
from resume_tailorer.job_search.models import JobPosting, JobSource
from resume_tailorer.job_search.normalize import normalize_sponsorship, YES, NO

FitBreakdown = dict
FitResult = dict[str, float | FitBreakdown | None]

_scorer = CandidateFitScorer()

_EMPTY_PROFILE = CareerTruthProfile(
    contact_info={}, education=[], work_experience=[], skills=[], tools=[], certifications=[], accomplishments=[]
)

_EMPLOYMENT_TYPES = frozenset(
    {"full-time", "part-time", "contract", "internship", "temporary", "unknown"}
)


def _profile_dict_to_engine(profile: dict) -> CareerTruthProfile:
    if not profile:
        return _EMPTY_PROFILE
    return CareerTruthProfile.from_dict(profile)


def _experience_from_job(job: dict) -> str | None:
    for key in ("experience_required", "experience", "years_experience"):
        raw = job.get(key)
        if raw and str(raw).strip().lower() not in _EMPLOYMENT_TYPES:
            return str(raw)
    desc = job.get("description") or ""
    match = re.search(r"(\d+)\+?\s*[\-–]?\s*(\d+)?\s*(years|yrs)", desc, re.IGNORECASE)
    if match:
        return match.group(0)
    return None


def _job_dict_to_posting(job: dict) -> JobPosting:
    source_raw = (job.get("source") or "company_pages").lower()
    try:
        source = JobSource(source_raw)
    except ValueError:
        source = JobSource.COMPANY_PAGES

    sponsorship_state = normalize_sponsorship(job.get("sponsorship"))
    if sponsorship_state == YES:
        sponsorship_available: bool | None = True
    elif sponsorship_state == NO:
        sponsorship_available = False
    else:
        sponsorship_available = None

    return JobPosting(
        source=source,
        source_id=(
            (job.get("external_ids") or {}).get(source_raw)
            or job.get("original_url")
            or job.get("title", "")
        ),
        company=job.get("company") or "",
        title=job.get("title") or "",
        location=job.get("location") or "",
        description=job.get("description") or "",
        experience_required=_experience_from_job(job),
        education_required=job.get("education_required") or job.get("education"),
        sponsorship_available=sponsorship_available,
        work_mode=job.get("work_mode"),
        url=job.get("original_url") or "",
        ats_platform=job.get("ats_platform") or "Unknown",
    )


def score_candidate_fit(profile: dict, job: dict) -> FitResult:
    engine_profile = _profile_dict_to_engine(profile)
    if not engine_profile.skills and not engine_profile.work_experience:
        return {
            "score": 0.0,
            "breakdown": {"reason": "No profile uploaded -- upload a resume to score fit"},
        }

    posting = _job_dict_to_posting(job)
    detailed = _scorer.score_fit_detailed(engine_profile, posting)
    score = detailed.overall_fit

    breakdown = detailed.to_dict()
    breakdown["method"] = "cf-v2 eligibility/core/preferred/evidence"
    if score is None:
        breakdown["reason"] = "Not enough information in the posting to score fit"
    return {
        "score": None if score is None else float(score),
        "breakdown": breakdown,
    }
