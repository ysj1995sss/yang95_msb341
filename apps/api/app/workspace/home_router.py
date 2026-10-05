"""Home (spec 009 phase 1): the same decisions as the Streamlit Home (ui/home_state.py)."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends

from app.workspace.context import Workspace, jsonable, route_for, stamp, workspace

router = APIRouter(prefix="/v2", tags=["workspace"])

_CLOSED_STATUSES = {"offer", "rejected", "withdrawn"}


@router.get("/me")
def me(ws: Workspace = Depends(workspace)):
    return {"name": ws.owner.name, "signed_in": ws.owner.signed_in, "mode": "google" if ws.owner.signed_in else "local"}


def _with_routes(items):
    return [dict(item, page=route_for(item.get("page", ""))) for item in items]


@router.get("/home")
def home(ws: Workspace = Depends(workspace)):
    from resume_tailorer.applications.models import ApplicationStatus
    from resume_tailorer.applications.status_tracker import StatusTracker
    from resume_tailorer.applications.weekly import build_weekly_summary
    from resume_tailorer.job_search.job_service import PENDING_TAILOR_JOB_KEY
    from resume_tailorer.review_store import load_review
    from resume_tailorer.tailoring_session import handoff_for_job
    from resume_tailorer.ui.home_state import (
        APPLY_PAGE, JOBS_PAGE, TAILOR_PAGE, HomeInputs, Item, build_home_view, due_items,
    )
    from resume_tailorer.ui.profile_readiness import build_readiness
    from resume_tailorer.ui.tracker_views import build_row as tracker_row

    ws.service.warm_up()  # job boards start downloading while the user reads Home
    record = ws.record
    service = ws.service
    apps_db = service.applications_db
    trackers = apps_db.get_all_applications()
    submissions = {t.application_id: apps_db.get_submission(t.application_id) for t in trackers}

    pending = ws.session.get(PENDING_TAILOR_JOB_KEY) or {}
    active = Item(pending["title"], pending.get("company", ""), TAILOR_PAGE) if pending.get("title") else None
    if active is None:
        earlier = service.db.get_jobs_by_latest_action("apply", limit=1)
        if earlier:
            active = Item(earlier[0].title, earlier[0].company, TAILOR_PAGE)
    review = load_review(ws.session["artifacts_dir"], pending.get("job_id")) if pending else None
    report = (review or {}).get("report")
    handoff = handoff_for_job(ws.session, pending.get("job_id", "")) if pending else None

    status_tracker = StatusTracker(apps_db)
    rows = [tracker_row(t, submissions.get(t.application_id), status_tracker.get_status_history(t.application_id))
            for t in trackers]
    followup_rows = [
        {"title": r.role, "company": r.company, "next_action": r.next_action,
         "due": r.due.isoformat() if r.due else "", "closed": r.status.value in _CLOSED_STATUSES}
        for r in rows
    ]
    last_seen = service.db.latest_seen()
    week_start = date.today() - timedelta(days=date.today().weekday())
    inputs = HomeInputs(
        readiness=build_readiness(record),
        goals_set=bool((record.get("preferences") or {}).get("job_title")),
        role_chosen=bool(pending) or bool(service.db.get_jobs_by_latest_action("apply", limit=1)) or bool(trackers),
        application_prepared=bool(trackers),
        active_job=active,
        artifact_status=report.validation.status.value if report else None,
        artifact_reviewed=bool((review or {}).get("reviewed")) and not (review or {}).get("dirty"),
        handoff_ready=bool(handoff),
        saved_jobs=tuple(Item(f"{j.title} at {j.company}", j.location or "", JOBS_PAGE)
                         for j in service.db.get_jobs_by_latest_action("save", limit=10)),
        ready_to_finish=tuple(Item(f"{r.role} at {r.company}", "Tracked; finish on the employer's site", APPLY_PAGE)
                              for r in rows if r.status == ApplicationStatus.READY_TO_APPLY),
        followups_due=due_items(followup_rows, date.today()),
        searched_this_week=bool(last_seen and last_seen.date() >= week_start),
    )
    view = jsonable(build_home_view(inputs))
    view["next_action"]["page"] = route_for(view["next_action"]["page"])
    for key in ("drafts", "saved_jobs", "ready_to_finish", "followups_due"):
        view[key] = _with_routes(view[key])
    weekly = build_weekly_summary([(r.status, r.applied) for r in rows], date.today())
    recent = [
        {"date": stamp(r.last_update), "role": r.role, "company": r.company,
         "status": r.status.value.replace("_", " ")}
        for r in sorted(rows, key=lambda r: r.last_update, reverse=True)[:5]
    ]
    contact = (record.get("profile") or {}).get("contact_info") or {}
    return {
        "view": view,
        "weekly": jsonable(weekly),
        "recent": recent,
        "first_name": (contact.get("name") or "").split(" ")[0],
        "weekly_goal": int((record.get("preferences") or {}).get("weekly_goal") or 0),
    }
