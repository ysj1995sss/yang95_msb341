"""Per-request workspace: the same session-shaped state the Streamlit app builds in
`require_identity`, so the shared modules (profile_import, active_job, tailoring_session,
the ui view models) work unchanged behind the API (decision 029)."""

from __future__ import annotations

import dataclasses
import enum
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Any

from fastapi import Depends

from app.workspace.identity import Owner, current_owner
from resume_tailorer.identity import applications_db_path, artifacts_dir, job_db_path
from resume_tailorer.profile_import import RECORD_KEY, load_into_session, store_for

OWNER_KEY = "owner_id"
_SERVICES: dict[str, Any] = {}
_SERVICES_LOCK = threading.Lock()

# Streamlit page paths used by the shared view models -> routes of the web app.
ROUTES = {
    "app.py": "/",
    "pages/1_Profile_Review.py": "/profile",
    "pages/2_Job_Search.py": "/jobs",
    "pages/5_Tailor.py": "/tailor",
    "pages/3_Applications.py": "/apply",
    "pages/4_Application_Tracker.py": "/tracker",
}


def job_service(owner_id: str):
    """One JobService per owner per process (its SQLite connections allow any thread)."""
    from resume_tailorer.job_search.job_service import JobService

    with _SERVICES_LOCK:
        service = _SERVICES.get(owner_id)
        if service is None:
            service = JobService(db_path=job_db_path(owner_id), applications_db_path=applications_db_path(owner_id))
            _SERVICES[owner_id] = service
        return service


def forget_services() -> None:
    """Tests: each test gets fresh databases."""
    with _SERVICES_LOCK:
        _SERVICES.clear()


class Workspace:
    def __init__(self, owner: Owner):
        self.owner = owner
        self.session: dict[str, Any] = {OWNER_KEY: owner.owner_id, "artifacts_dir": artifacts_dir(owner.owner_id)}
        self.service = job_service(owner.owner_id)
        load_into_session(self.session, owner.owner_id)
        try:
            from resume_tailorer.active_job import restore_handoff, restore_pending_job
            from resume_tailorer.session_profile import get_career_profile

            restore_pending_job(self.session, self.record, self.service.db, self.service.fit_scorer,
                                get_career_profile(self.session))
            restore_handoff(self.session, self.record)
        except Exception:  # the chosen job is a convenience; never fail a request on it
            pass

    @property
    def owner_id(self) -> str:
        return self.owner.owner_id

    @property
    def record(self) -> dict:
        return self.session.get(RECORD_KEY) or {}

    def store(self):
        return store_for(self.owner_id)

    def save_record(self, record: dict) -> dict:
        saved = self.store().save(record)
        load_into_session(self.session, self.owner_id, force=True)
        return saved


def workspace(owner: Owner = Depends(current_owner)) -> Workspace:
    return Workspace(owner)


def jsonable(value: Any) -> Any:
    """Dataclasses, enums, dates, tuples and sets as plain JSON values."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: jsonable(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, enum.Enum):
        return jsonable(value.value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k.value if isinstance(k, enum.Enum) else k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [jsonable(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, bytes):
        return None  # files are served by their own endpoints
    return value


def route_for(page: str) -> str:
    return ROUTES.get(page or "", page or "")
