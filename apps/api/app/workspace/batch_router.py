"""Batches (spec 011): tailor several jobs one at a time in the background, open any of them in
Tailor, and prepare the reviewed ones for applying. Nothing is ever submitted (decision 016).

The batch uses the same run lock and run status as a single run, so a person never has two
tailoring runs at once, and each job counts toward the daily tailoring limit when it starts.
State lives in `users/<owner>/tailor/batch.json`, so it survives a restart: a batch interrupted
by a restart says so, and the jobs it didn't reach are listed as not started.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.workspace import limits
from app.workspace.context import Workspace, workspace
from app.workspace.tailor_router import (
    BOOT_ID, LENGTHS, RunRequest, _RUNS_LOCK, _load_local_env, _read_run, _resume_source, _settings_for,
    _user_file, _write_run,
)

router = APIRouter(prefix="/v2", tags=["workspace"])
logger = logging.getLogger("job_copilot.api.batch")
MAX_BATCH = 10


def _batch_file(owner_id: str):
    return _user_file(owner_id, "tailor", "batch.json")


def _read_batch(owner_id: str) -> Optional[dict]:
    try:
        data = json.loads(_batch_file(owner_id).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if data.get("status") == "running" and data.get("boot") != BOOT_ID:
        data["status"] = "stopped"
        data["note"] = "The server restarted during this batch. Jobs it didn't reach weren't tailored."
        for item in data["items"]:
            if item["status"] in ("queued", "running"):
                item["status"] = "not_started"
    return data


def _write_batch(owner_id: str, data: dict) -> None:
    path = _batch_file(owner_id)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    os.replace(tmp, path)


def _view(owner_id: str) -> Optional[dict]:
    data = _read_batch(owner_id)
    if not data:
        return None
    counts = {s: sum(1 for i in data["items"] if i["status"] == s) for s in ("done", "failed", "skipped")}
    data.pop("boot", None)
    data["summary"] = (f"{counts['done']} of {len(data['items'])} tailored"
                       + (f" · {counts['failed']} failed" if counts["failed"] else "")
                       + (f" · {counts['skipped']} skipped" if counts["skipped"] else ""))
    return data


class BatchRequest(RunRequest):
    job_ids: list[str] = Field(min_length=1)


@router.post("/batch/tailor")
def start_batch(body: BatchRequest, ws: Workspace = Depends(workspace)):
    _load_local_env()
    job_ids = list(dict.fromkeys(body.job_ids))
    if len(job_ids) > MAX_BATCH:
        raise HTTPException(400, f"Choose up to {MAX_BATCH} jobs for one batch.")
    source = _resume_source(ws)
    if source is None:
        raise HTTPException(409, "Import your resume in Career Profile first.")
    if source[2].startswith("One-off"):
        raise HTTPException(409, "A batch uses your Career Profile resume. Remove the one-off file in Tailor first.")
    try:
        settings = _settings_for(body, ws)
    except ValueError as exc:
        raise HTTPException(503, "The writing model isn't set up on this server.") from exc
    items = []
    for job_id in job_ids:
        job = ws.service.db.get_job_posting(job_id)
        if job is None:
            raise HTTPException(404, "One of those jobs is no longer stored. Search again.")
        usable = bool((job.description or "").strip())
        items.append({"job_id": job_id, "title": job.title, "company": job.company,
                      "status": "queued" if usable else "skipped",
                      "error": "" if usable else "This posting has no description to tailor against."})
    with _RUNS_LOCK:
        if _read_run(ws.owner_id).get("status") == "running":
            raise HTTPException(409, "A tailoring run is already in progress. Wait for it to finish.")
        data = {"id": uuid.uuid4().hex[:8], "status": "running", "boot": BOOT_ID, "created": time.time(),
                "items": items, "note": ""}
        _write_batch(ws.owner_id, data)
        _write_run(ws.owner_id, {"status": "running", "step": "Starting the batch", "job_id": None,
                                 "batch": True, "started": time.time(), "boot": BOOT_ID})
    threading.Thread(target=_batch_worker, args=(ws.owner, data["id"], body, settings),
                     name=f"batch-{ws.owner_id[:8]}", daemon=True).start()
    return _view(ws.owner_id)


def _batch_worker(owner, batch_id: str, request: BatchRequest, settings) -> None:
    from resume_tailorer.batch import tailor_job
    from resume_tailorer.llm.client import LLMClient
    from resume_tailorer.session_profile import get_career_profile

    ws = Workspace(owner)
    try:
        for index in range(len(request.job_ids)):
            with _RUNS_LOCK:
                data = _read_batch(ws.owner_id)
                if not data or data["id"] != batch_id or data["status"] != "running":
                    return  # cancelled or replaced
                item = data["items"][index] if index < len(data["items"]) else None
                if item is None or item["status"] != "queued":
                    continue
                try:
                    limits.use(ws.owner_id, "tailor")
                except HTTPException as exc:
                    for later in data["items"][index:]:
                        if later["status"] == "queued":
                            later.update(status="skipped", error=str(exc.detail))
                    _write_batch(ws.owner_id, data)
                    break
                item["status"] = "running"
                _write_batch(ws.owner_id, data)
                _write_run(ws.owner_id, {**_read_run(ws.owner_id), "status": "running", "job_id": item["job_id"],
                                         "batch": True, "step": f"Tailoring {item['title']} ({index + 1} of {len(data['items'])})"})
            outcome = {"status": "done", "error": ""}
            try:
                job = ws.service.db.get_job_posting(item["job_id"])
                source = _resume_source(ws)
                tailor_job(job, artifacts_dir=ws.session["artifacts_dir"], original_bytes=source[1], filename=source[0],
                           llm=LLMClient(settings), fit_scorer=ws.service.fit_scorer,
                           career_profile=get_career_profile(ws.session), provenance=ws.record.get("provenance"),
                           target_length=LENGTHS[request.length], conservative=request.conservative)
            except Exception as exc:  # one job failing never stops the rest
                logger.exception("Batch job failed for owner %s", ws.owner_id[:8])
                outcome = {"status": "failed", "error": f"Tailoring didn't finish: {exc}"}
            with _RUNS_LOCK:
                data = _read_batch(ws.owner_id)
                if data and data["id"] == batch_id:
                    data["items"][index].update(outcome)
                    _write_batch(ws.owner_id, data)
    finally:
        with _RUNS_LOCK:
            data = _read_batch(ws.owner_id)
            if data and data["id"] == batch_id and data["status"] == "running":
                data["status"] = "done"
                _write_batch(ws.owner_id, data)
            _write_run(ws.owner_id, {**_read_run(ws.owner_id), "status": "done", "batch": True,
                                     "step": "Batch finished", "finished": time.time()})
        ws.close()


@router.get("/batch")
def batch_status(ws: Workspace = Depends(workspace)):
    return {"batch": _view(ws.owner_id)}


@router.delete("/batch")
def cancel_batch(ws: Workspace = Depends(workspace)):
    """Stop after the job that's running now; jobs not started stay untailored."""
    with _RUNS_LOCK:
        data = _read_batch(ws.owner_id)
        if data and data["status"] == "running":
            data["status"] = "cancelled"
            for item in data["items"]:
                if item["status"] == "queued":
                    item.update(status="skipped", error="Cancelled before it started.")
            _write_batch(ws.owner_id, data)
    return {"batch": _view(ws.owner_id)}


class JobChoice(BaseModel):
    job_id: str


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
    """Track every reviewed, passing batch job as "Ready to apply". Never submits anything."""
    from resume_tailorer.batch import prepare_jobs
    from resume_tailorer.session_profile import get_career_profile

    data = _read_batch(ws.owner_id)
    job_ids = body.job_ids or [i["job_id"] for i in (data or {}).get("items", []) if i["status"] == "done"]
    if not job_ids:
        raise HTTPException(409, "No tailored batch jobs to prepare yet.")
    profile = get_career_profile(ws.session)
    if profile is None:
        raise HTTPException(409, "Import your resume in Career Profile first.")
    results = prepare_jobs(job_ids, service=ws.service, profile=profile, artifacts_dir=ws.session["artifacts_dir"])
    return {"results": [r.__dict__ for r in results]}
