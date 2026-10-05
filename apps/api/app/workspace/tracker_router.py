"""Tracker (spec 009 phase 4): saved views, the immutable application record, next actions,
status changes, the weekly goal, and status from a pasted recruiter email (spec 005 slice 1:
suggested only; nothing changes until the user confirms). Same rules as the Streamlit Tracker."""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.workspace.context import Workspace, workspace

router = APIRouter(prefix="/v2", tags=["workspace"])

WHO = {"user": "you", "system": "Job Copilot", "email_integration": "you, from an email"}


def _rows(ws: Workspace):
    from resume_tailorer.applications.status_tracker import StatusTracker
    from resume_tailorer.ui.tracker_views import build_row

    tracker = StatusTracker(ws.service.applications_db)
    out = []
    for t in tracker.get_all_applications():
        sub = ws.service.applications_db.get_submission(t.application_id)
        out.append((build_row(t, sub, tracker.get_status_history(t.application_id)), sub))
    return out


def _row_json(row) -> dict:
    from resume_tailorer.ui.tracker_views import STATUS_WORDS

    return {
        "application_id": row.application_id, "company": row.company, "role": row.role,
        "status": row.status.value, "status_label": STATUS_WORDS.get(row.status, row.status.value),
        "applied": row.applied.isoformat() if row.applied else None, "next_action": row.next_action,
        "due": row.due.isoformat() if row.due else None, "fit": row.fit, "resume_version": row.resume_version,
        "source": row.source, "mode": row.mode, "last_update": row.last_update.isoformat(), "url": row.url,
    }


def _status_options():
    from resume_tailorer.applications.models import ApplicationStatus
    from resume_tailorer.ui.tracker_views import STATUS_WORDS

    return [{"value": s.value, "label": w} for s, w in STATUS_WORDS.items() if s is not ApplicationStatus.UNKNOWN]


@router.get("/tracker")
def tracker(view: Optional[str] = None, q: str = "", ws: Workspace = Depends(workspace)):
    from resume_tailorer.applications.weekly import build_weekly_summary
    from resume_tailorer.ui.tracker_views import LIFECYCLE, VIEWS, default_view, in_view, sort_rows, view_counts

    today = date.today()
    pairs = _rows(ws)
    rows = [r for r, _ in pairs]
    counts = view_counts(rows, today)
    chosen = view if view in VIEWS else default_view(counts)
    shown = [r for r in sort_rows(rows) if in_view(r, chosen, today)]
    needle = q.strip().lower()
    if needle:
        shown = [r for r in shown if needle in r.company.lower() or needle in r.role.lower()]
    week = build_weekly_summary([(r.status, r.applied) for r in rows], today)
    return {
        "total": len(rows),
        "views": [{"name": v, "count": counts[v]} for v in VIEWS],
        "view": chosen,
        "rows": [_row_json(r) for r in shown],
        "lifecycle": list(LIFECYCLE),
        "weekly": {"week_start": week.week_start.isoformat(), "applied": week.applied,
                   "interviews": week.interviews, "saved": week.saved},
        "weekly_goal": int((ws.record.get("preferences") or {}).get("weekly_goal") or 0),
        "status_options": _status_options(),
    }


def _find(ws: Workspace, application_id: str):
    for row, sub in _rows(ws):
        if row.application_id == application_id:
            return row, sub
    raise HTTPException(404, "That application isn't in your tracker.")


@router.get("/tracker/{application_id}")
def application_detail(application_id: str, ws: Workspace = Depends(workspace)):
    from resume_tailorer.applications.status_tracker import StatusTracker
    from resume_tailorer.ui.tracker_views import STATUS_WORDS

    row, sub = _find(ws, application_id)
    job = (sub.job_snapshot if sub else {}) or {}
    salary = "No salary stated"
    if job.get("salary_min") or job.get("salary_max"):
        salary = f"${(job.get('salary_min') or 0):,} – ${(job.get('salary_max') or 0):,}"
    history = StatusTracker(ws.service.applications_db).get_status_history(application_id)
    return {
        "row": _row_json(row),
        "facts": [
            {"label": "Status", "value": STATUS_WORDS.get(row.status, row.status.value)},
            {"label": "Applied", "value": row.applied.isoformat() if row.applied else "Not yet"},
            {"label": "Candidate fit when you applied", "value": row.fit},
            {"label": "Resume used", "value": row.resume_version},
            {"label": "Mode", "value": row.mode},
            {"label": "Location", "value": job.get("location") or "Not recorded"},
            {"label": "Salary", "value": salary},
            {"label": "Confirmation number", "value": (sub.confirmation_number if sub else "") or "None recorded"},
        ],
        "answers": [{"question": q, "answer": a} for q, a in ((sub.custom_answers if sub else {}) or {}).items()],
        "history": [
            {"when": e.status_updated.isoformat(), "status": STATUS_WORDS.get(e.status, e.status.value),
             "who": WHO.get(e.source.value, e.source.value.replace("_", " ")), "note": e.notes}
            # Newest first; entries made in the same instant keep the order they were made in.
            for _i, e in sorted(enumerate(history), key=lambda p: (p[1].status_updated, p[0]), reverse=True)
        ],
        "next_action": {"text": sub.next_action if sub else "", "due": (sub.next_action_due or "")[:10] if sub else "",
                        "notes": sub.next_action_notes if sub else ""},
        "job_id": sub.job_posting_id if sub else None,
        "status_options": _status_options(),
    }


