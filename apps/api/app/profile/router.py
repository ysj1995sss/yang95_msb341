import hashlib
import json
import os
import tempfile
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.db import get_db
from app.models import Profile, ResumeFile, ResumeFileVersion, User
from app.profile.verification import diff_user_edits
from app.schemas.profile import CareerTruthProfileOut
from app.schemas.resume_version import ResumeFileMetaOut, ResumeFileVersionOut

from resume_tailorer.parsers import ResumeParser

router = APIRouter(prefix="/profile", tags=["profile"])

_SUPPORTED_SUFFIXES = (".pdf", ".docx")
_CONTENT_TYPES = {".pdf": "application/pdf", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
# Generous ceiling, not a tuned production limit: catches an accidental
# wrong-file upload (a video, a zip) rather than a legitimate resume, which
# is never remotely this large.
_MAX_UPLOAD_BYTES = 10 * 1024 * 1024


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
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(raw) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({len(raw)} bytes); max {_MAX_UPLOAD_BYTES} bytes",
        )

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
    # A fresh upload replaces the source document entirely -- any prior
    # user_verified tags belonged to facts from the OLD resume and don't
    # carry semantic meaning against a newly parsed profile from a
    # different document. Everything from this parse is resume_verified by
    # construction (see app.profile.verification's module docstring).
    row.verification_json = "{}"
    db.add(row)

    # Spec 001 item 1: "Original resume is preserved and never overwritten."
    # The raw bytes -- not just the parsed structure -- are what's preserved
    # here. ResumeFile still holds only the one CURRENT resume per user (every
    # other reader of it is unchanged), but the row a re-upload replaces is
    # archived to ResumeFileVersion first, so history isn't silently lost.
    existing = db.get(ResumeFile, user.id)
    if existing is not None:
        db.add(
            ResumeFileVersion(
                user_id=user.id,
                filename=existing.filename,
                content_type=existing.content_type,
                data=existing.data,
                sha256=existing.sha256,
                size_bytes=existing.size_bytes,
                version=existing.version,
                uploaded_at=existing.uploaded_at,
            )
        )
    file_row = existing or ResumeFile(user_id=user.id)
    file_row.id = str(uuid.uuid4())
    file_row.filename = filename
    file_row.content_type = _CONTENT_TYPES.get(suffix, "application/octet-stream")
    file_row.data = raw
    file_row.sha256 = hashlib.sha256(raw).hexdigest()
    file_row.size_bytes = len(raw)
    file_row.version = (existing.version or 0 if existing else 0) + 1
    file_row.uploaded_at = datetime.utcnow()
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


@router.get("/resume-meta", response_model=ResumeFileMetaOut)
def get_resume_meta(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Metadata about the current resume file without downloading its
    bytes: stable id, hash, size, and version -- spec 001 item 1's
    "assign a stable resume ID/version" and "store ... size, ... hash/
    checksum, and version"."""
    row = db.get(ResumeFile, user.id)
    if not row:
        raise HTTPException(status_code=404, detail="No original resume file stored for this user")
    return ResumeFileMetaOut(
        id=row.id,
        filename=row.filename,
        content_type=row.content_type,
        size_bytes=row.size_bytes,
        sha256=row.sha256,
        version=row.version,
        uploaded_at=row.uploaded_at,
    )


@router.get("/resume-versions", response_model=list[ResumeFileVersionOut])
def list_resume_versions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Every resume a re-upload has ever superseded, newest first, plus the
    current one -- so a user (or a future UI) can see upload history and
    confirm nothing was silently lost on replacement."""
    versions = [
        ResumeFileVersionOut(
            id=v.id,
            filename=v.filename,
            content_type=v.content_type,
            size_bytes=v.size_bytes,
            sha256=v.sha256,
            version=v.version,
            uploaded_at=v.uploaded_at,
            archived_at=v.archived_at,
            is_current=False,
        )
        for v in db.query(ResumeFileVersion)
        .filter(ResumeFileVersion.user_id == user.id)
        .order_by(ResumeFileVersion.version.desc())
        .all()
    ]
    current = db.get(ResumeFile, user.id)
    if current is not None:
        versions.insert(
            0,
            ResumeFileVersionOut(
                id=current.id or "current",
                filename=current.filename,
                content_type=current.content_type,
                size_bytes=current.size_bytes,
                sha256=current.sha256,
                version=current.version,
                uploaded_at=current.uploaded_at,
                archived_at=current.uploaded_at,
                is_current=True,
            ),
        )
    return versions


@router.get("", response_model=CareerTruthProfileOut)
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(Profile, user.id)
    if not row:
        return CareerTruthProfileOut()
    return json.loads(row.data_json)


@router.get("/verification")
def get_profile_verification(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """{field_path: "resume_verified" | "user_verified"} for every fact the
    user has explicitly added/edited since the current resume was parsed.
    A field absent from this map is resume_verified by default -- see
    app.profile.verification's module docstring."""
    row = db.get(Profile, user.id)
    if not row or not row.verification_json:
        return {}
    return json.loads(row.verification_json)


@router.put("", response_model=CareerTruthProfileOut)
def put_profile(
    body: CareerTruthProfileOut,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.get(Profile, user.id) or Profile(user_id=user.id)
    old = json.loads(row.data_json) if row.data_json else {}
    new = body.model_dump()

    verification = json.loads(row.verification_json) if row.verification_json else {}
    verification.update(diff_user_edits(old, new))

    row.data_json = body.model_dump_json()
    row.verification_json = json.dumps(verification)
    row.updated_at = datetime.utcnow()
    db.add(row)
    db.commit()
    return body
