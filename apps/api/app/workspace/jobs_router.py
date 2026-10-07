"""Jobs (spec 009 phase 2): search the live boards, list with fit, detail with evidence,
save / pass / prepare. The same rules as the Streamlit Jobs page (ui/jobs_state.py,
ui/job_view.py); the last search is kept in the profile record instead of a browser
session, so it survives reloads and devices."""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.workspace import limits
from app.workspace.context import Workspace, jsonable, stamp, workspace

router = APIRouter(prefix="/v2", tags=["workspace"])

LAST_SEARCH_FIELD = "last_search"
VIEW_KEYS = {"best": "Best matches", "newest": "Newest", "saved": "Saved"}
_FIT_CACHES: dict[str, dict] = {}
_FIT_LOCK = threading.Lock()


def _fit_cache(owner_id: str) -> dict:
    with _FIT_LOCK:
        cache = _FIT_CACHES.setdefault(owner_id, {})
        if len(cache) > 5000:
            cache.clear()
        return cache


def _profile(ws: Workspace):
    from resume_tailorer.session_profile import get_career_profile

    return get_career_profile(ws.session)


def _live_sources():
    from resume_tailorer.job_search.job_attributes import (
        ASHBY_BOARDS, COMPANY_DIRECTORY, LEVER_BOARDS, SMARTRECRUITERS_BOARDS,
    )
    from resume_tailorer.job_search.models import JobSource

    return [
        (JobSource.GREENHOUSE, "Greenhouse", len(COMPANY_DIRECTORY)),
        (JobSource.LEVER, "Lever", len(LEVER_BOARDS)),
        (JobSource.ASHBY, "Ashby", len(ASHBY_BOARDS)),
        (JobSource.SMARTRECRUITERS, "SmartRecruiters", len(SMARTRECRUITERS_BOARDS)),
    ]


def _custom_boards(ws: Workspace) -> list[dict]:
    from resume_tailorer.job_search.custom_boards import boards_in

    return boards_in(ws.record)


def _boards_payload(ws: Workspace) -> list[dict]:
    from resume_tailorer.ui.search_help import board_view

    return [board_view(b) for b in _custom_boards(ws)]


def _help_texts() -> dict:
    from resume_tailorer.ui import search_help as sh

    return {"sources": sh.SOURCES_HELP, "add_board": sh.ADD_BOARD_HELP, "company_filter": sh.COMPANY_FILTER_HELP,
            "title_rule": sh.TITLE_RULE, "sponsorship": sh.SPONSORSHIP_HELP, "paste": sh.PASTE_PATH,
            "limit": sh.ADDED_BOARDS_LIMIT_TEXT}


def _goals(ws: Workspace) -> dict:
    """The search shown: the last search, else the saved goals."""
    last = (ws.record.get(LAST_SEARCH_FIELD) or {}).get("form")
    return dict(last or ws.record.get("preferences") or {})


class SearchForm(BaseModel):
    job_title: str
    location: str = ""
    remote_preference: str = "any"
    experience_level: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    min_salary: int = 0
    employment_type: list[str] = Field(default_factory=list)
    sponsorship_required: bool = False
    relocation_willing: bool = False
    target_companies: str = ""
    exclude_companies: str = ""
    # Not sent: every curated source (as before). An empty list: only the added boards (spec 013).
    sources: Optional[list[str]] = None
    # Spec 013: also search the boards this person added.
    include_custom: bool = True