class NextAction(BaseModel):
    text: str = ""
    due: Optional[str] = None
    notes: str = ""


@router.put("/tracker/{application_id}/next-action")
def save_next_action(application_id: str, body: NextAction, ws: Workspace = Depends(workspace)):
    _find(ws, application_id)
    due = None
    if body.due:
        try:
            due = date.fromisoformat(body.due[:10]).isoformat()
        except ValueError as exc:
            raise HTTPException(400, "Use a date like 2026-10-12.") from exc
    ws.service.applications_db.update_next_action(application_id, body.text.strip(), due, body.notes.strip())
    return application_detail(application_id, ws)


class StatusChange(BaseModel):
    status: str
    note: str = ""


@router.post("/tracker/{application_id}/status")
def change_status(application_id: str, body: StatusChange, ws: Workspace = Depends(workspace)):
    from resume_tailorer.applications.models import ApplicationStatus, StatusSource
    from resume_tailorer.applications.status_tracker import StatusTracker

    row, _ = _find(ws, application_id)
    try:
        status = ApplicationStatus(body.status)
    except ValueError as exc:
        raise HTTPException(400, "Unknown status.") from exc
    if status == row.status:
        raise HTTPException(400, "It already has that status.")
    StatusTracker(ws.service.applications_db).update_status(application_id, status, body.note.strip(), source=StatusSource.USER)
    return application_detail(application_id, ws)


@router.post("/tracker/{application_id}/retailor")
def tailor_again(application_id: str, ws: Workspace = Depends(workspace)):
    from resume_tailorer.active_job import remember

    _row, sub = _find(ws, application_id)
    if not sub or ws.service.db.get_job_posting(sub.job_posting_id) is None:
        raise HTTPException(404, "The original posting is no longer stored, so it can't be tailored again.")
    record = ws.record
    remember(record, sub.job_posting_id)
    ws.save_record(record)
    return {"next": "/tailor"}


class WeeklyGoal(BaseModel):
    goal: int


@router.put("/tracker/weekly-goal")
def weekly_goal(body: WeeklyGoal, ws: Workspace = Depends(workspace)):
    record = ws.record
    record.setdefault("preferences", {})["weekly_goal"] = max(0, min(100, body.goal))
    ws.save_record(record)
    return {"weekly_goal": record["preferences"]["weekly_goal"]}


class Email(BaseModel):
    text: str


@router.post("/tracker/email/read")
def read_email(body: Email, ws: Workspace = Depends(workspace)):
    from resume_tailorer.applications.email_status import Candidate, read_email as read
    from resume_tailorer.ui.tracker_views import STATUS_WORDS

    rows = [r for r, _ in _rows(ws)]
    reading = read(body.text, [Candidate(r.application_id, r.company, r.role, r.status) for r in rows])
    by_id = {r.application_id: r for r in rows}
    matched = [m.application_id for m in reading.matches]
    return {
        "status": reading.status.value if reading.status else None,
        "status_label": STATUS_WORDS.get(reading.status, "") if reading.status else "",
        "phrase": reading.phrase,
        "chosen": reading.chosen,
        "email_date": reading.email_date.isoformat() if reading.email_date else None,
        "subject": reading.subject,
        "options": [
            {"application_id": i, "label": f"{by_id[i].role} at {by_id[i].company}", "matched": i in matched,
             "backwards": reading.moves_backwards(by_id[i].status)}
            for i in matched + [i for i in by_id if i not in matched]
        ],
    }


class EmailConfirm(BaseModel):
    application_id: str
    status: str
    email_date: Optional[str] = None
    evidence: str = ""


@router.post("/tracker/email/confirm")
def confirm_email(body: EmailConfirm, ws: Workspace = Depends(workspace)):
    from resume_tailorer.applications.models import ApplicationStatus, StatusSource
    from resume_tailorer.applications.status_tracker import StatusTracker

    _find(ws, body.application_id)
    try:
        status = ApplicationStatus(body.status)
        when = date.fromisoformat(body.email_date[:10]) if body.email_date else date.today()
    except ValueError as exc:
        raise HTTPException(400, "Check the status and the email date.") from exc
    StatusTracker(ws.service.applications_db).update_status(
        body.application_id, status, notes=f"from a recruiter email dated {when:%b %d, %Y}",
        source=StatusSource.EMAIL_INTEGRATION, confidence="confirmed by you", evidence=body.evidence[:200],
    )
    return application_detail(body.application_id, ws)
