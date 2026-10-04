"""Pure-logic helper functions for the Job Search Streamlit page.

These functions contain NO Streamlit calls (no `import streamlit`). They exist
so the form-building, display-formatting, and filtering logic used by the
Job Search UI can be unit tested without a browser or a running Streamlit app.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from resume_tailorer.job_search.job_quality import evaluate_job_quality, quality_label
from resume_tailorer.job_search.models import (
    FitResult,
    JobPosting,
    JobQualityStatus,
    SearchGoals,
    TriageAction,
    canonicalize_triage_action,
)
from resume_tailorer.job_search.normalize import (
    NOT_STATED,
    NO,
    POSSIBLE,
    UNKNOWN,
    YES,
    normalize_sponsorship,
)

_KNOWN_ACTIONS = {
    TriageAction.SAVE.value,
    TriageAction.APPLY.value,
    TriageAction.PASS.value,
    "interested",
    "saved",
    "skipped",
    "applied",
}


@dataclass(frozen=True)
class JobCardView:
    company: str
    title: str
    location: str
    compensation: str
    sponsorship: str
    fit: str
    quality: str
    action: str
    strong_matches: tuple[str, ...]
    partial_matches: tuple[str, ...]
    true_gaps: tuple[str, ...]


def build_job_card_view(
    job: JobPosting,
    fit: Optional[FitResult],
    quality: Optional[JobQualityStatus],
    action: Optional[str],
) -> JobCardView:
    """Build one honest, display-ready job record without inventing zeroes."""
    action_labels = {
        TriageAction.SAVE: "Saved",
        TriageAction.APPLY: "Selected to tailor",
        TriageAction.PASS: "Passed",
        TriageAction.UNREVIEWED: "Not reviewed",
    }
    normalized_action = canonicalize_triage_action(action)
    return JobCardView(
        company=job.company or "Unknown company",
        title=job.title or "Untitled role",
        location=job.location or "Not stated",
        compensation=(
            "Not stated"
            if job.salary_min is None and job.salary_max is None
            else _format_salary(job.salary_min, job.salary_max)
        ),
        sponsorship=(
            "Not stated"
            if job.sponsorship_available is None
            else _format_sponsorship(job.sponsorship_available)
        ),
        fit="Not assessed" if fit is None or fit.overall_fit is None else f"{round(fit.overall_fit)}%",
        quality=quality_label(quality or evaluate_job_quality(job)),
        action=action_labels.get(normalized_action, "Not reviewed"),
        strong_matches=tuple(fit.strong_matches) if fit else (),
        partial_matches=tuple(fit.partial_matches) if fit else (),
        true_gaps=tuple(fit.true_gaps) if fit else (),
    )


def _parse_comma_separated(value: Any) -> List[str]:
    """Convert a comma-separated string (or list) into a clean list of strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return []


def build_search_goals_from_form(form_data: Dict[str, Any]) -> SearchGoals:
    """Build a SearchGoals object from a dict of raw form inputs."""
    job_title = (form_data.get("job_title") or "").strip()
    if not job_title:
        raise ValueError("job_title is required")

    location = (form_data.get("location") or "").strip()

    min_salary = form_data.get("min_salary") or 0
    max_salary = form_data.get("max_salary") or 0

    if max_salary and min_salary > max_salary:  # 0 = no maximum
        raise ValueError(
            f"min_salary ({min_salary}) must be <= max_salary ({max_salary})"
        )

    industries = form_data.get("industries") or []
    if isinstance(industries, str):
        industries = _parse_comma_separated(industries)

    return SearchGoals(
        job_title=job_title,
        industries=list(industries),
        min_salary=min_salary,
        max_salary=max_salary,
        location=location,
        remote_preference=form_data.get("remote_preference") or "any",
        sponsorship_required=bool(form_data.get("sponsorship_required", False)),
        experience_level=",".join(_parse_comma_separated(form_data.get("experience_level"))),
        company_size=form_data.get("company_size") or "",
        target_companies=_parse_comma_separated(form_data.get("target_companies")),
        exclude_companies=_parse_comma_separated(form_data.get("exclude_companies")),
        employment_type=",".join(_parse_comma_separated(form_data.get("employment_type"))),
        relocation_willing=bool(form_data.get("relocation_willing", False)),
    )


