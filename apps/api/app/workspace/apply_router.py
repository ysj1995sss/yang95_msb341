"""Apply (spec 009 phase 4): readiness, the application kit and helper code, track and mark
as applied. Same rules as the Streamlit Apply page (ui/apply_readiness.py,
ui/application_kit.py). Nothing is ever submitted to an employer from here."""

from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app.workspace.context import Workspace, jsonable, route_for, workspace

router = APIRouter(prefix="/v2", tags=["workspace"])


def _pending(ws: Workspace) -> dict:
    from resume_tailorer.job_search.job_service import PENDING_TAILOR_JOB_KEY

    return ws.session.get(PENDING_TAILOR_JOB_KEY) or {}


def _handoff(ws: Workspace, job_id: str) -> Optional[dict]:
    from resume_tailorer.tailoring_session import handoff_for_job

    handoff = handoff_for_job(ws.session, job_id)
    if handoff and str(handoff.get("validation_status", "")).upper() == "FAIL":
        return None  # a failed resume is never usable here
    return handoff


def _review_complete(ws: Workspace, job_id: str, handoff: Optional[dict]) -> bool:
    from resume_tailorer.review_store import load_review
    from resume_tailorer.ui.artifact_review import visible_changes
    from resume_tailorer.ui.tailor_progress import review_progress
    from resume_tailorer.ui.tailoring_view import group_changes

    state = load_review(ws.session["artifacts_dir"], job_id)
    if not state:
        return bool((handoff or {}).get("review_complete"))
    report = state["report"]
    reviewable = group_changes(visible_changes(state["changes"]), report.true_gaps).reviewable
    return review_progress(reviewable, state.get("decided", set()), state.get("dirty", False),
                           report.validation.status).can_continue


def _current_application(ws: Workspace, job_id: str):
    subs = ws.service.applications_db.get_submissions_by_job(job_id) if job_id else []
    if not subs:
        return None, None
    latest = sorted(subs, key=lambda s: s.submission_timestamp)[-1]
    return latest, ws.service.applications_db.get_current_status(latest.application_id)


def _score(handoff: Optional[dict]) -> float:
    score = (handoff or {}).get("resume_match_score")
    return min(float(score) * 100, 100.0) if isinstance(score, (int, float)) else 0.0


@router.get("/apply")
def apply_page(ws: Workspace = Depends(workspace)):
    from resume_tailorer.applications.capabilities import get_capability
    from resume_tailorer.applications.models import ApplicationStatus
    from resume_tailorer.applications.status_tracker import StatusTracker
    from resume_tailorer.session_profile import get_career_profile
    from resume_tailorer.ui.application_kit import build_kit, helper_payload, kit_summary
    from resume_tailorer.ui.apply_readiness import build_apply_view, empty_apply_view
    from resume_tailorer.ui.profile_readiness import build_readiness

    job = dict(_pending(ws))
    if not job:
        staged = []
        for t in StatusTracker(ws.service.applications_db).get_all_applications():
            if t.status == ApplicationStatus.READY_TO_APPLY:
                sub = ws.service.applications_db.get_submission(t.application_id)
                snap = (sub.job_snapshot or {}) if sub else {}
                staged.append({"job_id": t.job_posting_id, "title": snap.get("title", "Role"), "company": snap.get("company", "")})
        empty = empty_apply_view(False, False)
        return {"job": None, "empty": {"items": [{"label": l, "done": d} for l, d in empty.items],
                                       "action_label": empty.action_label, "action_page": route_for(empty.action_page)},
                "staged": staged}

    job_id = job.get("job_id", "")
    handoff = _handoff(ws, job_id)
    stored = ws.service.db.get_job_posting(job_id) if job_id else None
    if not job.get("url") and stored is not None:
        job["url"] = stored.url
    record = ws.record
    readiness = build_readiness(record)
    profile = get_career_profile(ws.session)
    application, status = _current_application(ws, job_id)
    capability = get_capability((stored.ats_platform if stored else "") or "")
    answers = ws.service.applications_db.get_answer_entries()
    view = build_apply_view(
        job=job, handoff=handoff, review_complete=_review_complete(ws, job_id, handoff),
        facts_confirmed=readiness.facts_confirmed, has_profile=profile is not None,
        approved_answers=len(answers), unanswered=(), status=status, capability=capability,
    )
    kit = build_kit(record, handoff, answers)
    return {
        "job": {"job_id": job_id, "title": job.get("title", "Role"), "company": job.get("company", ""), "url": job.get("url", "")},
        "view": jsonable(view),
        "handoff": {"version": handoff.get("version"), "has_file": bool(handoff.get("pdf_path") and os.path.exists(handoff["pdf_path"]))}
        if handoff else None,
        "application_id": application.application_id if application else None,
        "kit": jsonable(kit),
        "kit_summary": kit_summary(kit),
        "helper_code": _helper_code(kit, handoff),
    }


