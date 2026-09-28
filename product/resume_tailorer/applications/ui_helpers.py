"""Pure formatting/filtering/sorting functions for the Applications dashboard UI.

No streamlit import here -- kept separate so this logic is unit-testable,
matching the pattern in job_search/ui_helpers.py.
"""

import os
from typing import Any, Callable, Dict, List, Optional

from resume_tailorer.applications.models import ApplicationStatus, ApplicationSubmission, ApplicationTracker

# Saved views (spec 003 Step 24) -- None means "no filter" (the "All" view).
STATUS_GROUPS: Dict[str, Optional[set]] = {
    "All": None,
    "Saved": {ApplicationStatus.DISCOVERED, ApplicationStatus.INTERESTED},
    "Applying": {ApplicationStatus.PREPARING, ApplicationStatus.READY_TO_APPLY},
    "Submitted": {ApplicationStatus.APPLIED},
    "Assessments": {ApplicationStatus.ASSESSMENT},
    "Interviews": {
        ApplicationStatus.RECRUITER_SCREEN,
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.FINAL_INTERVIEW,
    },
    "Offers": {ApplicationStatus.OFFER},
    "Rejected": {ApplicationStatus.REJECTED},
    "Withdrawn": {ApplicationStatus.WITHDRAWN},
}


def format_application_for_display(
    tracker: ApplicationTracker, submission: Optional[ApplicationSubmission] = None
) -> dict:
    """Format a (tracker, submission) pair into display-ready strings for a
    table row. submission is optional so this stays backward compatible
    with a caller that only has status-history data; Company/Role/etc.
    fall back to "—" rather than crashing when it's not available."""
    job = (submission.job_snapshot if submission else {}) or {}
    fit = (submission.candidate_fit_snapshot if submission else {}) or {}
    overall_fit = fit.get("overall_fit")
    resume_used = submission.resume_used if submission else ""

    return {
        "Company": job.get("company") or "—",
        "Role": job.get("title") or "—",
        "Applied Date": submission.submission_timestamp.strftime("%Y-%m-%d") if submission else "—",
        "Mode": submission.mode.value.replace("_", " ").title() if submission else "—",
        "Status": tracker.status.value.replace("_", " ").title(),
        "Candidate Fit": f"{overall_fit:.0f}%" if isinstance(overall_fit, (int, float)) else "—",
        "Resume Version": os.path.basename(resume_used) if resume_used else "—",
        "Next Action": (submission.next_action if submission else "") or "—",
        "Last Updated": tracker.status_updated.strftime("%Y-%m-%d %H:%M"),
        "Notes": tracker.notes if tracker.notes else "—",
        "Job Posting ID": tracker.job_posting_id,
        "Application ID": tracker.application_id,
    }


def group_for_status(status: ApplicationStatus) -> str:
    """Which saved view a status belongs to (used for the view selector's
    counts and for filtering)."""
    for view, statuses in STATUS_GROUPS.items():
        if statuses is not None and status in statuses:
            return view
    return "All"


def filter_applications(
    rows: List[dict],
    *,
    view: str = "All",
    company: str = "",
    role: str = "",
    mode: str = "",
    min_fit: Optional[float] = None,
) -> List[dict]:
    """Filter formatted display rows (spec 003 Step 24). All filters are
    optional and combine with AND. Text filters are case-insensitive
    substring matches; min_fit excludes rows with an unknown ("—") fit
    value (there's nothing honest to compare an unknown fit against a
    threshold with)."""
    result = rows

    allowed_statuses = STATUS_GROUPS.get(view)
    if allowed_statuses is not None:
        allowed_labels = {s.value.replace("_", " ").title() for s in allowed_statuses}
        result = [r for r in result if r["Status"] in allowed_labels]

    if company:
        needle = company.lower()
        result = [r for r in result if needle in r["Company"].lower()]

    if role:
        needle = role.lower()
        result = [r for r in result if needle in r["Role"].lower()]

    if mode:
        result = [r for r in result if r["Mode"] == mode]

    if min_fit is not None:
        def _fit_value(row: dict) -> Optional[float]:
            raw = row["Candidate Fit"]
            return float(raw.rstrip("%")) if raw != "—" else None

        result = [r for r in result if _fit_value(r) is not None and _fit_value(r) >= min_fit]

    return result


_SORT_KEYS: Dict[str, Callable[[dict], Any]] = {
    "Newest application": lambda r: r["Applied Date"],
    "Oldest pending": lambda r: r["Applied Date"],
    "Company": lambda r: r["Company"].lower(),
    "Status": lambda r: r["Status"],
    "Candidate Fit": lambda r: float(r["Candidate Fit"].rstrip("%")) if r["Candidate Fit"] != "—" else -1.0,
}


def sort_applications(rows: List[dict], sort_by: str) -> List[dict]:
    """Sort formatted display rows. Unknown sort_by values return rows
    unchanged rather than raising, since this reads directly from a
    Streamlit selectbox value."""
    key = _SORT_KEYS.get(sort_by)
    if key is None:
        return rows
    reverse = sort_by in ("Newest application", "Candidate Fit")
    return sorted(rows, key=key, reverse=reverse)
