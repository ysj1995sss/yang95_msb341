"""Tailor (spec 009 phase 3): run tailoring in the background, review each change, rebuild
from decisions, preview and download. The pipeline is resume_tailorer.tailoring_service
(the same code the Streamlit page runs) and the review is the same saved state
(resume_tailorer.review_store), so either frontend can continue a review."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel

from app.workspace import limits
from app.workspace.context import Workspace, jsonable, workspace

router = APIRouter(prefix="/v2", tags=["workspace"])

# Run status and one-off resumes live in the user's data folder, so a restart loses neither
# (decision 030). BOOT_ID marks which server start a "running" status belongs to: a run from an
# earlier start can't still be running, and is reported as interrupted.
BOOT_ID = uuid.uuid4().hex
logger = logging.getLogger("job_copilot.tailor")
_RUNS_LOCK = threading.Lock()


def _user_file(owner_id: str, *parts: str) -> Path:
    from resume_tailorer.identity import user_dir

    path = user_dir(owner_id).joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _write_run(owner_id: str, data: dict) -> None:
    path = _user_file(owner_id, "tailor", "run.json")
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    os.replace(tmp, path)


def _read_run(owner_id: str) -> dict:
    path = _user_file(owner_id, "tailor", "run.json")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"status": "idle"}
    if data.get("status") == "running" and data.get("boot") != BOOT_ID:
        data.update(status="failed", error="The server restarted while tailoring. Start again.")
    return data


def _one_off(owner_id: str) -> Optional[tuple[str, bytes]]:
    meta = _user_file(owner_id, "tailor", "one_off.json")
    try:
        name = json.loads(meta.read_text(encoding="utf-8"))["filename"]
        return name, _user_file(owner_id, "tailor", "one_off.bin").read_bytes()
    except (OSError, ValueError, KeyError):
        return None
MAX_RESUME_BYTES = 10 * 1024 * 1024
LENGTHS = {"preserve": "preserve", "1_page": "1_page", "2_page": "2_page"}


def _load_local_env() -> None:
    """Local development: the same product/.env the Streamlit app reads. Never overrides
    real environment variables (how production supplies LLM_MODEL / LLM_API_KEY)."""
    import resume_tailorer
    from dotenv import load_dotenv

    load_dotenv(Path(resume_tailorer.__file__).resolve().parent.parent / ".env", override=False)


def _pending(ws: Workspace) -> dict:
    from resume_tailorer.job_search.job_service import PENDING_TAILOR_JOB_KEY

    return ws.session.get(PENDING_TAILOR_JOB_KEY) or {}


def _review(ws: Workspace, job_id: Optional[str]) -> Optional[dict]:
    from resume_tailorer.review_store import load_review

    return load_review(ws.session["artifacts_dir"], job_id) if job_id else None


def _save_review(ws: Workspace, job_id: str, state: dict) -> None:
    from resume_tailorer.review_store import save_review

    save_review(ws.session["artifacts_dir"], job_id, state)


def _persist_handoff(ws: Workspace, review_complete: bool) -> None:
    """Keep the validated resume with the Career Profile so Apply finds it (as Streamlit does)."""
    from resume_tailorer.active_job import remember_handoff
    from resume_tailorer.tailoring_session import HANDOFF_KEY

    record = ws.store().load()
    handoff = ws.session.get(HANDOFF_KEY)
    if handoff:
        handoff["review_complete"] = bool(review_complete)
    if remember_handoff(record, handoff, review_complete):
        ws.save_record(record)


def _resume_source(ws: Workspace):
    one_off = _one_off(ws.owner_id)
    if one_off:
        return one_off[0], one_off[1], f"One-off file for this job: {one_off[0]}"
    meta = ws.record.get("resume")
    data = ws.store().resume_bytes(meta) if meta else None
    if data:
        return meta["filename"], data, f"{meta['filename']} · version {meta['version']} from your Career Profile"
    return None


def _groups(state: dict, show_all: bool = False):
    from resume_tailorer.ui.artifact_review import visible_changes
    from resume_tailorer.ui.tailoring_view import group_changes

    return group_changes(visible_changes(state["changes"], advanced=show_all), state["report"].true_gaps)


def _review_view(ws: Workspace, state: dict, show_all: bool = False) -> dict:
    from resume_tailorer.analyzers.term_match import displayable_gaps, short_requirement
    from resume_tailorer.artifacts.models import FidelityMode
    from resume_tailorer.ui.pdf_preview import pdf_page_images
    from resume_tailorer.ui.tailor_progress import (
        DECISION_DONE, VERBS, artifact_status_text, artifact_tone, empty_queue_message, next_undecided,
        readable_requirement, rejected_by_checks, review_progress, supporting_fact, validation_word,
    )

    report = state["report"]
    groups = _groups(state, show_all)
    decided = state.get("decided") or set()
    progress = review_progress(groups.reviewable, decided, state.get("dirty", False), report.validation.status)
    status = report.validation.status
    pages = len(pdf_page_images(state.get("pdf_bytes") or b"")) if status.value != "FAIL" else 0

    def change_view(change) -> dict:
        current = state["dispositions"].get(change.change_id)
        is_decided = change.change_id in decided
        return {
            "id": change.change_id,
            "requirement": readable_requirement(change),
            "fact": supporting_fact(change, state["profile"]),
            "reason": change.reason or "Reworded to match the posting",
            "original": change.original_text or "",
            "proposed": change.proposed_text or "",
            "check": validation_word(change.validation_status),
            "decision": current if is_decided else None,
            "decision_label": DECISION_DONE.get(current, "Not reviewed yet") if is_decided else "Not reviewed yet",
            "manual_text": state["manual_texts"].get(change.change_id, change.proposed_text or ""),
        }

    return {
        "version": state.get("version", 1),
        "status": status.value,
        "status_text": artifact_status_text(status),
        "status_tone": artifact_tone(status),
        "findings": [f.message for f in report.validation.findings],
        "fidelity": "Original layout kept" if report.fidelity_mode is FidelityMode.PRESERVED else "Rebuilt layout; details may differ",
        "page_count": report.tailored_page_count,
        "preview_pages": pages,
        "has_pdf": bool(state.get("pdf_bytes")) and status.value != "FAIL",
        "has_docx": bool(state.get("docx_bytes")) and status.value != "FAIL",
        "tailored_text": state.get("tailored_text") or "",
        "alignment": {"before": report.original_alignment, "after": report.tailored_alignment},
        "pages_before_after": [report.original_page_count, report.tailored_page_count],
        "unsupported_claims": list(report.unsupported_claims or ()),
        "progress": {**jsonable(progress), "label": progress.label},
        "next_undecided": next_undecided(groups.reviewable, decided),
        "changes": [change_view(c) for c in groups.reviewable],
        "empty_message": empty_queue_message(state["changes"]),
        "turned_down": [{"original": c.original_text, "reason": c.reason or "did not pass the checks"}
                        for c in rejected_by_checks(state["changes"])],
        "true_gaps": [{"label": short_requirement(g), "full": g} for g in displayable_gaps(groups.true_gaps)],
        "blocked": [c.job_requirement or "an unsupported requirement" for c in groups.blocked],
        "show_all": show_all,
        "verbs": VERBS,
    }


def _run_status(owner_id: str) -> dict:
    with _RUNS_LOCK:
        data = _read_run(owner_id)
    data.pop("boot", None)
    return data


@router.get("/tailor")
def tailor_page(show_all: bool = False, ws: Workspace = Depends(workspace)):
    from resume_tailorer.llm.settings import resolve_settings

    _load_local_env()
    pending = _pending(ws)
    source = _resume_source(ws)
    run = _run_status(ws.owner_id)
    if run.get("job_id") != pending.get("job_id"):
        run = {"status": "idle"}
    try:
        resolve_settings()
        model_ready = True
    except ValueError:
        model_ready = False
    state = _review(ws, pending.get("job_id"))
    fit = (pending.get("candidate_fit") or {}).get("overall_fit")
    from resume_tailorer.tailoring_session import HANDOFF_KEY

    handoff = ws.session.get(HANDOFF_KEY) or {}
    return {
        "job": {"job_id": pending.get("job_id"), "title": pending.get("title"), "company": pending.get("company"),
                "fit": None if fit is None else round(fit)} if pending else None,
        "resume": {"label": source[2], "one_off": _one_off(ws.owner_id) is not None} if source else None,
        "model_ready": model_ready,
        "custom_api_base_allowed": not ws.owner.signed_in,
        "run": run,
        "review": _review_view(ws, state, show_all) if state else None,
        "existing": {"version": handoff.get("version"), "status": handoff.get("validation_status"),
                     "review_complete": bool(handoff.get("review_complete"))}
        if handoff and handoff.get("job_id") == pending.get("job_id") and not state else None,
    }


class RunRequest(BaseModel):
    length: Literal["preserve", "1_page", "2_page"] = "preserve"
    conservative: bool = False
    # Optional model for this run only (never stored or logged), like the Streamlit sidebar.
    model: Optional[str] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None


def _settings_for(body: RunRequest, ws: Workspace):
    """The server's model, or the user's for this run. A custom API address is allowed only in
    local mode: on a shared server it would let anyone make the server call any address."""
    from resume_tailorer.llm.settings import resolve_settings

    if body.api_base and ws.owner.signed_in:
        raise HTTPException(400, "A custom API address is only available when running Job Copilot locally.")
    return resolve_settings(model=(body.model or "").strip() or None, api_key=(body.api_key or "").strip() or None,
                            api_base=(body.api_base or "").strip() or None)


def _worker(owner, job_id: str, pending: dict, source, request: RunRequest, settings) -> None:
    """Runs on its own thread with its own workspace: the request that started it closes its
    database connections as soon as it answers."""
    ws = Workspace(owner)
    try:
        _run(ws, job_id, pending, source, request, settings)
    finally:
        ws.close()


def _run(ws: Workspace, job_id: str, pending: dict, source, request: RunRequest, settings) -> None:
    from resume_tailorer.llm.client import LLMClient
    from resume_tailorer.tailoring_service import TailoringError, regenerate, run_tailoring
    from resume_tailorer.ui.tailoring_view import safe_default_dispositions

    def step(message: str) -> None:
        with _RUNS_LOCK:
            _write_run(ws.owner_id, {**_read_run(ws.owner_id), "step": message})

    try:
        state = run_tailoring(
            ws.session, original_bytes=source[1], filename=source[0], job_description=pending.get("description") or "",
            pending=pending, llm=LLMClient(settings), target_length=LENGTHS[request.length],
            conservative=request.conservative, progress=step,
        )
        # Same first step as the Streamlit review room: changes that claim a missing
        # requirement start rejected, and the resume is rebuilt without them.
        safe = safe_default_dispositions(state["changes"], state["report"].true_gaps)
        if safe:
            state["dispositions"].update(safe)
            state["gap_blocks_applied"] = True
            regenerate(ws.session, state)
            state["reviewed"] = False
        _save_review(ws, job_id, state)
        _persist_handoff(ws, False)
        outcome = {"status": "done"}
    except TailoringError as exc:
        outcome = {"status": "failed", "error": str(exc)}
    except Exception as exc:  # never leave a run stuck as "running"
        logger.exception("Tailoring run failed for owner %s", ws.owner_id[:8])
        from app import alerts

        alerts.notify(uuid.uuid4().hex[:10], "a tailoring run", type(exc).__name__)
        outcome = {"status": "failed", "error": f"Tailoring didn't finish: {exc}. Try again."}
    with _RUNS_LOCK:
        _write_run(ws.owner_id, {**_read_run(ws.owner_id), **outcome, "finished": time.time()})


@router.post("/tailor/run")
def start_run(body: RunRequest, ws: Workspace = Depends(workspace)):
    from resume_tailorer.review_store import discard_review

    _load_local_env()
    pending = _pending(ws)
    if not pending.get("job_id"):
        raise HTTPException(409, "Choose a job in Jobs first.")
    if not (pending.get("description") or "").strip():
        raise HTTPException(409, "This job has no description to tailor against.")
    source = _resume_source(ws)
    if source is None:
        raise HTTPException(409, "Import your resume in Career Profile first.")
    try:
        settings = _settings_for(body, ws)
    except ValueError as exc:
        raise HTTPException(503, "The writing model isn't set up on this server. Enter a model and key under "
                                 "Settings to use your own.") from exc
    with _RUNS_LOCK:
        if _read_run(ws.owner_id).get("status") == "running":
            raise HTTPException(409, "A tailoring run is already in progress.")
        limits.use(ws.owner_id, "tailor")
        _write_run(ws.owner_id, {"status": "running", "step": "Starting", "job_id": pending["job_id"],
                                 "started": time.time(), "boot": BOOT_ID})
    discard_review(ws.session["artifacts_dir"], pending["job_id"])
    threading.Thread(target=_worker, args=(ws.owner, pending["job_id"], pending, source, body, settings),
                     name=f"tailor-{ws.owner_id[:8]}", daemon=True).start()
    return _run_status(ws.owner_id)


@router.get("/tailor/run")
def run_status(ws: Workspace = Depends(workspace)):
    return _run_status(ws.owner_id)


def _state_or_404(ws: Workspace) -> tuple[str, dict]:
    job_id = _pending(ws).get("job_id")
    state = _review(ws, job_id)
    if not state:
        raise HTTPException(404, "There's no tailored resume to review for this job yet.")
    return job_id, state


class Decision(BaseModel):
    change_id: str
    decision: Literal["ACCEPTED", "MANUALLY_EDITED", "REJECTED"]
    manual_text: Optional[str] = None


@router.post("/tailor/decisions")
def decide(body: Decision, ws: Workspace = Depends(workspace)):
    job_id, state = _state_or_404(ws)
    if body.change_id not in {c.change_id for c in state["changes"]}:
        raise HTTPException(404, "That change isn't in this review.")
    state.setdefault("decided", set())
    if state["dispositions"].get(body.change_id) != body.decision or body.change_id not in state["decided"]:
        state["dirty"] = True
    state["dispositions"][body.change_id] = body.decision
    state["decided"].add(body.change_id)
    if body.decision == "MANUALLY_EDITED" and body.manual_text is not None:
        state["manual_texts"][body.change_id] = body.manual_text
        state["dirty"] = True
    _save_review(ws, job_id, state)
    return _review_view(ws, state)


@router.post("/tailor/rebuild")
def rebuild(ws: Workspace = Depends(workspace)):
    from resume_tailorer.tailoring_service import TailoringError, regenerate
    from resume_tailorer.ui.tailor_progress import review_progress

    job_id, state = _state_or_404(ws)
    try:
        regenerate(ws.session, state)
    except TailoringError as exc:
        raise HTTPException(400, str(exc)) from exc
    _save_review(ws, job_id, state)
    groups = _groups(state)
    progress = review_progress(groups.reviewable, state.get("decided") or set(), state["dirty"],
                               state["report"].validation.status)
    _persist_handoff(ws, progress.can_continue)
    return _review_view(ws, state)


@router.delete("/tailor/review")
def discard(ws: Workspace = Depends(workspace)):
    from resume_tailorer.review_store import discard_review
    from resume_tailorer.tailoring_session import HANDOFF_KEY

    job_id = _pending(ws).get("job_id")
    discard_review(ws.session["artifacts_dir"], job_id)
    ws.session.pop(HANDOFF_KEY, None)
    record = ws.store().load()
    record["active_handoff"] = None
    ws.save_record(record)
    return {"discarded": True}


@router.get("/tailor/preview/{page}")
def preview_page(page: int, ws: Workspace = Depends(workspace)):
    from resume_tailorer.ui.pdf_preview import pdf_page_images

    _job_id, state = _state_or_404(ws)
    if state["report"].validation.status.value == "FAIL":
        raise HTTPException(404, "A resume that failed validation has no preview.")
    images = pdf_page_images(state.get("pdf_bytes") or b"")
    if not 1 <= page <= len(images):
        raise HTTPException(404, "No such page.")
    return Response(images[page - 1], media_type="image/png", headers={"Cache-Control": "private, max-age=60"})


@router.get("/tailor/download/{kind}")
def download(kind: Literal["pdf", "docx"], ws: Workspace = Depends(workspace)):
    _job_id, state = _state_or_404(ws)
    if state["report"].validation.status.value == "FAIL":
        raise HTTPException(409, "This resume failed validation and can't be downloaded.")
    data = state.get("pdf_bytes") if kind == "pdf" else state.get("docx_bytes")
    if not data:
        raise HTTPException(404, "That format isn't available for this resume.")
    name = (state.get("candidate_name") or "resume").replace(" ", "_")
    media = "application/pdf" if kind == "pdf" else \
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return Response(data, media_type=media,
                    headers={"Content-Disposition": f'attachment; filename="{name}_tailored_resume_v{state.get("version", 1)}.{kind}"'})


class PastedJob(BaseModel):
    title: str
    company: str = ""
    description: str
    url: str = ""


@router.post("/tailor/pasted")
def use_pasted_job(body: PastedJob, ws: Workspace = Depends(workspace)):
    """A job description the user pasted becomes a stored job, so Tailor, Apply and Tracker
    treat it like one found in Jobs."""
    import hashlib
    from datetime import datetime

    from resume_tailorer.active_job import remember
    from resume_tailorer.job_search.job_service import PENDING_TAILOR_JOB_KEY
    from resume_tailorer.job_search.models import JobPosting, JobSource

    description = body.description.strip()
    if not body.title.strip():
        raise HTTPException(400, "Add the job title.")
    if len(description.split()) < 40:
        raise HTTPException(400, "Paste the whole job description (at least a few paragraphs), so requirements can be found.")
    url = body.url.strip()
    if url and not url.lower().startswith(("http://", "https://")):
        raise HTTPException(400, "The link should start with https://")
    source_id = "pasted-" + hashlib.sha256(f"{body.title}|{body.company}|{description}".encode()).hexdigest()[:12]
    job = JobPosting(source=JobSource.COMPANY_PAGES, source_id=source_id, company=body.company.strip() or "Not stated",
                     title=body.title.strip(), location="Unknown", description=description,
                     posted_date=datetime.now(), url=url, ats_platform="Unknown")
    job_id = ws.service.db.save_job_posting(job)
    record = ws.record
    remember(record, job_id)
    ws.save_record(record)
    ws.session.pop(PENDING_TAILOR_JOB_KEY, None)
    return tailor_page(False, Workspace(ws.owner, ws.service))


@router.post("/tailor/one-off")
async def use_one_off(file: UploadFile = File(...), ws: Workspace = Depends(workspace)):
    name = file.filename or "resume"
    if not name.lower().endswith((".docx", ".pdf")):
        raise HTTPException(400, "Upload a Word (.docx) or PDF resume.")
    data = await file.read()
    if not data or len(data) > MAX_RESUME_BYTES:
        raise HTTPException(400, "That file is empty or larger than 10 MB.")
    _user_file(ws.owner_id, "tailor", "one_off.bin").write_bytes(data)
    _user_file(ws.owner_id, "tailor", "one_off.json").write_text(json.dumps({"filename": name}), encoding="utf-8")
    return {"label": f"One-off file for this job: {name}"}


@router.delete("/tailor/one-off")
def clear_one_off(ws: Workspace = Depends(workspace)):
    for part in ("one_off.json", "one_off.bin"):
        try:
            _user_file(ws.owner_id, "tailor", part).unlink()
        except OSError:
            pass
    return {"cleared": True}
