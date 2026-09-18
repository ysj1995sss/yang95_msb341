"""Pure-logic helper functions for the Job Search Streamlit page.

These functions contain NO Streamlit calls (no `import streamlit`). They exist
so the form-building, display-formatting, and filtering logic used by the
Job Search UI can be unit tested without a browser or a running Streamlit app.
"""

from typing import Any, Dict, List, Optional, Tuple

from resume_tailorer.job_search.models import JobPosting, SearchGoals

# Selection actions recognized by the dashboard filter, other than "all"
# and "unreviewed" which are handled specially.
_KNOWN_ACTIONS = {"interested", "saved", "skipped", "applied"}


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
    """Build a SearchGoals object from a dict of raw form inputs.

    Args:
        form_data: Dict of values collected from the Streamlit search goals form.
            Expected keys: job_title, industries, min_salary, max_salary,
            location, remote_preference, sponsorship_required, experience_level,
            company_size, target_companies, exclude_companies, employment_type,
            relocation_willing.
            `target_companies` / `exclude_companies` may be a comma-separated
            string or a list; both are normalized to a list of strings.

    Returns:
        A validated SearchGoals instance.

    Raises:
        ValueError: If a required field is missing/blank, or min_salary > max_salary.
    """
    job_title = (form_data.get("job_title") or "").strip()
    if not job_title:
        raise ValueError("job_title is required")

    location = (form_data.get("location") or "").strip()
    if not location:
        raise ValueError("location is required")

    min_salary = form_data.get("min_salary") or 0
    max_salary = form_data.get("max_salary") or 0

    if min_salary > max_salary:
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
        experience_level=form_data.get("experience_level") or "",
        company_size=form_data.get("company_size") or "",
        target_companies=_parse_comma_separated(form_data.get("target_companies")),
        exclude_companies=_parse_comma_separated(form_data.get("exclude_companies")),
        employment_type=form_data.get("employment_type") or "full-time",
        relocation_willing=bool(form_data.get("relocation_willing", False)),
    )


def _format_salary(salary_min: Optional[int], salary_max: Optional[int]) -> str:
    """Format a salary range as e.g. '$100K-$150K'."""
    if salary_min is None and salary_max is None:
        return "Not specified"

    def _to_k(value: int) -> str:
        return f"${round(value / 1000)}K"

    if salary_min is not None and salary_max is not None:
        return f"{_to_k(salary_min)}-{_to_k(salary_max)}"
    if salary_min is not None:
        return f"{_to_k(salary_min)}+"
    return f"Up to {_to_k(salary_max)}"


def _format_date(dt) -> str:
    """Format a date-like object, falling back to 'Unknown'."""
    if dt is None:
        return "Unknown"
    try:
        return dt.strftime("%Y-%m-%d")
    except AttributeError:
        return str(dt)


def format_job_for_display(job: JobPosting, fit_score: Optional[float] = None) -> Dict[str, str]:
    """Format a JobPosting (and optional fit score) into display-ready strings.

    Args:
        job: JobPosting to format.
        fit_score: Optional 0-100 fit score.

    Returns:
        Dict of formatted strings suitable for a dashboard table/expander row.
    """
    return {
        "Company": job.company or "Unknown",
        "Title": job.title or "Unknown",
        "Location": job.location or "Unknown",
        "Salary": _format_salary(job.salary_min, job.salary_max),
        "Work Mode": job.work_mode or "Not specified",
        "Sponsorship": "Yes" if job.sponsorship_available else "No",
        "Posted Date": _format_date(job.posted_date),
        "Source": job.source.value if job.source else "Unknown",
        "Fit Score": "N/A" if fit_score is None else f"{round(fit_score)}%",
        "URL": job.url or "",
    }


def filter_jobs_by_action(
    jobs_with_selections: List[Tuple[JobPosting, Optional[str]]],
    action_filter: str,
) -> List[JobPosting]:
    """Filter jobs by the user's latest selection/action status.

    Args:
        jobs_with_selections: List of (JobPosting, action) tuples, where action
            is the user's latest recorded action for that job (e.g.
            "interested", "saved", "skipped", "applied") or None if the job
            has not been reviewed yet.
        action_filter: One of "all", "interested", "saved", "skipped",
            "applied", "unreviewed".

    Returns:
        List of JobPosting objects matching the filter.
    """
    if action_filter == "all":
        return [job for job, _ in jobs_with_selections]

    if action_filter == "unreviewed":
        return [job for job, action in jobs_with_selections if action is None]

    return [job for job, action in jobs_with_selections if action == action_filter]
