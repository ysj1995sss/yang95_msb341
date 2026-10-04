"""The job the user chose to prepare, kept across sessions (spec 008).

Jobs stores the choice in the Career Profile record as `active_job_id`. When a
new session starts (or the app restarts), every page can rebuild the exact
handoff Jobs would have made: the stored posting with its full description and
a freshly computed Candidate Fit. No Streamlit import.
"""

from __future__ import annotations

from typing import Any, MutableMapping, Optional

from resume_tailorer.job_search.job_service import PENDING_TAILOR_JOB_KEY, build_tailor_snapshot

ACTIVE_JOB_FIELD = "active_job_id"
HANDOFF_FIELD = "active_handoff"


def remember(record: MutableMapping[str, Any], job_id: str) -> None:
    record[ACTIVE_JOB_FIELD] = job_id


def restore_pending_job(session: MutableMapping[str, Any], record: Optional[dict], job_db, fit_scorer,
                        profile) -> Optional[dict]:
    """The session's pending job, rebuilt from the record when the session lost it."""
    if session.get(PENDING_TAILOR_JOB_KEY):
        return session[PENDING_TAILOR_JOB_KEY]
    job_id = (record or {}).get(ACTIVE_JOB_FIELD)
    if not job_id:
        return None
    job = job_db.get_job_posting(job_id)
    if job is None or not (job.description or "").strip():
        return None
    fit = fit_scorer.score_fit_detailed(profile, job) if profile is not None else None
    snapshot = build_tailor_snapshot(job, fit)
    session[PENDING_TAILOR_JOB_KEY] = snapshot
    return snapshot


def remember_handoff(record: MutableMapping[str, Any], handoff: Optional[dict], review_complete: bool) -> bool:
    """Keep the validated resume handoff with the record. Returns True when it changed."""
    value = dict(handoff, review_complete=bool(review_complete)) if handoff else None
    if record.get(HANDOFF_FIELD) == value:
        return False
    record[HANDOFF_FIELD] = value
    return True


def restore_handoff(session: MutableMapping[str, Any], record: Optional[dict]) -> Optional[dict]:
    """Bring back the tailored resume for the active job, only if the exact file is still there."""
    import hashlib
    import os

    from resume_tailorer.tailoring_session import HANDOFF_KEY

    if session.get(HANDOFF_KEY):
        return session[HANDOFF_KEY]
    saved = (record or {}).get(HANDOFF_FIELD)
    pending = session.get(PENDING_TAILOR_JOB_KEY) or {}
    if not saved or saved.get("job_id") != pending.get("job_id"):
        return None
    if str(saved.get("validation_status", "")).upper() == "FAIL":
        return None
    path = saved.get("pdf_path") or ""
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as f:
        if hashlib.sha256(f.read()).hexdigest() != saved.get("sha256"):
            return None
    session[HANDOFF_KEY] = dict(saved)
    return session[HANDOFF_KEY]
