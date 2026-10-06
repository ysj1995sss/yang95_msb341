"""Tailor several jobs, then prepare the reviewed ones for applying (spec 011). No Streamlit
import: the workspace API and the Streamlit pages both use these.

- Each job is tailored in its own private session, so a batch never changes the job the person
  has open; its review is saved per job like any run.
- Preparing never submits anything (decision 016). It only tracks a job as "Ready to apply" when
  its review is finished and its resume passed validation, the same rule Apply uses for one job.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

MAX_BATCH = 10


def private_session(artifacts_dir: str, owner_id: str = "local") -> dict:
    return {"owner_id": owner_id, "artifacts_dir": artifacts_dir}


def tailor_job(job, *, artifacts_dir: str, original_bytes: bytes, filename: str, llm, fit_scorer=None,
               career_profile=None, provenance: Optional[dict] = None, target_length: str = "preserve",
               conservative: bool = False, progress: Callable[[str], None] = lambda m: None) -> dict:
    """Tailor one stored job in a private session and save its review. Returns the review state."""
    from resume_tailorer.job_search.job_service import build_tailor_snapshot
    from resume_tailorer.review_store import save_review
    from resume_tailorer.tailoring_service import regenerate, run_tailoring
    from resume_tailorer.tailoring_session import ACTIVE_JOB_KEY
    from resume_tailorer.ui.tailoring_view import safe_default_dispositions

    job_id = f"{job.source.value}_{job.source_id}"
    fit = fit_scorer.score_fit_detailed(career_profile, job) if (fit_scorer and career_profile) else None
    pending = build_tailor_snapshot(job, fit)
    session = private_session(artifacts_dir)
    session[ACTIVE_JOB_KEY] = job_id
    state = run_tailoring(session, original_bytes=original_bytes, filename=filename,
                          job_description=job.description or "", pending=pending, llm=llm,
                          target_length=target_length, conservative=conservative, progress=progress,
                          provenance=provenance, career_profile=career_profile)
    # The same first step as a single run: changes that claim a missing requirement start rejected.
    safe = safe_default_dispositions(state["changes"], state["report"].true_gaps)
    if safe:
        state["dispositions"].update(safe)
        state["gap_blocks_applied"] = True
        regenerate(session, state)
        state["reviewed"] = False
    save_review(artifacts_dir, job_id, state)
    return state


def review_ready(state: Optional[dict]) -> tuple[bool, str]:
    """(ready to apply, why not) for a saved review."""
    from resume_tailorer.ui.artifact_review import visible_changes
    from resume_tailorer.ui.tailor_progress import review_progress
    from resume_tailorer.ui.tailoring_view import group_changes

    if not state:
        return False, "Not tailored yet."
    report = state["report"]
    if report.validation.status.value == "FAIL":
        return False, "The tailored resume failed validation."
    reviewable = group_changes(visible_changes(state["changes"]), report.true_gaps).reviewable
    progress = review_progress(reviewable, state.get("decided", set()), state.get("dirty", False),
                               report.validation.status)
    return (True, "") if progress.can_continue else (False, progress.blocker or "Review the changes first.")


@dataclass
class Prepared:
    job_id: str
    title: str
    company: str
    url: str
    status: str  # "tracked" | "already_tracked" | "review_first" | "not_found"
    message: str = ""


def prepare_jobs(job_ids: list[str], *, service, profile, artifacts_dir: str) -> list[Prepared]:
    """Track each reviewed, passing job as "Ready to apply". Never submits anything."""
    from resume_tailorer.applications.models import ApplicationMode
    from resume_tailorer.review_store import load_review
    from resume_tailorer.tailoring_session import ACTIVE_JOB_KEY, publish_artifact_handoff

    results: list[Prepared] = []
    for job_id in job_ids[:MAX_BATCH]:
        job = service.db.get_job_posting(job_id)
        if job is None:
            results.append(Prepared(job_id, "", "", "", "not_found", "That job is no longer stored."))
            continue
        base = dict(job_id=job_id, title=job.title, company=job.company, url=job.url or "")
        state = load_review(artifacts_dir, job_id)
        ready, why = review_ready(state)
        if not ready:
            results.append(Prepared(**base, status="review_first", message=why))
            continue
        if service.applications_db.get_submissions_by_job(job_id):
            results.append(Prepared(**base, status="already_tracked", message="Already tracked."))
            continue
        session = private_session(artifacts_dir)
        session[ACTIVE_JOB_KEY] = job_id
        handoff = publish_artifact_handoff(
            session, pdf_bytes=state.get("pdf_bytes"), validation_status=state["report"].validation.status.value,
            tailored_alignment=state["report"].tailored_alignment, version=state.get("version", 1),
            folder=artifacts_dir,
        )
        if not handoff:
            results.append(Prepared(**base, status="review_first", message="There's no tailored PDF to attach."))
            continue
        score = state["report"].tailored_alignment
        for dry_run in (True, False):  # the dry run is the preview, as on Apply
            service.apply_for_job(job_id=job_id, profile=profile, resume_pdf_path=handoff["pdf_path"],
                                  mode=ApplicationMode.MANUAL,
                                  resume_match_score=min(float(score or 0) * 100, 100.0), dry_run=dry_run)
        results.append(Prepared(**base, status="tracked",
                                message="Tracked as ready to apply. Finish on the employer's site, then mark it applied."))
    return results


def handoff_for_saved_review(session: dict[str, Any], artifacts_dir: str, job_id: str) -> Optional[dict]:
    """Hand a saved review's passing PDF to Apply for this job (used when the person opens a batch
    job), so Apply finds it without running anything again."""
    from resume_tailorer.review_store import load_review
    from resume_tailorer.tailoring_session import ACTIVE_JOB_KEY, publish_artifact_handoff

    state = load_review(artifacts_dir, job_id)
    if not state:
        return None
    session[ACTIVE_JOB_KEY] = job_id
    return publish_artifact_handoff(
        session, pdf_bytes=state.get("pdf_bytes"), validation_status=state["report"].validation.status.value,
        tailored_alignment=state["report"].tailored_alignment, version=state.get("version", 1), folder=artifacts_dir,
    )
