import json
import os
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db import get_db
from app.models import Profile, ResumeFile, User
from app.schemas.profile import CareerTruthProfileOut

from resume_tailorer.parsers import ResumeParser

router = APIRouter(prefix="/profile", tags=["profile"])

_SUPPORTED_SUFFIXES = (".pdf", ".docx")
_CONTENT_TYPES = {".pdf": "application/pdf", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}


@router.post("/upload", response_model=CareerTruthProfileOut)
async def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    filename = file.filename or "resume.pdf"
    suffix = os.path.splitext(filename)[1].lower()
    if suffix not in _SUPPORTED_SUFFIXES:
        raise HTTPException(status_code=400, detail="Only PDF or DOCX supported")

    raw = await file.read()
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
        # ResumeParser extracts real structure (education, work experience,
        # skills, tools, certifications) -- not just name + email.
        profile = ResumeParser().parse(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    row = db.get(Profile, user.id) or Profile(user_id=user.id)
    row.data_json = json.dumps(profile.to_dict())
    db.add(row)

    # Spec 001 item 1: "Original resume is preserved and never overwritten."
    # The raw bytes -- not just the parsed structure -- are what's preserved
    # here; re-uploading a new resume replaces the stored file for this user
    # (one current resume per user, not version history).
    file_row = db.get(ResumeFile, user.id) or ResumeFile(user_id=user.id)
    file_row.filename = filename
    file_row.content_type = _CONTENT_TYPES.get(suffix, "application/octet-stream")
    file_row.data = raw
    db.add(file_row)

    db.commit()
    return profile.to_dict()


@router.get("/original")
def get_original_resume(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(ResumeFile, user.id)
    if not row:
        raise HTTPException(status_code=404, detail="No original resume file stored for this user")
    return Response(
        content=row.data,
        media_type=row.content_type,
        headers={"Content-Disposition": f'attachment; filename="{row.filename}"'},
    )


@router.get("", response_model=CareerTruthProfileOut)
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(Profile, user.id)
    if not row:
        return CareerTruthProfileOut()
    return json.loads(row.data_json)


@router.put("", response_model=CareerTruthProfileOut)
def put_profile(
    body: CareerTruthProfileOut,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.get(Profile, user.id) or Profile(user_id=user.id)
    row.data_json = body.model_dump_json()
    db.add(row)
    db.commit()
    return body
