"""Job posting quality / freshness evaluation (Step 6).

Honest labels only:
- EXPIRED when application_deadline is in the past
- STALE when posted_date is older than the stale threshold
- BROKEN when URL check confirmed closed (404/410)
- ACTIVE when URL is active (or unchecked mock) and dates look fresh
- UNKNOWN when we cannot tell (no dates, ambiguous URL status)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from resume_tailorer.job_search.models import JobPosting, JobQualityStatus

DEFAULT_STALE_DAYS = 45

_URL_ACTIVE = "active"
_URL_CLOSED = "closed"
_URL_UNKNOWN = "unknown"


def evaluate_job_quality(
    job: JobPosting,
    *,
    now: Optional[datetime] = None,
    stale_days: int = DEFAULT_STALE_DAYS,
    url_status: Optional[str] = None,
) -> JobQualityStatus:
    """Classify a posting's quality for dashboard display and filtering.

    Priority (most severe first): BROKEN → EXPIRED → STALE → ACTIVE → UNKNOWN.
    """
    clock = now or datetime.now()
    status = (url_status or "").strip().lower() or None

    if status == _URL_CLOSED:
        return JobQualityStatus.BROKEN

    if job.application_deadline is not None:
        deadline = job.application_deadline
        if deadline.tzinfo is not None and clock.tzinfo is None:
            clock = clock.replace(tzinfo=deadline.tzinfo)
        elif deadline.tzinfo is None and clock.tzinfo is not None:
            deadline = deadline.replace(tzinfo=clock.tzinfo)
        if deadline < clock:
            return JobQualityStatus.EXPIRED

    if job.posted_date is not None:
        posted = job.posted_date
        if posted.tzinfo is not None and clock.tzinfo is None:
            clock = clock.replace(tzinfo=posted.tzinfo)
        elif posted.tzinfo is None and clock.tzinfo is not None:
            posted = posted.replace(tzinfo=clock.tzinfo)
        if posted < clock - timedelta(days=stale_days):
            return JobQualityStatus.STALE
        if status in (None, _URL_ACTIVE, _URL_UNKNOWN):
            return JobQualityStatus.ACTIVE

    if status == _URL_ACTIVE:
        return JobQualityStatus.ACTIVE

    return JobQualityStatus.UNKNOWN


def quality_label(status: JobQualityStatus) -> str:
    """Human-readable quality label for UI."""
    labels = {
        JobQualityStatus.ACTIVE: "Active",
        JobQualityStatus.STALE: "Stale",
        JobQualityStatus.EXPIRED: "Expired",
        JobQualityStatus.BROKEN: "Broken URL",
        JobQualityStatus.UNKNOWN: "Unknown",
    }
    return labels.get(status, "Unknown")