def _helper_code(kit, handoff: Optional[dict]) -> str:
    """The browser helper's code, with the tailored PDF inside so it can attach it (decision 030)."""
    import base64
    import json

    from resume_tailorer.ui.application_kit import helper_payload

    code = json.loads(helper_payload(kit))
    path = (handoff or {}).get("pdf_path") or ""
    if path and os.path.exists(path):
        with open(path, "rb") as f:
            code["resume"] = {"filename": f"tailored_resume_v{handoff.get('version', 1)}.pdf",
                              "data": base64.b64encode(f.read()).decode("ascii")}
    return json.dumps(code, ensure_ascii=False)


class Select(BaseModel):
    job_id: str


@router.post("/apply/select")
def select_staged(body: Select, ws: Workspace = Depends(workspace)):
    from resume_tailorer.active_job import remember

    if ws.service.db.get_job_posting(body.job_id) is None:
        raise HTTPException(404, "That job is no longer stored.")
    record = ws.record
    remember(record, body.job_id)
    ws.save_record(record)
    return apply_page(Workspace(ws.owner))


@router.post("/apply/track")
def track(ws: Workspace = Depends(workspace)):
    from resume_tailorer.applications.models import ApplicationMode
    from resume_tailorer.session_profile import get_career_profile

    job_id = _pending(ws).get("job_id", "")
    handoff = _handoff(ws, job_id)
    profile = get_career_profile(ws.session)
    if not handoff or profile is None:
        raise HTTPException(409, "Tailor a resume for this job first.")
    if _current_application(ws, job_id)[1] is not None:
        raise HTTPException(409, "This application is already tracked.")
    try:
        # The dry run is the preview: nothing is saved by it.
        ws.service.apply_for_job(job_id=job_id, profile=profile, resume_pdf_path=handoff["pdf_path"],
                                 mode=ApplicationMode.MANUAL, resume_match_score=_score(handoff), dry_run=True)
        ws.service.apply_for_job(job_id=job_id, profile=profile, resume_pdf_path=handoff["pdf_path"],
                                 mode=ApplicationMode.MANUAL, resume_match_score=_score(handoff), dry_run=False)
    except ValueError as exc:
        raise HTTPException(400, f"Couldn't track this application: {exc}") from exc
    return apply_page(ws)


@router.post("/apply/applied")
def mark_applied(ws: Workspace = Depends(workspace)):
    from resume_tailorer.applications.models import ApplicationStatus, StatusSource
    from resume_tailorer.applications.status_tracker import StatusTracker

    application, status = _current_application(ws, _pending(ws).get("job_id", ""))
    if application is None or status != ApplicationStatus.READY_TO_APPLY:
        raise HTTPException(409, "Track the application first, then mark it as applied after you submit.")
    StatusTracker(ws.service.applications_db).update_status(
        application.application_id, ApplicationStatus.APPLIED,
        "Marked as applied by you after finishing on the employer's site.", source=StatusSource.USER,
    )
    return apply_page(ws)


@router.post("/apply/questions")
def check_questions(ws: Workspace = Depends(workspace)):
    from resume_tailorer.applications.models import ApplicationMode
    from resume_tailorer.session_profile import get_career_profile

    job_id = _pending(ws).get("job_id", "")
    handoff = _handoff(ws, job_id) or {}
    try:
        result = ws.service.apply_for_job(job_id=job_id, profile=get_career_profile(ws.session),
                                          resume_pdf_path=handoff.get("pdf_path", ""), mode=ApplicationMode.ASSIST,
                                          resume_match_score=0.0, dry_run=True)
    except ValueError:
        return {"readable": False, "unanswered": [], "used": {}}
    return {"readable": True, "unanswered": list(dict.fromkeys(result.unanswered_questions)),
            "used": dict(result.custom_answers or {})}


@router.get("/apply/resume")
def tailored_resume(ws: Workspace = Depends(workspace)):
    handoff = _handoff(ws, _pending(ws).get("job_id", ""))
    if not handoff or not os.path.exists(handoff.get("pdf_path", "")):
        raise HTTPException(404, "There's no tailored resume file for this job.")
    with open(handoff["pdf_path"], "rb") as f:
        data = f.read()
    return Response(data, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="tailored_resume_v{handoff.get("version", 1)}.pdf"'})
