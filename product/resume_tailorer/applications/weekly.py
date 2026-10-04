"""Weekly application counts for the Tracker gauge."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable, Optional

from resume_tailorer.applications.models import ApplicationStatus

_NOT_SUBMITTED = {
    ApplicationStatus.DISCOVERED,
    ApplicationStatus.INTERESTED,
    ApplicationStatus.PREPARING,
    ApplicationStatus.READY_TO_APPLY,
    ApplicationStatus.WITHDRAWN,
    ApplicationStatus.UNKNOWN,
}
_INTERVIEW = {
    ApplicationStatus.RECRUITER_SCREEN,
    ApplicationStatus.INTERVIEW,
    ApplicationStatus.FINAL_INTERVIEW,
}


@dataclass(frozen=True)
class WeeklySummary:
    week_start: date
    week_end: date
    applied: int
    interviews: int  # applications currently in an interview stage, any week
    saved: int


def week_bounds(today: date) -> tuple[date, date]:
    start = today - timedelta(days=today.weekday())
    return start, start + timedelta(days=6)


def build_weekly_summary(
    entries: Iterable[tuple[ApplicationStatus, Optional[date]]], today: date
) -> WeeklySummary:
    """entries: (current status, date the application was submitted or None)."""
    start, end = week_bounds(today)
    applied = interviews = saved = 0
    for status, submitted in entries:
        in_week = submitted is not None and start <= submitted <= end
        if status in {ApplicationStatus.DISCOVERED, ApplicationStatus.INTERESTED} and submitted is None:
            saved += 1
        if status not in _NOT_SUBMITTED and in_week:
            applied += 1
        if status in _INTERVIEW:
            interviews += 1
    return WeeklySummary(start, end, applied, interviews, saved)
