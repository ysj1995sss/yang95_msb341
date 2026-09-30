import json
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user_access_or_device
from app.db import get_db
from app.fit.scoring import score_candidate_fit
from app.jobs.dedupe import dedupe_key, legacy_dedupe_key
from app.jobs.normalize import normalize_job_payload
from app.jobs.ranking import apply_goals_rank_boost
from app.models import Goals, Job, Profile, User, UserJob
from app.jobs.list_router import list_jobs, transition_job_state
from app.schemas.job import JobListItem, JobStateOut, JobUpsertIn, JobUpsertOut

router = APIRouter(prefix="/jobs", tags=["jobs"])

router.get("", response_model=list[JobListItem])(list_jobs)
router.post("/{job_id}/state", response_model=JobStateOut)(transition_job_state)


@router.post("/upsert", response_model=JobUpsertOut)
def upsert_job(
    body: JobUpsertIn,
    user: User = Depends(get_current_user_access_or_device),
    db: Session = Depends(get_db),
):
    normalized = normalize_job_payload(body.model_dump())
    key = dedupe_key(normalized)
    data_json = json.dumps(normalized)

    job = db.query(Job).filter(Job.dedupe_key == key).one_or_none()
    legacy_key = legacy_dedupe_key(normalized) if job is None else None
    if legacy_key:
        job = db.query(Job).filter(Job.dedupe_key == legacy_key).one_or_none()
        if job is not None:
            job.dedupe_key = key
    job_created = job is None
    if job is None:
        job = Job(dedupe_key=key, data_json=data_json)
        db.add(job)
        db.flush()
    else:
        job.data_json = data_json

    user_job = (
        db.query(UserJob)
        .filter(UserJob.user_id == user.id, UserJob.job_id == job.id)
        .one_or_none()
    )
    user_job_created = user_job is None
    if user_job is None:
        user_job = UserJob(user_id=user.id, job_id=job.id, state="discovered")
        db.add(user_job)

    profile_row = db.get(Profile, user.id)
    goals_row = db.get(Goals, user.id)
    profile = json.loads(profile_row.data_json) if profile_row else {}
    goals = json.loads(goals_row.data_json) if goals_row else {}

    fit = score_candidate_fit(profile, normalized)
    user_job.fit_score = (
        None if fit["score"] is None
        else apply_goals_rank_boost(float(fit["score"]), normalized, goals)
    )
    user_job.fit_breakdown_json = json.dumps(fit["breakdown"])
    user_job.last_scored_at = datetime.utcnow()

    db.commit()
    db.refresh(job)
    db.refresh(user_job)

    return JobUpsertOut(
        job_id=job.id,
        user_job_id=user_job.id,
        created=job_created or user_job_created,
    )
