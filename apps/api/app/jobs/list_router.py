import json

from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db import get_db
from app.jobs.ranking import is_excluded_by_goals
from app.models import Goals, Job, User, UserJob
from app.schemas.job import JobListItem, JobStateIn, JobStateOut
from resume_tailorer.job_search.models import (
    canonicalize_triage_action,
    triage_storage_value,
)


def _goals_for_user(db: Session, user_id: str) -> dict:
    row = db.get(Goals, user_id)
    if not row:
        return {}
    return json.loads(row.data_json)


def _canonical_state(raw: str | None) -> str:
    return triage_storage_value(canonicalize_triage_action(raw))


def _to_list_item(user_job: UserJob, job: Job) -> JobListItem:
    data = json.loads(job.data_json)
    breakdown = None
    if user_job.fit_breakdown_json:
        try:
            parsed = json.loads(user_job.fit_breakdown_json)
            if isinstance(parsed, dict) and parsed:
                breakdown = parsed
        except json.JSONDecodeError:
            breakdown = None
    return JobListItem(
        job_id=job.id,
        user_job_id=user_job.id,
        state=_canonical_state(user_job.state),
        fit_score=user_job.fit_score,
        company=data.get("company") or "",
        title=data.get("title") or "",
        location=data.get("location") or "",
        description=data.get("description") or "",
        work_mode=data.get("work_mode"),
        salary=data.get("salary"),
        posted_at=data.get("posted_at"),
        deadline=data.get("deadline"),
        employment_type=data.get("employment_type"),
        sponsorship=data.get("sponsorship"),
        source=data.get("source"),
        original_url=data.get("original_url") or "",
        ats_platform=data.get("ats_platform"),
        discovered_at=data.get("discovered_at") or "",
        external_ids=data.get("external_ids") or {},
        fit_breakdown=breakdown,
    )


def list_jobs(
    state: str | None = Query(None),
    min_fit: float | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    goals = _goals_for_user(db, user.id)
    rows = (
        db.query(UserJob, Job)
        .join(Job, UserJob.job_id == Job.id)
        .filter(UserJob.user_id == user.id)
        .order_by(UserJob.fit_score.desc().nullslast(), Job.created_at.desc())
        .all()
    )

    wanted = canonicalize_triage_action(state) if state is not None else None

    items: list[JobListItem] = []
    for user_job, job in rows:
        data = json.loads(job.data_json)
        if is_excluded_by_goals(data, goals):
            continue
        if wanted is not None:
            current = canonicalize_triage_action(user_job.state)
            if current != wanted:
                continue
        if min_fit is not None:
            score = user_job.fit_score
            if score is None or score < min_fit:
                continue
        items.append(_to_list_item(user_job, job))
    return items


def transition_job_state(
    job_id: str,
    body: JobStateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_job = (
        db.query(UserJob)
        .filter(UserJob.user_id == user.id, UserJob.job_id == job_id)
        .one_or_none()
    )
    if user_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    canonical = triage_storage_value(canonicalize_triage_action(body.state))
    user_job.state = canonical
    db.commit()
    db.refresh(user_job)
    return JobStateOut(job_id=job_id, state=canonical)
