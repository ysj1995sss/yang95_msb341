"""Session handoffs around Tailoring Studio: which job it is working on, and
the validated artifact it passes to Apply Launchpad. No Streamlit import."""

from __future__ import annotations

import hashlib
import os
import tempfile
from typing import Any, MutableMapping, Optional

ACTIVE_JOB_KEY = "tailoring_active_job_id"
HANDOFF_KEY = "tailored_artifact_handoff"


def _job_key(pending: dict) -> str:
    return str(pending.get("job_id") or pending.get("url") or pending.get("title") or "")


def sync_pending_job(
    session: MutableMapping[str, Any], pending: Optional[dict], jd_key: str, state_key: str
) -> bool:
    """Switch the studio to the job sent from Job Search. Returns True on a switch.

    A new job replaces the description and discards the previous job's review
    and artifact; the same job arriving again leaves the user's edits alone.
    """
    if not pending:
        return False
    job_key = _job_key(pending)
    if session.get(ACTIVE_JOB_KEY) == job_key:
        return False
    session[ACTIVE_JOB_KEY] = job_key
    session[jd_key] = pending.get("description") or ""
    session.pop(state_key, None)
    session.pop(HANDOFF_KEY, None)
    return True


def publish_artifact_handoff(
    session: MutableMapping[str, Any],
    *,
    pdf_bytes: Optional[bytes],
    validation_status: str,
    tailored_alignment: Optional[float],
    version: int,
    folder: Optional[str] = None,
) -> Optional[dict]:
    """Hand a validated PDF to Launchpad; a FAIL or missing artifact withdraws any handoff."""
    if not pdf_bytes or str(validation_status) == "FAIL":
        session.pop(HANDOFF_KEY, None)
        return None
    sha256 = hashlib.sha256(pdf_bytes).hexdigest()
    folder = folder or os.path.join(tempfile.gettempdir(), "job_copilot_artifacts")
    os.makedirs(folder, exist_ok=True)
    pdf_path = os.path.join(folder, f"{sha256[:16]}.pdf")
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)
    handoff = {
        "job_id": session.get(ACTIVE_JOB_KEY) or None,
        "pdf_path": pdf_path,
        "sha256": sha256,
        "version": version,
        "validation_status": str(validation_status),
        "resume_match_score": tailored_alignment,
    }
    session[HANDOFF_KEY] = handoff
    return handoff


def handoff_for_job(session: MutableMapping[str, Any], job_id: str) -> Optional[dict]:
    """The tailored artifact for this job, or None if it was made for a different job."""
    handoff = session.get(HANDOFF_KEY)
    if not handoff:
        return None
    if handoff.get("job_id") and job_id and handoff["job_id"] != job_id:
        return None
    return handoff
