"""Pure presentation models and visual tokens for the Job Copilot UI (spec 007)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Destination:
    name: str
    path: str
    purpose: str
    icon: str


@dataclass(frozen=True)
class ProgressStep:
    """One step of a page's own progress strip. state: complete, current or pending."""

    label: str
    state: str


@dataclass(frozen=True)
class SemanticStatus:
    label: str
    tone: str
    application_ready: bool


# The six user-facing destinations, in navigation order. File routes are internal.
DESTINATIONS = (
    Destination("Home", "app.py", "What to do next", ":material/home:"),
    Destination("Career Profile", "pages/1_Profile_Review.py", "Your verified facts", ":material/badge:"),
    Destination("Jobs", "pages/2_Job_Search.py", "Find and choose real roles", ":material/work:"),
    Destination("Tailor", "pages/5_Tailor.py", "Review resume changes", ":material/edit_document:"),
    Destination("Apply", "pages/3_Applications.py", "Get ready and open the application", ":material/send:"),
    Destination("Tracker", "pages/4_Application_Tracker.py", "Follow every application", ":material/checklist:"),
)
WORKSPACES = DESTINATIONS  # older name, kept for imports

# Semantic colors. Meaning never changes between screens.
TOKENS = {
    "ink": "#172033",
    "canvas": "#F3F6FA",
    "paper": "#FFFFFF",
    "line": "#D7DEE8",
    "action": "#2457D6",
    "verified": "#167A5A",
    "review": "#A86108",
    # #A86108 is 4.4:1 on the canvas, below AA; this darker amber is used there.
    "review_on_canvas": "#9A5806",
    "blocked": "#B43A45",
    "muted": "#5D6878",
}

_STATUS_MAP = {
    "PASS": SemanticStatus("Verified", "verified", True),
    "READY": SemanticStatus("Application ready", "verified", True),
    "WARNING": SemanticStatus("Review required", "review", False),
    "REVIEW": SemanticStatus("Review required", "review", False),
    "FAIL": SemanticStatus("Blocked", "blocked", False),
    "BLOCKED": SemanticStatus("Blocked", "blocked", False),
    "PENDING": SemanticStatus("Not assessed", "neutral", False),
    "UNKNOWN": SemanticStatus("Not assessed", "neutral", False),
}

# Text symbols so status never relies on color alone.
TONE_SYMBOLS = {"verified": "✓", "review": "!", "blocked": "✕", "neutral": "–", "action": "→"}


def semantic_status(status: Any) -> SemanticStatus:
    """Map product statuses to one consistent, honest visual state."""
    key = getattr(status, "value", status)
    return _STATUS_MAP.get(str(key or "UNKNOWN").upper(), _STATUS_MAP["UNKNOWN"])


def display_optional(value: Any, empty_label: str = "Not stated") -> str:
    """Display unknown values explicitly without turning them into a numeric zero."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return empty_label
    return str(value)


def progress_steps(labels: tuple[str, ...], done: tuple[bool, ...]) -> tuple[ProgressStep, ...]:
    """Steps for a page's progress strip; the first unfinished step is current."""
    first_open = next((i for i, d in enumerate(done) if not d), None)
    return tuple(
        ProgressStep(label, "complete" if d else "current" if i == first_open else "pending")
        for i, (label, d) in enumerate(zip(labels, done))
    )
