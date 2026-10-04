"""Tracker: dense rows and the six saved views (spec 007). Pure."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from resume_tailorer.applications.models import ApplicationStatus, ApplicationSubmission, ApplicationTracker

WAITING_DAYS = 14

INTERVIEWING = {
    ApplicationStatus.RECRUITER_SCREEN, ApplicationStatus.INTERVIEW,
    ApplicationStatus.FINAL_INTERVIEW, ApplicationStatus.ASSESSMENT,
}
CLOSED = {ApplicationStatus.OFFER, ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN}

VIEWS = ("All", "Needs action", "Ready to apply", "Applied", "Interviewing", "Waiting", "Closed")

STATUS_WORDS = {
    ApplicationStatus.DISCOVERED: "Discovered",
    ApplicationStatus.INTERESTED: "Interested",
    ApplicationStatus.PREPARING: "Preparing",
    ApplicationStatus.READY_TO_APPLY: "Ready to apply",
    ApplicationStatus.APPLIED: "Applied",
    ApplicationStatus.ASSESSMENT: "Assessment",
    ApplicationStatus.RECRUITER_SCREEN: "Recruiter screen",
    ApplicationStatus.INTERVIEW: "Interview",
    ApplicationStatus.FINAL_INTERVIEW: "Final interview",
    ApplicationStatus.OFFER: "Offer",
    ApplicationStatus.REJECTED: "Rejected",
    ApplicationStatus.WITHDRAWN: "Withdrawn",
    ApplicationStatus.UNKNOWN: "Unknown",
}


@dataclass(frozen=True)
class TrackerRow:
    application_id: str
    company: str
    role: str
    status: ApplicationStatus
    applied: Optional[date]
    next_action: str
    due: Optional[date]
    fit: str
    resume_version: str
    source: str
    mode: str
    last_update: datetime
    url: str

    def as_table(self) -> dict:
        return {
            "Company": self.company,
            "Role": self.role,
            "Status": STATUS_WORDS.get(self.status, self.status.value),
            "Applied": self.applied.isoformat() if self.applied else "Not yet",
            "Next action": self.next_action or "None set",
            "Due": self.due.isoformat() if self.due else "",
            "Candidate fit": self.fit,
            "Resume": self.resume_version,
            "Source": self.source,
            "Mode": self.mode,
        }


def _resume_label(path: str) -> str:
    """Tailored files are named by content hash; show that plainly and briefly."""
    if not path:
        return "Not recorded"
    name = os.path.basename(path)
    stem, ext = os.path.splitext(name)
    if len(stem) == 16 and all(ch in "0123456789abcdef" for ch in stem.lower()):
        return f"Tailored resume ({stem[:8]})"
    return name


def _parse_due(value: Optional[str]) -> Optional[date]:
    try:
        return date.fromisoformat(str(value)[:10]) if value else None
    except ValueError:
        return None


def applied_date(history: list[ApplicationTracker]) -> Optional[date]:
    """When the user first marked it applied (or a later stage), from status history."""
    for event in sorted(history, key=lambda e: e.status_updated):
        if event.status not in {ApplicationStatus.DISCOVERED, ApplicationStatus.INTERESTED,
                                ApplicationStatus.PREPARING, ApplicationStatus.READY_TO_APPLY,
                                ApplicationStatus.UNKNOWN}:
            return event.status_updated.date()
    return None


def build_row(tracker: ApplicationTracker, submission: Optional[ApplicationSubmission],
              history: list[ApplicationTracker]) -> TrackerRow:
    job = (submission.job_snapshot if submission else {}) or {}
    fit = (submission.candidate_fit_snapshot if submission else {}) or {}
    overall = fit.get("overall_fit")
    resume = _resume_label(submission.resume_used if submission else "")
    source = (tracker.job_posting_id.split("_", 1)[0] or "").title() if tracker.job_posting_id else "Not recorded"
    return TrackerRow(
        application_id=tracker.application_id,
        company=job.get("company") or "Company not recorded",
        role=job.get("title") or "Role not recorded",
        status=tracker.status,
        applied=applied_date(history),
        next_action=(submission.next_action if submission else "") or "",
        due=_parse_due(submission.next_action_due if submission else None),
        fit=f"{overall:.0f}%" if isinstance(overall, (int, float)) else "Not assessed",
        resume_version=resume,
        source=source,
        mode=submission.mode.value.title() if submission else "Not recorded",
        last_update=tracker.status_updated,
        url=(job.get("url") or (submission.form_url if submission else "")) or "",
    )


def in_view(row: TrackerRow, view: str, today: date) -> bool:
    if view == "All":
        return True
    if view == "Needs action":
        due_now = row.due is not None and row.due <= today and row.status not in CLOSED
        return due_now or row.status == ApplicationStatus.PREPARING
    if view == "Ready to apply":
        return row.status == ApplicationStatus.READY_TO_APPLY
    if view == "Applied":
        return row.status == ApplicationStatus.APPLIED
    if view == "Interviewing":
        return row.status in INTERVIEWING
    if view == "Waiting":
        return row.status == ApplicationStatus.APPLIED and (today - row.last_update.date()).days >= WAITING_DAYS
    if view == "Closed":
        return row.status in CLOSED
    return True


def view_counts(rows: list[TrackerRow], today: date) -> dict[str, int]:
    return {view: sum(in_view(r, view, today) for r in rows) for view in VIEWS}


def sort_rows(rows: list[TrackerRow]) -> list[TrackerRow]:
    """Due items first (soonest), then most recently updated."""
    return sorted(rows, key=lambda r: (r.due is None, r.due or date.max, -r.last_update.timestamp()))
