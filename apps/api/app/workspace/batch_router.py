"""Batches (specs 011 and 014): tailor several jobs one at a time in the background, open any of
them in Tailor, continue a batch that stopped, and prepare the reviewed ones for applying.
Nothing is ever submitted (decision 016).

The loop itself is `resume_tailorer.batch_runner`, shared with the Streamlit app, and the state
lives in `users/<owner>/tailor/batch.json`. Here the batch also keeps the API's run status, so a
person never has a single run and a batch at once, and each job counts toward the daily
tailoring limit when it starts.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.workspace import limits
from app.workspace.context import Workspace, workspace
from app.workspace.tailor_router import (
    BOOT_ID, LENGTHS, RunRequest, _RUNS_LOCK, _load_local_env, _read_run, _resume_source, _settings_for,
    _write_run,
)

router = APIRouter(prefix="/v2", tags=["workspace"])
logger = logging.getLogger("job_copilot.api.batch")
MAX_BATCH = 10


def _user_dir(owner_id: str):
    from resume_tailorer.identity import user_dir

    return user_dir(owner_id)


def _view(ws: Workspace) -> Optional[dict]:
    from resume_tailorer.batch import item_freshness
    from resume_tailorer.batch_runner import read_batch, view
    from resume_tailorer.session_profile import get_career_profile

    shown = view(read_batch(_user_dir(ws.owner_id)))
    if shown:
        profile = get_career_profile(ws.session)
        for item in shown["items"]:
            item.update(item_freshness(ws.session["artifacts_dir"], item, profile))
    return shown


class JobChoice(BaseModel):
    job_id: str


class BatchRequest(RunRequest):
    job_ids: list[str] = Field(min_length=1)


def _hooks(owner, settings, request: RunRequest):
    """How the shared runner tailors one job here, counts the daily limit and reports progress."""
    from resume_tailorer.batch import stage_tailor_job, publish_staged_review
    from resume_tailorer.batch_runner import Hooks, LimitReached, when_current
    from resume_tailorer.llm.client import LLMClient
    from resume_tailorer.session_profile import get_career_profile

    def tailor_one(claim):
        job_id = claim.job_id
        ws = Workspace(owner)  # fresh each job, so a profile edit mid-batch is used from then on
        try:
            job = ws.service.db.get_job_posting(job_id)
            if job is None:
                raise LookupError("That job is no longer stored.")
            # A one-off upload changed mid-batch must not replace the batch's profile resume.
            meta = ws.record.get('resume')
            data = ws.store().resume_bytes(meta) if meta else None
            source = (meta['filename'], data) if data else None
            if source is None:
                raise LookupError("Import your resume in Career Profile first.")
            return stage_tailor_job(job, execution=claim.execution, artifacts_dir=ws.session["artifacts_dir"], original_bytes=source[1], filename=source[0],
                       llm=LLMClient(settings), fit_scorer=ws.service.fit_scorer,
                       career_profile=get_career_profile(ws.session), provenance=ws.record.get("provenance"),
                       target_length=LENGTHS[request.length], conservative=request.conservative)
        finally:
            ws.close()

    def use_limit() -> None:
        try:
            limits.use(owner.owner_id, "tailor")
        except HTTPException as exc:
            raise LimitReached(str(exc.detail)) from exc

    def on_step(claim, step: str) -> None:
        with _RUNS_LOCK:
            if not _read_run(owner.owner_id).get('batch'):
                return
            when_current(claim, lambda: _write_run(owner.owner_id, {**_read_run(owner.owner_id), "status": "running", "job_id": claim.job_id,
                                        "batch": True, "step": step, "boot": BOOT_ID}))

    def on_finish(claim) -> None:
        with _RUNS_LOCK:
            if not _read_run(owner.owner_id).get('batch'):
                return
            when_current(claim, lambda: _write_run(owner.owner_id, {**_read_run(owner.owner_id), "status": "done", "batch": True,
                                        "step": "Batch finished", "finished": time.time()}))

    return Hooks(tailor_one=lambda job_id: None, tailor_claim=tailor_one, publish_result=publish_staged_review,
                 use_limit=use_limit, on_claim_step=on_step, on_claim_finish=on_finish)


def _check_can_run(ws: Workspace, body: RunRequest):
    _load_local_env()
    source = _resume_source(ws)
    if source is None:
        raise HTTPException(409, "Import your resume in Career Profile first.")
    if source[3]:
        raise HTTPException(409, "A batch uses your Career Profile resume. Remove the one-off file in Tailor first.")
    try:
        return _settings_for(body, ws)
    except ValueError as exc:
        raise HTTPException(503, "The writing model isn't set up on this server.") from exc


def _begin(ws: Workspace, launch) -> dict:
    """Claim the run status, then let `launch` start the runner. One run or batch at a time."""
    from resume_tailorer.batch_runner import BatchBusy

    with _RUNS_LOCK:
        run = _read_run(ws.owner_id)
        # A recovered batch may still have a stale API callback status; token ownership wins.
        from resume_tailorer.batch_runner import read_batch, _is_active
        batch = read_batch(_user_dir(ws.owner_id)) if run.get('batch') else None
        if run.get("status") == "running" and (not run.get('batch') or (batch and _is_active(batch))):
            raise HTTPException(409, "A tailoring run is already in progress. Wait for it to finish.")
        try:
            launch()
        except BatchBusy as exc:
            raise HTTPException(409, str(exc)) from exc
        _write_run(ws.owner_id, {"status": "running", "step": "Starting the batch", "job_id": None,
                                 "batch": True, "started": time.time(), "boot": BOOT_ID})
    return {"batch": _view(ws)}


@router.post("/batch/tailor")
def start_batch(body: BatchRequest, ws: Workspace = Depends(workspace)):
    from resume_tailorer import batch_runner

    job_ids = list(dict.fromkeys(body.job_ids))
    if len(job_ids) > MAX_BATCH:
        raise HTTPException(400, f"Choose up to {MAX_BATCH} jobs for one batch.")
    settings = _check_can_run(ws, body)
    items = []
    for job_id in job_ids:
        job = ws.service.db.get_job_posting(job_id)
        if job is None:
            raise HTTPException(404, "One of those jobs is no longer stored. Search again.")
        items.append(batch_runner.new_item(job_id, job.title, job.company, job.description or ""))
    # A per-run API key or address is never stored: Continue uses the model name with the server's key.
    options = {"model": (body.model or "").strip() or None, "length": body.length, "conservative": body.conservative}
    hooks = _hooks(ws.owner, settings, body)
    return _begin(ws, lambda: batch_runner.start(_user_dir(ws.owner_id), items, options, hooks))["batch"]


@router.post("/batch/continue")
def continue_batch(body: RunRequest, ws: Workspace = Depends(workspace)):
    """Spec 014: tailor the jobs that didn't finish (restart, failure or stop), with the batch's options."""
    from resume_tailorer import batch_runner

    data = batch_runner.read_batch(_user_dir(ws.owner_id))
    if not data or not any(batch_runner.is_resumable(i) for i in data["items"]):
        raise HTTPException(409, "There's nothing to continue in this batch.")
    options = {**batch_runner.DEFAULT_OPTIONS, **(data.get("options") or {})}
    request = RunRequest(length=options["length"], conservative=bool(options["conservative"]),
                         model=(body.model or "").strip() or options.get("model"),
                         api_key=body.api_key, api_base=body.api_base)
    settings = _check_can_run(ws, request)
    hooks = _hooks(ws.owner, settings, request)

    def launch():
        try:
            batch_runner.continue_batch(_user_dir(ws.owner_id), hooks)
        except LookupError as exc:
            raise HTTPException(409, str(exc)) from exc

    return _begin(ws, launch)


@router.post("/batch/again")
def tailor_again(body: JobChoice, ws: Workspace = Depends(workspace)):
    """Spec 014: tailor one job again (its profile changed) with the batch's options, keeping the batch."""
    from resume_tailorer import batch_runner

    job = ws.service.db.get_job_posting(body.job_id)
    if job is None:
        raise HTTPException(404, "That job is no longer stored.")
    last = batch_runner.read_batch(_user_dir(ws.owner_id)) or {}
    options = {**batch_runner.DEFAULT_OPTIONS, **(last.get("options") or {})}
    request = RunRequest(length=options["length"], conservative=bool(options["conservative"]), model=options.get("model"))
    settings = _check_can_run(ws, request)
    hooks = _hooks(ws.owner, settings, request)
    items = [batch_runner.new_item(body.job_id, job.title, job.company, job.description or "")]

    def launch():
        # Keep the batch (its other jobs stay listed); a job not in it gets a batch of its own.
        if batch_runner.redo(_user_dir(ws.owner_id), body.job_id, hooks) is None:
            batch_runner.start(_user_dir(ws.owner_id), items, options, hooks)

    return _begin(ws, launch)


