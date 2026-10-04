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


THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&display=swap');
:root {
  --jc-ink: #172033; --jc-canvas: #F3F6FA; --jc-paper: #FFFFFF; --jc-line: #D7DEE8;
  --jc-action: #2457D6; --jc-verified: #167A5A; --jc-review: #A86108; --jc-review-canvas: #9A5806;
  --jc-blocked: #B43A45; --jc-muted: #5D6878;
}
html, body, [class*="st-"] { font-family: "Atkinson Hyperlegible", Inter, system-ui, sans-serif; color: var(--jc-ink); }
/* Streamlit draws icons with a ligature font; the rule above would turn them into words. */
[data-testid="stIconMaterial"], [data-testid="stIconMaterial"] * { font-family: "Material Symbols Rounded" !important; }
.stApp { background: var(--jc-canvas); }
[data-testid="stSidebar"] { background: var(--jc-paper); border-right: 1px solid var(--jc-line); }
@media (min-width: 781px) {
  [data-testid="stSidebar"] { width: 240px !important; min-width: 240px !important; }
  /* Tailor: keep the resume preview in view while reviewing changes. */
  div[data-testid="stColumn"]:has(.jc-sticky-marker) { position: sticky; top: 3.75rem; align-self: flex-start; max-height: calc(100vh - 4.5rem); overflow-y: auto; }
}
[data-testid="stSidebarNav"] { display: none; }
[data-testid="stSidebar"] a { border-radius: 4px; }
[data-testid="stSidebar"] a:hover { background: #EEF2F7; }
input, textarea, [data-baseweb="select"] * { color: var(--jc-ink) !important; }
.block-container { max-width: 1500px; padding-top: 2rem; padding-bottom: 4rem; }
h1, h2, h3, h4 { color: var(--jc-ink); letter-spacing: -0.02em; }
h1 { font-size: clamp(2.25rem, 3.4vw, 2.75rem) !important; line-height: 1.08 !important; }
h2 { font-size: clamp(1.375rem, 2.2vw, 1.75rem) !important; }
h3 { font-size: clamp(1.0625rem, 1.6vw, 1.25rem) !important; }
p, li { font-size: 1rem; line-height: 1.55; }
.jc-muted, .jc-meta { color: var(--jc-muted); }
.jc-meta { font-size: .875rem; }
.jc-brand { padding: .25rem 0 .75rem; border-bottom: 1px solid var(--jc-line); margin-bottom: .75rem; }
.jc-brand strong { font-size: 1.15rem; letter-spacing: -.02em; }
.jc-brand span { display: block; color: var(--jc-muted) !important; font-size: .8rem; margin-top: .15rem; }
.jc-rail-block { border-top: 1px solid var(--jc-line); padding-top: .6rem; margin-top: .6rem; font-size: .85rem; }
.jc-rail-block strong { display: block; font-size: .78rem; color: var(--jc-muted); font-weight: 700; margin-bottom: .15rem; }
.jc-page-header { border-bottom: 1px solid var(--jc-line); padding: .25rem 0 1rem; margin-bottom: 1.25rem; }
.jc-page-header p { max-width: 72ch; margin: .4rem 0 0; color: var(--jc-muted); }
.jc-progress { display: flex; gap: 0; overflow-x: auto; background: var(--jc-paper); border: 1px solid var(--jc-line); margin: 0 0 1.5rem; }
.jc-step { min-width: 9.5rem; flex: 1; padding: .65rem 1rem .65rem 1.8rem; position: relative; border-right: 1px solid var(--jc-line); font-size: .875rem; white-space: nowrap; color: var(--jc-muted); }
.jc-step:last-child { border-right: 0; }
.jc-step::before { content: ""; width: .55rem; height: .55rem; border-radius: 50%; background: #AEB8C4; position: absolute; left: .75rem; top: .95rem; }
.jc-step.complete { color: var(--jc-ink); }
.jc-step.complete::before { background: var(--jc-verified); }
.jc-step.current { color: var(--jc-ink); box-shadow: inset 0 -3px 0 var(--jc-action); font-weight: 700; }
.jc-step.current::before { background: var(--jc-action); }
.jc-panel { background: var(--jc-paper); border: 1px solid var(--jc-line); padding: 1.1rem 1.25rem; height: 100%; }
.jc-panel h3, .jc-panel h4 { margin-top: 0; }
.jc-panel p { margin-bottom: 0; }
.jc-focus { margin-bottom: .9rem; background: var(--jc-paper); border: 1px solid var(--jc-line); border-left: 4px solid var(--jc-action); padding: 1.25rem 1.5rem; box-shadow: 0 2px 10px rgba(23,32,51,.06); }
.jc-focus h2 { margin: .1rem 0 .4rem; }
.jc-focus .jc-value { color: var(--jc-muted); margin: 0 0 .25rem; }
.jc-eyebrow { font-size: .875rem; color: var(--jc-muted); font-weight: 700; }
.jc-status { border-left: 4px solid var(--jc-line); padding: .65rem .9rem; background: var(--jc-paper); }
.jc-status.verified { border-color: var(--jc-verified); }
.jc-status.review { border-color: var(--jc-review); }
.jc-status.blocked { border-color: var(--jc-blocked); }
.jc-chip { display: inline-block; font-size: .8rem; line-height: 1.2; padding: .15rem .45rem; border: 1px solid var(--jc-line); border-radius: 3px; background: var(--jc-paper); margin: 0 .25rem .25rem 0; white-space: nowrap; }
.jc-chip.verified { color: var(--jc-verified); border-color: var(--jc-verified); }
.jc-chip.review { color: var(--jc-review); border-color: var(--jc-review); }
.jc-chip.blocked { color: var(--jc-blocked); border-color: var(--jc-blocked); }
.jc-chip.action { color: var(--jc-action); border-color: var(--jc-action); }
.jc-chain { display: grid; grid-template-columns: 1fr auto 1fr auto 1fr; gap: .5rem; align-items: stretch; margin: .5rem 0 .75rem; }
.jc-chain > div:not(.jc-arrow) { background: var(--jc-paper); border: 1px solid var(--jc-line); padding: .55rem .7rem; font-size: .9rem; }
.jc-chain small { display: block; color: var(--jc-muted); font-size: .78rem; font-weight: 700; margin-bottom: .15rem; }
.jc-arrow { align-self: center; color: var(--jc-muted); font-weight: 700; }
.jc-row { border-bottom: 1px solid var(--jc-line); padding: .55rem 0; }
.jc-row strong { font-size: 1rem; }
.jc-milestone { display: flex; gap: .75rem; align-items: baseline; padding: .55rem 0; border-bottom: 1px solid var(--jc-line); }
.jc-milestone .jc-mark { width: 1.4rem; text-align: center; font-weight: 700; }
.jc-milestone.complete .jc-mark { color: var(--jc-verified); }
.jc-milestone.current { font-weight: 700; }
.jc-milestone.current .jc-mark { color: var(--jc-action); }
.jc-milestone.pending { color: var(--jc-muted); }
.jc-table { width: 100%; border-collapse: collapse; background: var(--jc-paper); }
.jc-table th, .jc-table td { text-align: left; padding: .45rem .6rem; border-bottom: 1px solid var(--jc-line); vertical-align: top; font-size: .95rem; }
.jc-sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
div.stButton > button[kind="primary"], button[data-testid="stBaseButton-primary"],
button[data-testid="stBaseButton-primaryFormSubmit"], a[data-testid="stBaseLinkButton-primary"] { background: var(--jc-action); border-color: var(--jc-action); border-radius: 4px; font-weight: 700; }
button[data-testid="stBaseButton-primary"], button[data-testid="stBaseButton-primary"] *,
button[data-testid="stBaseButton-primaryFormSubmit"], button[data-testid="stBaseButton-primaryFormSubmit"] *,
a[data-testid="stBaseLinkButton-primary"], a[data-testid="stBaseLinkButton-primary"] * { color: #FFFFFF !important; }
[data-testid="stHeaderActionElements"] { display: none !important; }
button:disabled, button[disabled] { opacity: .45 !important; cursor: not-allowed !important; }
div.stButton > button:not([kind="primary"]) { border-radius: 4px; border-color: #AAB4C0; }
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 4px; }
a:focus-visible, button:focus-visible, input:focus-visible, textarea:focus-visible, [tabindex]:focus-visible { outline: 3px solid #FFBF47 !important; outline-offset: 2px !important; }
/* --- spec 008: work-page composition --- */
.jc-page-header { padding: 0 0 .75rem; margin-bottom: 1rem; }
.jc-page-header h1 { font-size: clamp(1.75rem, 2.4vw, 2.125rem) !important; margin: 0; }
.jc-page-header p { margin-top: .25rem; }
.jc-status.action { border-color: var(--jc-action); }
.jc-search-summary { font-size: 1.125rem; font-weight: 700; color: var(--jc-ink); }
.jc-warn-line { color: var(--jc-review-canvas); font-size: .9rem; }
.jc-card-title { font-size: 1.375rem !important; margin: 0 0 .15rem; }
.jc-aside { padding: .25rem 0 0 0; border-left: 3px solid var(--jc-line); padding-left: 1rem; }
.jc-aside h3 { font-size: 1rem !important; margin: 0 0 .4rem; }
.jc-aside p { color: var(--jc-muted); font-size: .95rem; }
.jc-detail-title { font-size: clamp(1.4rem, 2vw, 1.75rem) !important; margin: 0 0 .2rem; line-height: 1.2; }
.jc-chiprow { margin: .55rem 0 .65rem; }
.jc-sec { font-size: 1.05rem !important; margin: 1.25rem 0 .35rem !important; padding-top: .9rem; border-top: 1px solid var(--jc-line); }
.jc-ev-group { font-size: .8rem; font-weight: 700; color: var(--jc-muted); margin: .7rem 0 .2rem; letter-spacing: .01em; }
.jc-ev { display: grid; grid-template-columns: 1.4rem 1fr; gap: .35rem; padding: .3rem 0; font-size: .95rem; }
.jc-ev-mark { font-weight: 700; text-align: center; color: var(--jc-muted); }
.jc-ev-mark.verified { color: var(--jc-verified); }
.jc-ev-mark.review { color: var(--jc-review); }
.jc-ev-mark.blocked { color: var(--jc-blocked); }
/* Selectable result rows: one radio group styled as a list. */
.st-key-joblist { background: var(--jc-paper); border: 1px solid var(--jc-line) !important; border-radius: 4px; }
.st-key-joblist [role="radiogroup"] { gap: 0 !important; width: 100%; }
.st-key-joblist [role="radiogroup"] > label { width: 100%; margin: 0 !important; padding: .65rem .8rem .65rem .7rem !important;
  border-bottom: 1px solid var(--jc-line); border-left: 4px solid transparent; cursor: pointer; align-items: flex-start; }
.st-key-joblist [role="radiogroup"] > label:hover { background: #F6F8FC; }
.st-key-joblist [role="radiogroup"] > label:has(input:checked) { border-left-color: var(--jc-action); background: #EAF0FC; }
.st-key-joblist [role="radiogroup"] > label > div:first-child { display: none; }
.st-key-joblist [role="radiogroup"] > label p { font-weight: 700; font-size: .98rem; margin: 0; }
.st-key-joblist [role="radiogroup"] > label [data-testid="stCaptionContainer"] p,
.st-key-joblist [role="radiogroup"] > label small { font-weight: 400; color: var(--jc-muted); font-size: .84rem; }
.st-key-jobdetail { background: var(--jc-paper); border: 1px solid var(--jc-line); border-radius: 4px; padding: 1.1rem 1.25rem; }
.jc-rail-status { font-size: .82rem; border: 1px solid var(--jc-line); border-radius: 4px; padding: .45rem .6rem; background: #FBFAF3; }
.jc-rail-status summary { cursor: pointer; font-weight: 700; }
.jc-rail-status p { margin: .35rem 0 0; color: var(--jc-muted); font-size: .8rem; line-height: 1.4; }
.jc-check { display: grid; grid-template-columns: 1fr auto; gap: .5rem; padding: .55rem 0; border-bottom: 1px solid var(--jc-line); align-items: center; }
.jc-check:last-child { border-bottom: 0; }
.jc-srow { display: grid; grid-template-columns: 1.4fr 1fr; gap: .5rem; align-items: center; padding: .55rem 0; border-bottom: 1px solid var(--jc-line); }
@keyframes jc-confirm { from { background: #E7F3EE; } to { background: transparent; } }
.jc-confirmed { animation: jc-confirm 1.2s ease-out 1; }
@media (max-width: 780px) {
  .block-container { padding: 1rem 1rem 3rem; }
  .jc-progress { margin-left: -1rem; margin-right: -1rem; border-left: 0; border-right: 0; }
  .jc-step { min-width: 8.75rem; }
  .jc-chain { grid-template-columns: 1fr; }
  .jc-arrow { transform: rotate(90deg); justify-self: start; }
  div.stButton > button, a[data-testid^="stBaseLinkButton"] { width: 100%; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; scroll-behavior: auto !important; }
}
</style>
"""
