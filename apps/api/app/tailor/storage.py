"""Persistence for immutable tailoring runs and artifact versions (Steps
16-20, spec 002 section 5.3). TailoringRunStore is the only writer of
TailoringRun/TailoredArtifact rows -- callers (the router, Task 7) never
touch the ORM models directly, so "artifacts are immutable" and "every
read enforces ownership" stay true in exactly one place.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import TailoredArtifact, TailoringRun


def _dump(value: Any) -> str:
    return json.dumps(value, default=str)


class TailoringRunStore:
    def __init__(self, db: Session):
        self.db = db

    def create_run(
        self,
        *,
        user_id: str,
        original_resume_id: str | None,
        original_resume_version: int | None,
        profile_snapshot_hash: str,
        job_snapshot: Mapping[str, Any],
        request_options: Mapping[str, Any],
        candidate_fit: Mapping[str, Any],
        proposed_changes: Sequence[Any],
        validation: Mapping[str, Any],
        baseline_tailored_text: str = "",
        source_kind: str = "PDF",
    ) -> TailoringRun:
        run = TailoringRun(
            user_id=user_id,
            original_resume_id=original_resume_id,
            original_resume_version=original_resume_version,
            profile_snapshot_hash=profile_snapshot_hash,
            job_snapshot_json=_dump(dict(job_snapshot)),
            request_options_json=_dump(dict(request_options)),
            candidate_fit_json=_dump(dict(candidate_fit)),
            proposed_changes_json=_dump(list(proposed_changes)),
            reviewed_changes_json=_dump(list(proposed_changes)),
            validation_json=_dump(dict(validation)),
            report_json="{}",
            baseline_tailored_text=baseline_tailored_text,
            source_kind=source_kind,
            state="PROPOSED",
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def update_run(
        self,
        run: TailoringRun,
        *,
        reviewed_changes: Sequence[Any] | None = None,
        validation: Mapping[str, Any] | None = None,
        report: Mapping[str, Any] | None = None,
        state: str | None = None,
    ) -> TailoringRun:
        if reviewed_changes is not None:
            run.reviewed_changes_json = _dump(list(reviewed_changes))
        if validation is not None:
            run.validation_json = _dump(dict(validation))
        if report is not None:
            run.report_json = _dump(dict(report))
        if state is not None:
            run.state = state
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def next_artifact_version(self, run_id: str, kind: str) -> int:
        current_max = (
            self.db.query(func.max(TailoredArtifact.version))
            .filter(TailoredArtifact.run_id == run_id, TailoredArtifact.kind == kind)
            .scalar()
        )
        return (current_max or 0) + 1

    def save_artifact(
        self,
        run_id: str,
        kind: str,
        data: bytes,
        filename: str,
        validation_status: str,
        mime_type: str | None = None,
    ) -> TailoredArtifact:
        run = self.db.get(TailoringRun, run_id)
        if run is None:
            raise ValueError(f"Unknown tailoring run: {run_id}")

        version = self.next_artifact_version(run_id, kind)
        previous = None
        if version > 1:
            previous = (
                self.db.query(TailoredArtifact)
                .filter(
                    TailoredArtifact.run_id == run_id,
                    TailoredArtifact.kind == kind,
                    TailoredArtifact.version == version - 1,
                )
                .one_or_none()
            )

        artifact = TailoredArtifact(
            run_id=run_id,
            user_id=run.user_id,
            kind=kind,
            version=version,
            filename=filename,
            mime_type=mime_type or _default_mime_type(kind),
            data=data,
            sha256=hashlib.sha256(data).hexdigest(),
            size_bytes=len(data),
            validation_status=validation_status,
            supersedes_artifact_id=previous.id if previous else None,
        )
        self.db.add(artifact)
        self.db.commit()
        self.db.refresh(artifact)
        return artifact

    def get_owned_run(self, run_id: str, user_id: str) -> TailoringRun | None:
        return (
            self.db.query(TailoringRun)
            .filter(TailoringRun.id == run_id, TailoringRun.user_id == user_id)
            .one_or_none()
        )

    def get_owned_artifact(self, artifact_id: str, user_id: str) -> TailoredArtifact | None:
        return (
            self.db.query(TailoredArtifact)
            .filter(TailoredArtifact.id == artifact_id, TailoredArtifact.user_id == user_id)
            .one_or_none()
        )

    def latest_artifact(self, run_id: str, kind: str) -> TailoredArtifact | None:
        return (
            self.db.query(TailoredArtifact)
            .filter(TailoredArtifact.run_id == run_id, TailoredArtifact.kind == kind)
            .order_by(TailoredArtifact.version.desc())
            .first()
        )


def _default_mime_type(kind: str) -> str:
    if kind == "DOCX":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if kind == "PDF":
        return "application/pdf"
    return "application/octet-stream"