@router.get("/jobs/setup")
def search_setup(ws: Workspace = Depends(workspace)):
    from resume_tailorer.job_search.job_attributes import (
        EMPLOYMENT_TYPE_OPTIONS, EXPERIENCE_LEVEL_OPTIONS, INDUSTRY_OPTIONS, LIVE_BOARD_COUNT,
    )
    from resume_tailorer.job_search.custom_boards import MAX_CUSTOM_BOARDS
    from resume_tailorer.ui import search_help as sh
    from resume_tailorer.ui.jobs_state import goals_summary_line
    from resume_tailorer.ui.onboarding import suggested_titles

    ws.service.warm_up()
    goals = _goals(ws)
    auth = ws.record.get("authorization") or {}
    form = {
        "job_title": goals.get("job_title", ""), "location": goals.get("location", ""),
        "remote_preference": goals.get("remote_preference") or "any",
        "experience_level": list(goals.get("experience_level") or []), "industries": list(goals.get("industries") or []),
        "min_salary": int(goals.get("min_salary") or 0), "employment_type": list(goals.get("employment_type") or []),
        "sponsorship_required": bool(goals.get("sponsorship_required", auth.get("sponsorship_required") is True)),
        "relocation_willing": bool(goals.get("relocation_willing")),
        "target_companies": goals.get("target_companies") or "", "exclude_companies": goals.get("exclude_companies") or "",
        "sources": list((ws.record.get(LAST_SEARCH_FIELD) or {}).get("sources", [s.value for s, _, _ in _live_sources()])),
        "include_custom": bool((ws.record.get(LAST_SEARCH_FIELD) or {}).get("include_custom", True)),
    }
    last = ws.record.get(LAST_SEARCH_FIELD) or {}
    boards = _custom_boards(ws)
    return {
        "form": form,
        "has_goals": bool(form["job_title"]),
        "searched": bool(last),
        "summary_line": goals_summary_line(goals) if form["job_title"] else "",
        "suggested_titles": suggested_titles((ws.record.get("profile") or {})),
        # Boards the form's current choices would search (spec 013); the page recounts as they change.
        "board_count": sh.boards_in_scope(form["sources"], boards, form["include_custom"]),
        "all_curated_count": LIVE_BOARD_COUNT,
        "custom_boards": _boards_payload(ws),
        "max_custom_boards": MAX_CUSTOM_BOARDS,
        "help": _help_texts(),
        "saved_count": len(ws.service.db.get_jobs_by_latest_action("save", limit=100)),
        "options": {
            "experience_levels": EXPERIENCE_LEVEL_OPTIONS, "industries": INDUSTRY_OPTIONS,
            "employment_types": EMPLOYMENT_TYPE_OPTIONS,
            "work_modes": [{"value": "any", "label": "No preference"}, {"value": "remote", "label": "Remote"},
                           {"value": "hybrid", "label": "Hybrid"}, {"value": "onsite", "label": "On-site"}],
            "sources": [{"value": s.value, "label": sh.source_label(s.value), "curated_count": count}
                        for s, _, count in _live_sources()],
        },
    }


@router.post("/jobs/search")
def search(body: SearchForm, ws: Workspace = Depends(workspace)):
    from resume_tailorer.job_search.models import JobSource
    from resume_tailorer.job_search.ui_helpers import build_search_goals_from_form
    from resume_tailorer.ui.onboarding import form_to_goals, save_goals

    from resume_tailorer.job_search.custom_boards import record_search_results

    form = body.model_dump()
    include_custom = form.pop("include_custom")
    sources_raw = form.pop("sources")
    if sources_raw is None:
        sources_raw = [s.value for s, _, _ in _live_sources()]
    live = {s.value for s, _, _ in _live_sources()}
    sources = [JobSource(v) for v in sources_raw if v in live]
    boards = _custom_boards(ws) if include_custom else []
    if not form["job_title"].strip():
        raise HTTPException(400, "Add a target role to search, for example “Product marketing manager”.")
    if not sources and not boards:
        raise HTTPException(400, "Choose at least one source.")
    limits.use(ws.owner_id, "search")
    form["job_title"] = form["job_title"].strip()
    form["max_salary"] = 0
    try:
        goals = build_search_goals_from_form(form)
    except ValueError as exc:
        raise HTTPException(400, f"Check your search: {exc}") from exc
    try:
        summary = ws.service.search_and_store(goals, sources, custom_boards=boards)
    except Exception as exc:
        raise HTTPException(502, f"The search didn't finish: {exc}. Your previous results are still here; try again.") from exc
    record = ws.record
    if record.get("profile"):
        save_goals(record, form_to_goals(form))
    record[LAST_SEARCH_FIELD] = {
        "form": form, "sources": [s.value for s in sources], "include_custom": include_custom,
        "started_at": stamp(summary.started_at),
        "providers": [{"source": p.source.value, "status": p.status.value, "scraped": p.scraped,
                       "note": p.error} for p in summary.providers],
        "boards_searched": summary.boards_searched, "boards_failed": summary.boards_failed,
        "custom_board_results": summary.custom_board_results,
    }
    record_search_results(record, summary.custom_board_results, stamp(summary.started_at))
    ws.save_record(record)
    return list_jobs("best", 0, 50, ws)