def _format_salary(salary_min: Optional[int], salary_max: Optional[int]) -> str:
    if salary_min is None and salary_max is None:
        return "Not specified"

    def _to_k(value: int) -> str:
        return f"${round(value / 1000)}K"

    if salary_min is not None and salary_max is not None:
        return f"{_to_k(salary_min)}-{_to_k(salary_max)}"
    if salary_min is not None:
        return f"{_to_k(salary_min)}+"
    return f"Up to {_to_k(salary_max)}"


def _format_sponsorship(value: Optional[bool]) -> str:
    state = normalize_sponsorship(value)
    labels = {
        YES: "Yes",
        NO: "No",
        POSSIBLE: "Possible",
        NOT_STATED: "Not stated",
        UNKNOWN: "Unknown",
    }
    return labels.get(state, "Unknown")


def _format_date(dt) -> str:
    if dt is None:
        return "Unknown"
    try:
        return dt.strftime("%Y-%m-%d")
    except AttributeError:
        return str(dt)


def format_job_for_display(
    job: JobPosting,
    fit_score: Optional[float] = None,
    fit_result: Optional[FitResult] = None,
    quality: Optional[JobQualityStatus] = None,
) -> Dict[str, str]:
    """Format a JobPosting (and optional fit) into display-ready strings."""
    overall = fit_score
    if fit_result is not None and fit_result.overall_fit is not None:
        overall = fit_result.overall_fit

    quality_status = quality if quality is not None else evaluate_job_quality(job)

    display = {
        "Company": job.company or "Unknown",
        "Title": job.title or "Unknown",
        "Location": job.location or "Unknown",
        "Salary": _format_salary(job.salary_min, job.salary_max),
        "Work Mode": job.work_mode or "Not specified",
        "Sponsorship": _format_sponsorship(job.sponsorship_available),
        "Posted Date": _format_date(job.posted_date),
        "Deadline": _format_date(job.application_deadline),
        "Source": job.source.value if job.source else "Unknown",
        "Quality": quality_label(quality_status),
        "Fit Score": "N/A" if overall is None else f"{round(overall)}%",
        "URL": job.url or "",
    }
    if fit_result is not None:
        def _pct(v: Optional[float]) -> str:
            return "N/A" if v is None else f"{round(v)}%"

        display["Fit Eligibility"] = _pct(fit_result.eligibility)
        display["Fit Core"] = _pct(fit_result.core_capabilities)
        display["Fit Preferred"] = _pct(fit_result.preferred_qualifications)
        display["Fit Evidence Confidence"] = _pct(fit_result.evidence_confidence)
        display["Fit Strong"] = "; ".join(fit_result.strong_matches[:5]) or "—"
        display["Fit Partial"] = "; ".join(fit_result.partial_matches[:5]) or "—"
        display["Fit Gaps"] = "; ".join(fit_result.true_gaps[:5]) or "—"
    return display


def filter_jobs_by_action(
    jobs_with_selections: List[Tuple[JobPosting, Optional[str]]],
    action_filter: str,
) -> List[JobPosting]:
    """Filter jobs by the user's latest selection/action status."""
    if action_filter == "all":
        return [job for job, _ in jobs_with_selections]

    if action_filter == "unreviewed":
        return [
            job
            for job, action in jobs_with_selections
            if canonicalize_triage_action(action) == TriageAction.UNREVIEWED
        ]

    wanted = canonicalize_triage_action(action_filter)
    return [
        job
        for job, action in jobs_with_selections
        if canonicalize_triage_action(action) == wanted
    ]

