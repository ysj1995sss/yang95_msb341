import uuid
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Profile(Base):
    """Stores CareerTruthProfile.to_dict() JSON -- the resume_tailorer engine's
    own shape, not a separate API-layer schema, so no adapter is needed
    between storage and the tailoring pipeline."""

    __tablename__ = "profiles"
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), primary_key=True)
    data_json: Mapped[str] = mapped_column(Text, default="{}")
    # Sidecar tagging of which top-level facts (contact fields, skills,
    # tools, certifications, each work-experience bullet/job, each
    # education entry) were explicitly added/edited by the user via PUT
    # /profile, as opposed to originally parsed from the uploaded resume.
    # Keyed by a stable path string (e.g. "skills[3]", "work_experience[0].
    # accomplishments[1]"); a fact absent from this map is "resume_verified"
    # by default -- everything the parser extracts is literal resume text,
    # never an LLM inference, so it's true-by-construction unless a user
    # edit says otherwise. See app.profile.verification for the diffing
    # logic that maintains this map.
    verification_json: Mapped[str] = mapped_column(Text, default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ResumeFile(Base):
    """The CURRENT original uploaded resume file, byte-for-byte. Spec 001
    item 1: "Original resume is preserved and never overwritten" -- Profile
    only stores the *parsed* structured data; the raw bytes live here so
    the original can be re-downloaded and so PDF generation can extract
    style hints (bullet character, heading style) from the source
    formatting. Re-uploading replaces this row, but the row it replaces is
    archived to ResumeFileVersion first (see profile/router.py) -- this
    table itself still holds only the one current resume per user, keeping
    every other reader of ResumeFile (tailor/router.py, etc.) unchanged."""

    __tablename__ = "resume_files"
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), primary_key=True)
    # Stable identifier for this specific upload, distinct from user_id (the
    # row's own PK) -- regenerated on every upload so a version has a durable
    # id even after a later upload moves it into ResumeFileVersion.
    id: Mapped[str | None] = mapped_column(String(36), unique=True, index=True, nullable=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    data: Mapped[bytes] = mapped_column(LargeBinary)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 1 on first upload, incremented on every re-upload for this user.
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ResumeFileVersion(Base):
    """Archive of a resume file a later upload superseded -- written just
    before ResumeFile is overwritten, so re-uploading a new resume never
    silently loses the previous one. Not read by any tailoring/parsing
    code path; exists purely so GET /profile/versions can list history and
    GET /profile/versions/{id} can retrieve an old file's bytes."""

    __tablename__ = "resume_file_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    data: Mapped[bytes] = mapped_column(LargeBinary)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    version: Mapped[int] = mapped_column(Integer)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime)
    archived_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Goals(Base):
    __tablename__ = "goals"
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), primary_key=True)
    data_json: Mapped[str] = mapped_column(Text, default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class JobSearchProfile(Base):
    """A named, saveable, reusable job-search preference set -- distinct
    from the single-row `Goals` table (kept as-is for backward
    compatibility with jobs/ranking.py's exclude-company filtering), which
    structurally cannot support more than one profile per user (user_id is
    its primary key). A user can have several of these at once (e.g.
    "Marketing - Dallas", "Strategy - Nationwide"), each independently
    pausable/editable/deletable. `data_json` reuses the same field shape as
    app.schemas.goals.JobGoals (titles, industries, locations, etc.),
    extended with the additional fields the product spec calls for that
    JobGoals doesn't have (target_functions, work_arrangements,
    relocation_preference, preferred_salary, employment_types,
    keywords_include/exclude) -- see app.schemas.job_search_profile."""

    __tablename__ = "job_search_profiles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    data_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(16), default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    dedupe_key: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    data_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DeviceToken(Base):
    __tablename__ = "device_tokens"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UserJob(Base):
    __tablename__ = "user_jobs"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_user_job"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), index=True)
    state: Mapped[str] = mapped_column(String(32), default="discovered")
    fit_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    fit_breakdown_json: Mapped[str] = mapped_column(Text, default="{}")
    last_scored_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TailoringRun(Base):
    """One preview/review lifecycle (Steps 16-20, spec 002 section 5.3).

    Everything needed to deterministically regenerate an artifact from
    scratch is snapshotted here at creation time -- the profile can change
    after this run is created (a later PUT /profile edit), but this run's
    own tailoring must always regenerate against the EXACT inputs it was
    proposed against, not whatever the profile looks like now. Snapshot/
    change/report/validation payloads are stored as canonical JSON text,
    matching every other *_json column in this module (Profile, Goals,
    Job, UserJob), rather than introducing a different storage shape here.
    """

    __tablename__ = "tailoring_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    original_resume_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    original_resume_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Hash (not the full profile) so a run stays a compact pointer while
    # still detecting "the profile has since changed" -- the immutable
    # snapshot the run needs for deterministic regeneration is the request
    # options/job snapshot/proposed changes captured below, all of which
    # are independent of what the LIVE profile currently looks like.
    profile_snapshot_hash: Mapped[str] = mapped_column(String(64))
    job_snapshot_json: Mapped[str] = mapped_column(Text, default="{}")
    request_options_json: Mapped[str] = mapped_column(Text, default="{}")
    candidate_fit_json: Mapped[str] = mapped_column(Text, default="{}")
    proposed_changes_json: Mapped[str] = mapped_column(Text, default="[]")
    reviewed_changes_json: Mapped[str] = mapped_column(Text, default="[]")
    validation_json: Mapped[str] = mapped_column(Text, default="{}")
    report_json: Mapped[str] = mapped_column(Text, default="{}")
    # PROPOSED -> REVIEWED (a disposition changed) -> VALIDATED (PASS/WARNING
    # regenerated) or FAILED (regeneration still FAILs).
    state: Mapped[str] = mapped_column(String(16), default="PROPOSED")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TailoredArtifact(Base):
    """One immutable generated file version for a TailoringRun. Regeneration
    always creates a NEW row (see TailoringRunStore.save_artifact) --
    existing rows are never updated or deleted, so a prior download link
    keeps returning the exact bytes it always did. `user_id` is
    denormalized from the owning run so ownership checks never need a
    join, matching how ResumeFile/Profile already key directly on
    user_id."""

    __tablename__ = "tailored_artifacts"
    __table_args__ = (
        UniqueConstraint("run_id", "kind", "version", name="uq_run_kind_version"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("tailoring_runs.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(8))  # "DOCX" | "PDF"
    version: Mapped[int] = mapped_column(Integer)
    filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    data: Mapped[bytes] = mapped_column(LargeBinary)
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    validation_status: Mapped[str] = mapped_column(String(16))
    # Points BACKWARD to the version this one replaces -- set once at
    # creation, never written onto the older row afterward, so immutability
    # holds for every artifact row for its entire lifetime.
    supersedes_artifact_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