@router.get("/jobs")
def list_jobs(view: Literal["best", "newest", "saved"] = "best", offset: int = 0, limit: int = 50,
              ws: Workspace = Depends(workspace)):
    from resume_tailorer.job_search.custom_boards import added_board_keys, industry_labels
    from resume_tailorer.job_search.ui_helpers import build_search_goals_from_form
    from resume_tailorer.ui import search_help as sh
    from resume_tailorer.ui.job_view import build_row, job_id_for
    from resume_tailorer.ui.jobs_state import JobsInputs, goals_summary_line, order_jobs, resolve

    view_name = VIEW_KEYS[view]
    service = ws.service
    last = ws.record.get(LAST_SEARCH_FIELD) or {}
    boards = _custom_boards(ws)
    labels = industry_labels(boards)
    started = datetime.fromisoformat(last["started_at"]) if last.get("started_at") else None

    def matching(form: dict) -> list:
        return service.get_available_jobs(build_search_goals_from_form(dict(form, max_salary=0)),
                                          seen_since=started, industry_labels=labels)

    if view == "saved":
        jobs = service.db.get_jobs_by_latest_action("save", limit=100)
    elif last.get("form"):
        jobs = matching(last["form"])
    else:
        jobs = []
    ids_all = [job_id_for(j) for j in jobs]
    actions = service.db.get_latest_actions(ids_all) if ids_all else {}
    profile = _profile(ws)
    fits = service.fit_results_cached(profile, jobs, _fit_cache(ws.owner_id)) if profile and jobs else {}
    jobs = order_jobs(jobs, view_name, {k: (r.overall_fit if r else None) for k, r in fits.items()}, actions, job_id_for)
    statuses = tuple((p["source"], p["status"]) for p in last.get("providers") or [])
    state = resolve(JobsInputs(
        has_goals=bool(_goals(ws).get("job_title")), searched=bool(last), search_requested=False,
        result_ids=tuple(job_id_for(j) for j in jobs), selected_id=None, view=view_name,
        provider_statuses=() if view == "saved" else statuses,
    ))
    searched = view != "saved" and bool(last.get("form"))
    form = last.get("form") or {}
    added = added_board_keys(boards)
    sponsorship_needed = bool(form.get("sponsorship_required")) and view != "saved"
    return {
        "view": view,
        "state": state.state.value,
        "partial_failure": state.partial_failure,
        "source_note": state.source_note,
        "summary_line": goals_summary_line(_goals(ws)),
        # ISO time; the browser shows it in the user's own time zone.
        "searched_at": stamp(started) if started and view != "saved" else None,
        "coverage_notes": [p["note"] for p in last.get("providers") or [] if p.get("note")] if view != "saved" else [],
        # One page at a time: a broad search can match hundreds of roles.
        "total": len(jobs),
        "offset": max(0, offset),
        "rows": [jsonable(build_row(j, fits.get(job_id_for(j)), actions.get(job_id_for(j)),
                                    added_keys=added, sponsorship_needed=sponsorship_needed))
                 for j in jobs[max(0, offset): max(0, offset) + max(1, min(limit, 200))]],
        # Spec 013: what was searched, which added boards failed, and why results may be few.
        "boards_line": sh.search_result_line(
            int(last.get("boards_searched") or 0), int(last.get("boards_failed") or 0),
            sh.failed_added_boards(boards, last.get("custom_board_results") or {})) if searched else "",
        "failed_boards": sh.failed_added_boards(boards, last.get("custom_board_results") or {}) if searched else [],
        "narrowing": sh.narrowing(form, len(jobs), lambda f: len(matching(f))) if searched else [],
        "broader_titles": sh.broader_titles(form.get("job_title", "")) if searched and len(jobs) < sh.FEW_RESULTS else [],
        "company_notes": sh.unknown_company_notes(form.get("target_companies", ""), last.get("sources") or [],
                                                  boards if last.get("include_custom", True) else []) if searched else [],
        "help": _help_texts(),
    }


class NewBoard(BaseModel):
    url: str = Field(max_length=2000)
    name: str = Field(default="", max_length=80)
    industry: str = ""


_BOARD_STATUS = {"link": 400, "duplicate": 409, "curated": 409, "limit": 409,
                 "not_found": 422, "unconfirmed": 422, "unreachable": 502}


@router.get("/boards")
def list_boards(ws: Workspace = Depends(workspace)):
    from resume_tailorer.job_search.custom_boards import MAX_CUSTOM_BOARDS

    return {
        "curated": [{"value": s.value, "label": name, "count": count} for s, name, count in _live_sources()],
        "custom_boards": _boards_payload(ws),
        "max_custom_boards": MAX_CUSTOM_BOARDS,
        "help": _help_texts(),
    }


