"""Evaluate job quality for API-stored job payloads (dict shape)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from resume_tailorer.job_search.job_quality import DEFAULT_STALE_DAYS
from resume_tailorer.job_search.models import JobQualityStatus

_UNKNOWN_SENTINELS = {"", "unknown", "n/a", "not specified", "none"}


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text or text.lower() in _UNKNOWN_SENTINELS:
        return None
    # Support trailing Z
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def evaluate_api_job_quality(
    data: dict,
    *,
    now: Optional[datetime] = None,
    stale_days: int = DEFAULT_STALE_DAYS,
    url_status: Optional[str] = None,
) -> JobQualityStatus:
    """Classify API job data_json for quality_status on list responses."""
    clock = now or datetime.now(timezone.utc)
    status = (url_status or "").strip().lower() or None

    if status == "closed":
        return JobQualityStatus.BROKEN

    deadline = _parse_dt(data.get("deadline"))
    if deadline is not None:
        if deadline.tzinfo is not None and clock.tzinfo is None:
            clock = clock.replace(tzinfo=deadline.tzinfo)
        elif deadline.tzinfo is None and clock.tzinfo is not None:
            deadline = deadline.replace(tzinfo=clock.tzinfo)
        if deadline < clock:
            return JobQualityStatus.EXPIRED

    posted = _parse_dt(data.get("posted_at"))
    if posted is not None:
        if posted.tzinfo is not None and clock.tzinfo is None:
            clock = clock.replace(tzinfo=posted.tzinfo)
        elif posted.tzinfo is None and clock.tzinfo is not None:
            posted = posted.replace(tzinfo=clock.tzinfo)
        if posted < clock - timedelta(days=stale_days):
            return JobQualityStatus.STALE
        if status in (None, "active", "unknown"):
            return JobQualityStatus.ACTIVE

    original_url = (data.get("original_url") or "").strip()
    if status == "active" or (original_url and status is None and posted is not None):
        return JobQualityStatus.ACTIVE

    return JobQualityStatus.UNKNOWN
