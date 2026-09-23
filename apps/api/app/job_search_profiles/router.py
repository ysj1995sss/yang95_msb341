import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db import get_db
from app.models import JobSearchProfile, User
from app.schemas.job_search_profile import JobSearchGoals, JobSearchProfileIn, JobSearchProfileOut

router = APIRouter(prefix="/job-search-profiles", tags=["job-search-profiles"])


def _to_out(row: JobSearchProfile) -> JobSearchProfileOut:
    return JobSearchProfileOut(
        id=row.id,
        name=row.name,
        status=row.status,
        goals=JobSearchGoals.model_validate_json(row.data_json),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _get_owned_or_404(db: Session, user: User, profile_id: str) -> JobSearchProfile:
    row = db.get(JobSearchProfile, profile_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job search profile not found")
    return row


@router.get("", response_model=list[JobSearchProfileOut])
def list_job_search_profiles(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(JobSearchProfile)
        .filter(JobSearchProfile.user_id == user.id)
        .order_by(JobSearchProfile.created_at)
        .all()
    )
    return [_to_out(row) for row in rows]


@router.post("", response_model=JobSearchProfileOut, status_code=201)
def create_job_search_profile(
    body: JobSearchProfileIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    row = JobSearchProfile(user_id=user.id, name=body.name, data_json=body.goals.model_dump_json())
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.get("/{profile_id}", response_model=JobSearchProfileOut)
def get_job_search_profile(
    profile_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return _to_out(_get_owned_or_404(db, user, profile_id))


@router.put("/{profile_id}", response_model=JobSearchProfileOut)
def update_job_search_profile(
    profile_id: str,
    body: JobSearchProfileIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = _get_owned_or_404(db, user, profile_id)
    row.name = body.name
    row.data_json = body.goals.model_dump_json()
    row.updated_at = datetime.utcnow()
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.delete("/{profile_id}", status_code=204)
def delete_job_search_profile(
    profile_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    row = _get_owned_or_404(db, user, profile_id)
    db.delete(row)
    db.commit()


@router.post("/{profile_id}/pause", response_model=JobSearchProfileOut)
def pause_job_search_profile(
    profile_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    row = _get_owned_or_404(db, user, profile_id)
    row.status = "paused"
    row.updated_at = datetime.utcnow()
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.post("/{profile_id}/activate", response_model=JobSearchProfileOut)
def activate_job_search_profile(
    profile_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    row = _get_owned_or_404(db, user, profile_id)
    row.status = "active"
    row.updated_at = datetime.utcnow()
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.post("/{profile_id}/duplicate", response_model=JobSearchProfileOut, status_code=201)
def duplicate_job_search_profile(
    profile_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    source = _get_owned_or_404(db, user, profile_id)
    copy = JobSearchProfile(
        user_id=user.id,
        name=f"{source.name} (copy)",
        data_json=source.data_json,
        status="active",
    )
    db.add(copy)
    db.commit()
    db.refresh(copy)
    return _to_out(copy)
