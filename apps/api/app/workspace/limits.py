"""Usage limits per person (decision 030): tailoring spends the model key, searches load every
job board, imports parse files. Counts live in the user's folder, so they hold across restarts.
Limits come from settings (TAILOR_RUNS_PER_DAY, SEARCHES_PER_HOUR, IMPORTS_PER_DAY,
BOARD_CHECKS_PER_DAY); 0 turns a limit off."""

from __future__ import annotations

import json
import threading
import time

from fastapi import HTTPException

from app.config import get_settings

_LOCK = threading.Lock()
WINDOWS = {"tailor": 24 * 3600, "search": 3600, "import": 24 * 3600, "boards": 24 * 3600}
WORDS = {"tailor": ("tailoring runs", "today"), "search": ("searches", "this hour"), "import": ("resume imports", "today"),
         "boards": ("career-board checks", "today")}


def _limit(kind: str) -> int:
    settings = get_settings()
    return {"tailor": settings.tailor_runs_per_day, "search": settings.searches_per_hour,
            "import": settings.imports_per_day, "boards": settings.board_checks_per_day}[kind]


def use(owner_id: str, kind: str, now: float | None = None) -> None:
    """Count one use, or refuse with 429 when the limit for the window is reached."""
    from resume_tailorer.identity import user_dir

    limit = _limit(kind)
    if limit <= 0:
        return
    now = time.time() if now is None else now
    path = user_dir(owner_id) / "limits.json"
    with _LOCK:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        recent = [t for t in data.get(kind, []) if now - t < WINDOWS[kind]]
        if len(recent) >= limit:
            minutes = max(1, round((WINDOWS[kind] - (now - min(recent))) / 60))
            wait = f"{minutes} minutes" if minutes < 120 else f"{round(minutes / 60)} hours"
            noun, window = WORDS[kind]
            raise HTTPException(429, f"You've reached the limit of {limit} {noun} {window}. Try again in about {wait}.")
        data[kind] = recent + [now]
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        tmp.replace(path)
