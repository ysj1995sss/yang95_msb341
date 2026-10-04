"""Turn an uploaded resume into the stored Career Profile, and load it into a
session. No Streamlit import; callers pass the session mapping."""

from __future__ import annotations

import os
import tempfile
from typing import Any, MutableMapping, Optional

from resume_tailorer.identity import user_dir
from resume_tailorer.profile_store import FROM_RESUME, ProfileStore, fact_paths

RECORD_KEY = "profile_record"
_LOADED_MTIME_KEY = "profile_record_mtime"
_LOADED_OWNER_KEY = "profile_record_owner"


def store_for(owner_id: str) -> ProfileStore:
    return ProfileStore(user_dir(owner_id) / "profile")


def import_resume(store: ProfileStore, filename: str, data: bytes, parser=None) -> dict:
    """Parse a resume and make it the profile's current version.

    Preferences, links and authorization answers are kept; facts are replaced
    by the new resume's facts and must be confirmed again.
    """
    if parser is None:
        from resume_tailorer.parsers import ResumeParser

        parser = ResumeParser()
    suffix = os.path.splitext(filename)[1].lower()
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        profile = parser.parse(tmp_path)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    record = store.load()
    store.save_resume_file(record, filename, data)
    record["profile"] = profile.to_dict()
    record["provenance"] = {path: FROM_RESUME for path in fact_paths(record["profile"])}
    record["facts_confirmed_at"] = None
    return store.save(record)


def load_into_session(session: MutableMapping[str, Any], owner_id: str, force: bool = False) -> Optional[dict]:
    """Make the stored profile this session's career profile (reloads when the file changed)."""
    from resume_tailorer.session_profile import (
        CAREER_PROFILE_KEY,
        FACT_VAULT,
        PROFILE_SOURCE_KEY,
        set_career_profile,
    )

    store = store_for(owner_id)
    mtime = store.mtime()
    if (
        not force
        and session.get(_LOADED_OWNER_KEY) == owner_id
        and session.get(_LOADED_MTIME_KEY) == mtime
        and RECORD_KEY in session
    ):
        return session[RECORD_KEY]
    record = store.load()
    session[RECORD_KEY] = record
    session[_LOADED_OWNER_KEY] = owner_id
    session[_LOADED_MTIME_KEY] = mtime
    if record.get("profile"):
        session.pop(PROFILE_SOURCE_KEY, None)
        set_career_profile(session, record["profile"], FACT_VAULT)
    elif session.get(PROFILE_SOURCE_KEY) == FACT_VAULT:
        session.pop(CAREER_PROFILE_KEY, None)
        session.pop(PROFILE_SOURCE_KEY, None)
    return record


def save_record(session: MutableMapping[str, Any], owner_id: str, record: dict) -> dict:
    saved = store_for(owner_id).save(record)
    load_into_session(session, owner_id, force=True)
    return saved
