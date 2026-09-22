"""
Candidate fit scoring backed by the existing resume_tailorer.CandidateFitScorer
(skills 40% / experience-level 30% / education 20% / sponsorship 10%),
instead of job-copilot's naive keyword-overlap heuristic. Since the stored
profile is already CareerTruthProfile.to_dict() (see app.models.Profile),
no adapter is needed here -- CareerTruthProfile.from_dict() round-trips it
directly.
"""

from resume_tailorer.models.career_profile import CareerTruthProfile
from resume_tailorer.job_search.candidate_fit import CandidateFitScorer
from resume_tailorer.job_search.models import JobPosting, JobSource

FitBreakdown = dict[str, str]
FitResult = dict[str, float | FitBreakdown]

_scorer = CandidateFitScorer()

_EMPTY_PROFILE = CareerTruthProfile(
    contact_info={}, education=[], work_experience=[], skills=[], tools=[], certifications=[], accomplishments=[]
)


def _profile_dict_to_engine(profile: dict) -> CareerTruthProfile:
    if not profile:
        return _EMPTY_PROFILE
    return CareerTruthProfile.from_dict(profile)


def _job_dict_to_posting(job: dict) -> JobPosting:
    source_raw = (job.get("source") or "company_pages").lower()
    try:
        source = JobSource(source_raw)
    except ValueError:
        source = JobSource.COMPANY_PAGES

    sponsorship_raw = job.get("sponsorship")
    sponsorship_available = {"yes": True, "no": False}.get(sponsorship_raw)

    return JobPosting(
        source=source,
        source_id=job.get("original_url") or job.get("title", ""),
        company=job.get("company") or "",
        title=job.get("title") or "",
        location=job.get("location") or "",
        description=job.get("description") or "",
        experience_required=job.get("employment_type"),
        education_required=None,
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
    score = _scorer.score_fit(engine_profile, posting)
    if score is None:
        return {
            "score": 0.0,
            "breakdown": {"reason": "Not enough job/profile data to score fit honestly"},
        }

    return {
        "score": score,
        "breakdown": {"method": "skills 40% / experience 30% / education 20% / sponsorship 10%"},
    }