@router.post("/boards")
def add_company_board(body: NewBoard, ws: Workspace = Depends(workspace)):
    """Spec 013: verify a pasted public career board with its platform, then save it for this person."""
    from resume_tailorer.job_search.board_links import LinkProblem, parse_board_link
    from resume_tailorer.job_search.custom_boards import add_board, precheck
    from resume_tailorer.ui.search_help import board_view

    record = ws.record
    ref = parse_board_link(body.url)
    if isinstance(ref, LinkProblem):
        raise HTTPException(400, ref.message)
    refused = precheck(record, ref)
    if refused is not None:
        raise HTTPException(_BOARD_STATUS[refused.code], refused.message)
    limits.use(ws.owner_id, "boards")  # counts only checks that reach the platform
    result = add_board(record, body.url, name=body.name, industry=body.industry)
    if not result.ok:
        raise HTTPException(_BOARD_STATUS.get(result.code, 400), result.message)
    ws.save_record(record)
    return {"message": result.message, "board": board_view(result.board), "custom_boards": _boards_payload(ws)}


@router.delete("/boards/{board_id}")
def remove_company_board(board_id: str, ws: Workspace = Depends(workspace)):
    """Removes the board only; jobs, triage and applications from it stay."""
    from resume_tailorer.job_search.custom_boards import remove_board

    record = ws.record
    if not remove_board(record, board_id):
        raise HTTPException(404, "That board isn't in your list.")
    ws.save_record(record)
    return {"custom_boards": _boards_payload(ws)}


@router.get("/jobs/{job_id}")
def job_detail(job_id: str, ws: Workspace = Depends(workspace)):
    from resume_tailorer.analyzers.ats_keywords import check_keywords, profile_text
    from resume_tailorer.ui import ats_explainer
    from resume_tailorer.job_search.job_quality import evaluate_job_quality
    from resume_tailorer.ui.job_view import build_detail

    job = ws.service.db.get_job_posting(job_id)
    if job is None:
        raise HTTPException(404, "That job is no longer stored. Search again.")
    action = ws.service.db.get_latest_actions([job_id]).get(job_id)
    profile = _profile(ws)
    fit = ws.service.fit_results_cached(profile, [job], _fit_cache(ws.owner_id)).get(job_id) if profile else None
    keywords = None
    requirements = None
    review = None
    if profile is not None:
        check = check_keywords(job.title + " " + (job.description or ""), profile_text(profile))
        keywords = {"summary": check.summary, "present": list(check.present), "missing": list(check.missing)}
        if (job.description or "").strip():
            # Spec 010/011: the requirement review drives the evidence lists, so Jobs and Tailor agree.
            from resume_tailorer.analyzers.job_analyzer import JobAnalyzer
            from resume_tailorer.analyzers.requirement_review import build_review

            review = build_review(JobAnalyzer().analyze(job.description), profile,
                                  provenance=ws.record.get("provenance"), posting=job.description)
            requirements = {"summary": review.summary, "rows": len(review.rows)}
    from resume_tailorer.job_search.custom_boards import added_board_keys, industry_labels

    boards = _custom_boards(ws)
    detail = build_detail(job, fit, action, ws.record.get("authorization"), evaluate_job_quality(job), review=review,
                          added_keys=added_board_keys(boards), industry_labels=industry_labels(boards))
    return {
        **jsonable(detail),
        "fit_measured": fit is not None and fit.overall_fit is not None,
        "keywords": keywords,
        "requirements": requirements,
        "ats_explainer": ats_explainer.as_dict(),
        "description": (job.description or "").strip() or "This posting has no description.",
        "active": (ws.record.get("active_job_id") == job_id),
    }


class JobAction(BaseModel):
    action: Literal["save", "pass", "apply"]


@router.post("/jobs/{job_id}/action")
def job_action(job_id: str, body: JobAction, ws: Workspace = Depends(workspace)):
    from resume_tailorer.active_job import remember
    from resume_tailorer.job_search.job_service import build_tailor_snapshot
    from resume_tailorer.job_search.models import UserSelection
    from resume_tailorer.ui.job_view import source_text

    job = ws.service.db.get_job_posting(job_id)
    if job is None:
        raise HTTPException(404, "That job is no longer stored. Search again.")
    if body.action == "apply" and source_text(job)[1]:
        raise HTTPException(400, "Demo listings aren't real jobs.")
    ws.service.db.record_user_selection(UserSelection(job_posting_id=job_id, action=body.action))
    result: dict[str, Any] = {"action": body.action}
    if body.action == "apply":
        profile = _profile(ws)
        fit = ws.service.fit_results_cached(profile, [job], _fit_cache(ws.owner_id)).get(job_id) if profile else None
        build_tailor_snapshot(job, fit)  # validates the job can be handed to Tailor
        record = ws.record
        remember(record, job_id)
        ws.save_record(record)
        result["next"] = "/tailor"
    return result
