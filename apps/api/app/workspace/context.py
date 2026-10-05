"""Per-request workspace: the same session-shaped state the Streamlit app builds in
`require_identity`, so the shared modules (profile_import, active_job, tailoring_session,
the ui view models) work unchanged behind the API (decision 029)."""

from __future__ import annotations

import dataclasses
import enum
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterator

from fastapi import Depends

from app.workspace.identity import Owner, current_owner
from resume_tailorer.identity import applications_db_path, artifacts_dir, job_db_path
from resume_tailorer.profile_import import RECORD_KEY, load_into_session, store_for

OWNER_KEY = "owner_id"

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
    """A JobService with its own SQLite connections, for one request or one background run.

    Never shared: one person's requests run on several threads at once (two tabs, React's double
    fetch), and a Python SQLite connection used from two threads at the same time fails with
    "bad parameter or other API misuse". Opening one costs about 3 ms (decision 030)."""
    from resume_tailorer.job_search.job_service import JobService

    return JobService(db_path=job_db_path(owner_id), applications_db_path=applications_db_path(owner_id))


class Workspace:
    def __init__(self, owner: Owner, service=None):
        """`service`: reuse a request's open connections when re-reading state in that request."""
        self.owner = owner
        self.session: dict[str, Any] = {OWNER_KEY: owner.owner_id, "artifacts_dir": artifacts_dir(owner.owner_id)}
        self.service = service or job_service(owner.owner_id)
        load_into_session(self.session, owner.owner_id)
        try:
            from resume_tailorer.active_job import restore_handoff, restore_pending_job
            from resume_tailorer.session_profile import get_career_profile

            pending = restore_pending_job(self.session, self.record, self.service.db, self.service.fit_scorer,
                                          get_career_profile(self.session))
            if pending:
                # The tailored-resume handoff is labelled with this key (Streamlit sets it in
                # sync_pending_job); without it Apply can't match the resume to the job.
                from resume_tailorer.tailoring_session import ACTIVE_JOB_KEY

                self.session[ACTIVE_JOB_KEY] = pending.get("job_id")
            restore_handoff(self.session, self.record)
        except Exception:  # the chosen job is a convenience; never fail a request on it
            pass

    def close(self) -> None:
        self.service.close()

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


def session_version(owner_id: str) -> int:
    """The user's current session version; sessions made before a "sign out everywhere" are older."""
    import json

    from resume_tailorer.identity import user_dir

    try:
        return int(json.loads((user_dir(owner_id) / "account.json").read_text(encoding="utf-8")).get("session_version", 0))
    except (OSError, ValueError, TypeError):
        return 0


def workspace(owner: Owner = Depends(current_owner)) -> Iterator[Workspace]:
    """The person's workspace for one request; its database connections close afterwards."""
    from fastapi import HTTPException

    if owner.signed_in and owner.session_version != session_version(owner.owner_id):
        raise HTTPException(401, "You were signed out on all devices. Sign in again.")
    ws = Workspace(owner)
    try:
        yield ws
    finally:
        ws.close()


def stamp(value: datetime) -> str:
    """A moment in time for the browser, always with its UTC offset. The shared modules store
    naive server-local times (datetime.now()); without an offset a browser in another time zone
    reads them as its own local time and shows the wrong hour or day (decision 030)."""
    if value.tzinfo is None:
        value = value.astimezone()  # naive means server-local
    return value.isoformat()


def jsonable(value: Any) -> Any:
    """Dataclasses, enums, dates, tuples and sets as plain JSON values."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: jsonable(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, enum.Enum):
        return jsonable(value.value)
    if isinstance(value, datetime):
        return stamp(value)
    if isinstance(value, date):
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
