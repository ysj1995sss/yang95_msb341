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
