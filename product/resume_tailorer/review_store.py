"""The Tailor review (proposed changes, your decisions, the built resume), kept per job
so leaving mid-review loses nothing (decision 027). No Streamlit import.

Stored with pickle because the review holds the app's own dataclasses and file bytes.
Files are only ever written by this app, inside the user's own data folder, and a file
that no longer loads (e.g. after an upgrade) is ignored rather than trusted.
"""

from __future__ import annotations

import hashlib
import os
import pickle
import tempfile
from pathlib import Path
from typing import Any, Optional

_FORMAT = 1


def _path(folder: str, job_id: str) -> Path:
    name = hashlib.sha256(job_id.encode("utf-8")).hexdigest()[:20]
    return Path(folder) / "reviews" / f"{name}.review"


def signature(state: dict) -> tuple:
    """What changes when the user decides something; saving is skipped when it hasn't."""
    return (
        tuple(sorted((state.get("dispositions") or {}).items())),
        tuple(sorted(state.get("decided") or ())),
        tuple(sorted((state.get("manual_texts") or {}).items())),
        state.get("version"),
        state.get("reviewed"),
        state.get("dirty"),
    )


def save_review(folder: Optional[str], job_id: Optional[str], state: dict) -> bool:
    if not folder or not job_id or not state:
        return False
    path = _path(folder, job_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"format": _FORMAT, "job_id": job_id, "state": state}
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp, path)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False
    return True


def load_review(folder: Optional[str], job_id: Optional[str]) -> Optional[dict[str, Any]]:
    if not folder or not job_id:
        return None
    path = _path(folder, job_id)
    if not path.is_file():
        return None
    try:
        with open(path, "rb") as f:
            payload = pickle.load(f)
    except Exception:
        return None
    if not isinstance(payload, dict) or payload.get("format") != _FORMAT or payload.get("job_id") != job_id:
        return None
    state = payload.get("state")
    return state if isinstance(state, dict) and "changes" in state else None


def discard_review(folder: Optional[str], job_id: Optional[str]) -> None:
    if folder and job_id:
        try:
            _path(folder, job_id).unlink()
        except OSError:
            pass
