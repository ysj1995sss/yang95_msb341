"""Who is using the app, and where their data lives.

With Google sign-in configured ([auth] in Streamlit secrets), every visitor
must sign in and gets an owner id derived from their account. Without it the
app runs in local single-user mode, which must never be shared publicly.
Every owner's jobs, applications, statuses, answers and resume files live in
their own directory, so one visitor's queries cannot reach another's data.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

LOCAL_OWNER = "local"
DATA_DIR_ENV = "JOB_COPILOT_DATA_DIR"


@dataclass(frozen=True)
class Identity:
    owner_id: str
    display_name: str
    signed_in: bool


def resolve_identity(auth_configured: bool, user_info: Mapping) -> Optional[Identity]:
    """The current identity, or None when sign-in is required but hasn't happened."""
    if not auth_configured:
        return Identity(LOCAL_OWNER, "Local user", signed_in=False)
    if not user_info.get("is_logged_in"):
        return None
    subject = user_info.get("sub") or user_info.get("email")
    if not subject:
        return None
    owner_id = hashlib.sha256(f"google:{subject}".encode("utf-8")).hexdigest()[:32]
    return Identity(owner_id, user_info.get("name") or user_info.get("email") or "Signed in", signed_in=True)


def data_root() -> Path:
    configured = os.environ.get(DATA_DIR_ENV)
    return Path(configured) if configured else Path.home() / ".job_copilot"


def user_dir(owner_id: str) -> Path:
    if not owner_id or any(ch in owner_id for ch in "/\\.:"):
        raise ValueError("Invalid owner id")
    path = data_root() / "users" / owner_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def job_db_path(owner_id: str) -> str:
    return str(user_dir(owner_id) / "job_search.db")


def applications_db_path(owner_id: str) -> str:
    return str(user_dir(owner_id) / "applications.db")


def artifacts_dir(owner_id: str) -> str:
    path = user_dir(owner_id) / "artifacts"
    path.mkdir(exist_ok=True)
    return str(path)
