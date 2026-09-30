"""Pure presentation models and visual tokens for the Job Copilot UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class Workspace:
    name: str
    path: str
    purpose: str


@dataclass(frozen=True)
class WorkflowStep:
    label: str
    state: str


@dataclass(frozen=True)
class SemanticStatus:
    label: str
    tone: str
    application_ready: bool


WORKSPACES = (
    Workspace("Fact Vault", "pages/1_Profile_Review.py", "Verify reusable career facts"),
    Workspace("Job Discovery", "pages/2_Job_Search.py", "Find roles and inspect fit"),
    Workspace("Tailoring Studio", "app.py", "Review evidence-backed edits"),
    Workspace("Apply Launchpad", "pages/3_Applications.py", "Stage a safe application"),
    Workspace("Application Tracker", "pages/4_Application_Tracker.py", "Track outcomes and follow-ups"),
)

WORKFLOW_LABELS = (
    "Verified facts",
    "Matched role",
    "Reviewed edits",
    "Application ready",
)

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


def semantic_status(status: Any) -> SemanticStatus:
    """Map product statuses to one consistent, honest visual state."""
    key = getattr(status, "value", status)
    return _STATUS_MAP.get(str(key or "UNKNOWN").upper(), _STATUS_MAP["UNKNOWN"])


def display_optional(value: Any, empty_label: str = "Not stated") -> str:
    """Display unknown values explicitly without turning them into a numeric zero."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return empty_label
    return str(value)


def _has_value(session: Mapping[str, Any], *keys: str) -> bool:
    return any(bool(session.get(key)) for key in keys)


def build_workflow_state(session: Mapping[str, Any]) -> tuple[WorkflowStep, ...]:
    """Build the four-stage evidence ribbon from persisted session evidence."""
    artifact = session.get("artifact_run_state") or {}
    validation = artifact.get("validation") if isinstance(artifact, Mapping) else None
    validation_value = getattr(getattr(validation, "status", validation), "value", getattr(validation, "status", validation))
    reviewed = bool(isinstance(artifact, Mapping) and artifact.get("reviewed"))
    has_artifact = bool(
        isinstance(artifact, Mapping)
        and (artifact.get("pdf_bytes") or artifact.get("docx_bytes"))
    )
    completed = (
        _has_value(session, "career_profile", "profile_data", "profile", "candidate_profile"),
        _has_value(session, "job_description_text", "selected_job", "pending_tailor_job"),
        reviewed,
        reviewed and has_artifact and str(validation_value).upper() == "PASS",
    )
    first_open = next((index for index, done in enumerate(completed) if not done), len(completed) - 1)
    return tuple(
        WorkflowStep(label, "complete" if done else "current" if index == first_open else "pending")
        for index, (label, done) in enumerate(zip(WORKFLOW_LABELS, completed))
    )


THEME_CSS = r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&display=swap');
:root {
  --jc-ink: #17202A; --jc-action: #2457D6; --jc-verified: #187A57;
  --jc-review: #B86E12; --jc-blocked: #B33A3A; --jc-canvas: #F5F7FA;
  --jc-paper: #FFFFFF; --jc-line: #D9E0E8;
}
html, body, [class*="st-"] { font-family: "Atkinson Hyperlegible", Inter, system-ui, sans-serif; color: var(--jc-ink); }
/* Streamlit draws icons with a ligature font; the rule above would turn them into words. */
[data-testid="stIconMaterial"], [data-testid="stIconMaterial"] * { font-family: "Material Symbols Rounded" !important; }
.stApp { background: var(--jc-canvas); }
[data-testid="stSidebar"] { background: var(--jc-paper); border-right: 1px solid var(--jc-line); }
[data-testid="stSidebar"] a { border-radius: 4px; }
[data-testid="stSidebar"] a:hover { background: #EEF2F7; }
input, textarea, [data-baseweb="select"] * { color: var(--jc-ink) !important; }
[data-testid="stExpander"] summary { gap: .5rem; }
[data-testid="stSidebarNav"] { display: none; }
.block-container { max-width: 1440px; padding-top: 2rem; padding-bottom: 4rem; }
h1, h2, h3 { color: var(--jc-ink); letter-spacing: -0.025em; }
h1 { font-size: clamp(2rem, 4vw, 2.6rem) !important; line-height: 1.08 !important; }
p { line-height: 1.55; }
.jc-brand { padding: .5rem 0 1rem; border-bottom: 1px solid var(--jc-line); margin-bottom: 1rem; }
.jc-brand strong { font-size: 1.2rem; letter-spacing: -.02em; }
.jc-brand span { display: block; color: #52606D !important; font-size: .82rem; margin-top: .2rem; }
.jc-page-header { border-bottom: 1px solid var(--jc-line); padding: .25rem 0 1.25rem; margin-bottom: 1.5rem; }
.jc-page-header p { max-width: 72ch; margin: .45rem 0 0; color: #52606D; }
.jc-ribbon { display: flex; gap: 0; overflow-x: auto; background: var(--jc-paper); border: 1px solid var(--jc-line); margin: 0 0 1.75rem; }
.jc-step { min-width: 10.5rem; flex: 1; padding: .75rem 1rem .75rem 1.8rem; position: relative; border-right: 1px solid var(--jc-line); font-size: .9rem; white-space: nowrap; }
.jc-step:last-child { border-right: 0; }
.jc-step::before { content: ""; width: .55rem; height: .55rem; border-radius: 50%; background: #AEB8C4; position: absolute; left: .75rem; top: 1rem; }
.jc-step.complete::before { background: var(--jc-verified); }
.jc-step.current { box-shadow: inset 0 -3px 0 var(--jc-action); font-weight: 700; }
.jc-step.current::before { background: var(--jc-action); }
.jc-panel { background: var(--jc-paper); border: 1px solid var(--jc-line); padding: 1.25rem; }
.jc-panel + .jc-panel { margin-top: 1rem; }
.jc-status { border-left: 4px solid var(--jc-line); padding: .7rem .9rem; background: var(--jc-paper); }
.jc-status.verified { border-color: var(--jc-verified); }
.jc-status.review { border-color: var(--jc-review); }
.jc-status.blocked { border-color: var(--jc-blocked); }
.jc-sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
div.stButton > button[kind="primary"] { background: var(--jc-action); border-color: var(--jc-action); border-radius: 4px; font-weight: 700; }
div.stButton > button:not([kind="primary"]) { border-radius: 4px; border-color: #AAB4C0; }
a:focus-visible, button:focus-visible, input:focus-visible, textarea:focus-visible, [tabindex]:focus-visible { outline: 3px solid #FFBF47 !important; outline-offset: 2px !important; }
@media (max-width: 780px) {
  .block-container { padding: 1rem 1rem 3rem; }
  .jc-ribbon { margin-left: -1rem; margin-right: -1rem; border-left: 0; border-right: 0; }
  .jc-step { min-width: 9.25rem; }
  div.stButton > button { width: 100%; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; scroll-behavior: auto !important; }
}
</style>
"""