@router.get("/batch")
def batch_status(ws: Workspace = Depends(workspace)):
    return {"batch": _view(ws)}


@router.delete("/batch")
def cancel_batch(ws: Workspace = Depends(workspace)):
    """Stop after the job that's running now; the jobs not started can be continued later."""
    from resume_tailorer.batch_runner import cancel

    cancel(_user_dir(ws.owner_id))
    return {"batch": _view(ws)}


@router.post("/batch/open")
def open_batch_job(body: JobChoice, ws: Workspace = Depends(workspace)):
    """Make a batch job the one open in Tailor and Apply, with its saved review and resume."""
    from resume_tailorer.active_job import remember, remember_handoff
    from resume_tailorer.batch import handoff_for_saved_review, review_ready
    from resume_tailorer.review_store import load_review

    if ws.service.db.get_job_posting(body.job_id) is None:
        raise HTTPException(404, "That job is no longer stored.")
    record = ws.store().load()
    remember(record, body.job_id)
    handoff = handoff_for_saved_review({}, ws.session["artifacts_dir"], body.job_id)
    ready, _why = review_ready(load_review(ws.session["artifacts_dir"], body.job_id))
    remember_handoff(record, handoff, ready)
    ws.save_record(record)
    return {"opened": body.job_id}


class PrepareRequest(BaseModel):
    job_ids: Optional[list[str]] = None


@router.post("/batch/prepare")
def prepare_batch(body: PrepareRequest, ws: Workspace = Depends(workspace)):
    """Track every reviewed, passing, up-to-date batch job as "Ready to apply". Never submits."""
    from resume_tailorer.batch import prepare_jobs
    from resume_tailorer.batch_runner import read_batch
    from resume_tailorer.session_profile import get_career_profile

    data = read_batch(_user_dir(ws.owner_id))
    job_ids = body.job_ids or [i["job_id"] for i in (data or {}).get("items", []) if i["status"] == "done"]
    if not job_ids:
        raise HTTPException(409, "No tailored batch jobs to prepare yet.")
    profile = get_career_profile(ws.session)
    if profile is None:
        raise HTTPException(409, "Import your resume in Career Profile first.")
    results = prepare_jobs(job_ids, service=ws.service, profile=profile, artifacts_dir=ws.session["artifacts_dir"])
    return {"results": [r.__dict__ for r in results]}
