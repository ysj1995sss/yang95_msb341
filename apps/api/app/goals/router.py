from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db import get_db
from app.models import Goals, User
from app.schemas.goals import JobGoals

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("", response_model=JobGoals)
def get_goals(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(Goals, user.id)
    if not row:
        return JobGoals()
    return JobGoals.model_validate_json(row.data_json)


@router.put("", response_model=JobGoals)
def put_goals(
    body: JobGoals,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.get(Goals, user.id) or Goals(user_id=user.id)
    row.data_json = body.model_dump_json()
    db.add(row)
    db.commit()
    return body
