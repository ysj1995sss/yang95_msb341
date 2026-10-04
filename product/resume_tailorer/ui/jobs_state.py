"""Jobs presentation state (spec 008). Pure: no Streamlit import.

The page asks this module what to show. It never infers "goals exist" from
widget state, which Streamlit deletes when the user leaves the page; goals
come from the saved Career Profile or from the last search this session.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Iterable, Mapping, Optional, Sequence


class JobsState(str, Enum):
    NO_GOALS = "no_goals"
    READY_TO_SEARCH = "ready_to_search"
    SEARCHING = "searching"
    RESULTS = "results"
    DETAIL_SELECTED = "detail_selected"
    NO_RESULTS = "no_results"
    SAVED = "saved"


BEST = "Best matches"
NEWEST = "Newest"
SAVED_VIEW = "Saved"
VIEWS = (BEST, NEWEST, SAVED_VIEW)

SOURCE_NAMES = {"greenhouse": "Greenhouse", "lever": "Lever", "ashby": "Ashby",
                "linkedin": "LinkedIn (demo)", "indeed": "Indeed (demo)", "handshake": "Handshake (demo)"}


@dataclass(frozen=True)
class JobsInputs:
    has_goals: bool
    searched: bool  # a search finished this session
    search_requested: bool  # the user asked for a search on this run
    result_ids: tuple[str, ...]  # ids in the current view, in display order
    selected_id: Optional[str]
    view: str = BEST
    provider_statuses: tuple[tuple[str, str], ...] = ()  # (source, ok|partial|failed|skipped)


@dataclass(frozen=True)
class JobsView:
    state: JobsState
    selected_id: Optional[str]
    partial_failure: bool
    source_note: str
    show_workspace: bool  # list and detail regions
    show_setup: bool  # the full search card instead of a summary


def resolve_selection(selected: Optional[str], ids: Sequence[str]) -> Optional[str]:
    """Keep the selection while it's still listed; otherwise the first row."""
    if selected in ids:
        return selected
    return ids[0] if ids else None


def source_note(statuses: Iterable[tuple[str, str]]) -> tuple[bool, str]:
    """(partial failure?, plain sentence about which sources answered)."""
    statuses = [(SOURCE_NAMES.get(src, src.title()), st) for src, st in statuses]
    ok = [name for name, st in statuses if st in ("ok", "partial")]
    failed = [name for name, st in statuses if st == "failed"]
    if not statuses:
        return False, ""
    if not ok:
        return False, "No source responded. Check your connection and search again."
    note = "Searched " + ", ".join(ok)
    if failed:
        note += f" · {', '.join(failed)} didn't respond, so results may be incomplete"
    return bool(failed), note


def resolve(inputs: JobsInputs) -> JobsView:
    partial, note = source_note(inputs.provider_statuses)
    selected = resolve_selection(inputs.selected_id, inputs.result_ids)
    has_rows = bool(inputs.result_ids)

    if inputs.view == SAVED_VIEW and not inputs.search_requested:
        state = JobsState.SAVED
        return JobsView(state, selected, False, "", True, False)
    if inputs.search_requested:
        return JobsView(JobsState.SEARCHING, selected, partial, note, inputs.searched and has_rows,
                        not inputs.has_goals and not inputs.searched)
    if not inputs.searched:
        state = JobsState.READY_TO_SEARCH if inputs.has_goals else JobsState.NO_GOALS
        return JobsView(state, None, False, "", False, state is JobsState.NO_GOALS)
    if not has_rows:
        return JobsView(JobsState.NO_RESULTS, None, partial, note, False, False)
    state = JobsState.DETAIL_SELECTED if selected else JobsState.RESULTS
    return JobsView(state, selected, partial, note, True, False)


def _money(value: Any) -> str:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return ""
    return f"${value // 1000}k+" if value >= 1000 else f"${value}+"


def goals_summary_line(goals: Mapping[str, Any]) -> str:
    """'Product marketing manager roles · Denver or remote · Mid-level · $90k+'."""
    title = (goals.get("job_title") or "").strip()
    parts = [f"{title} roles" if title else "Any role"]
    location = (goals.get("location") or "").strip()
    mode = goals.get("remote_preference") or "any"
    if location and mode == "remote":
        parts.append(f"{location} or remote")
    elif location:
        parts.append(location + (f" · {mode}" if mode in ("hybrid", "onsite") else ""))
    elif mode != "any":
        parts.append({"remote": "Remote", "hybrid": "Hybrid", "onsite": "On-site"}.get(mode, mode))
    else:
        parts.append("Anywhere")
    levels = goals.get("experience_level") or []
    if levels:
        parts.append(", ".join(levels))
    if goals.get("min_salary"):
        parts.append(_money(goals["min_salary"]))
    return " · ".join(parts)


def order_jobs(jobs: Sequence[Any], view: str, fit_by_id: Mapping[str, Optional[float]],
               actions: Mapping[str, Optional[str]], id_of) -> list:
    """Best matches: highest fit first, unassessed after, passed last.
    Newest: most recently posted first, passed last."""
    def passed(job) -> bool:
        return str(actions.get(id_of(job)) or "").lower() == "pass"

    if view == NEWEST:
        def key(job):
            posted = getattr(job, "posted_date", None)
            ts = posted.timestamp() if isinstance(posted, datetime) else float("-inf")
            return (passed(job), -ts)
    else:
        def key(job):
            fit = fit_by_id.get(id_of(job))
            return (passed(job), fit is None, -(fit or 0))
    return sorted(jobs, key=key)


def searched_at_text(started: Optional[datetime]) -> str:
    if not started:
        return ""
    return "searched " + started.strftime("%I:%M %p").lstrip("0")
