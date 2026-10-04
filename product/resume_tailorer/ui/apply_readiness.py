"""Apply readiness: what's ready, what isn't, and what each application mode can
really do. Pure. Opening the employer page is never treated as submitting.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional
from urllib.parse import urlparse

from resume_tailorer.applications.models import ApplicationStatus, ATSCapability

ASSIST_UNAVAILABLE = (
    "Not available yet. Most application forms are built in the browser, and Job Copilot "
    "can't fill them reliably. Planned with browser assist."
)


@dataclass(frozen=True)
class CheckItem:
    label: str
    state: str  # "ok", "review", "blocked", "neutral"
    detail: str


@dataclass(frozen=True)
class ModeOption:
    name: str
    available: bool
    recommended: bool
    detail: str


@dataclass(frozen=True)
class ApplyView:
    checklist: tuple[CheckItem, ...]
    can_open: bool
    can_track: bool
    can_mark_applied: bool
    stage: str  # "not_ready", "ready", "tracked", "applied"
    headline: str
    modes: tuple[ModeOption, ...]


def valid_employer_url(url: Optional[str]) -> bool:
    try:
        parsed = urlparse((url or "").strip())
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def mode_options(capability: ATSCapability) -> tuple[ModeOption, ...]:
    """Manual always works. Assist and Auto stay unavailable until a platform
    proves real end-to-end submission (decisions 012, 016; spec 006)."""
    assist = capability.assist_supported and capability.final_submission
    auto = capability.auto_supported and capability.final_submission
    return (
        ModeOption("Manual", True, True, "You apply on the employer's site with your tailored resume. Works with any employer link."),
        ModeOption("Assist", assist, False, "Fills the form for you to review." if assist else ASSIST_UNAVAILABLE),
        ModeOption("Auto", auto, False, "Submits for you after you approve." if auto else ASSIST_UNAVAILABLE),
    )


def build_apply_view(
    *,
    job: Optional[Mapping[str, Any]],
    handoff: Optional[Mapping[str, Any]],
    review_complete: bool,
    facts_confirmed: bool,
    has_profile: bool,
    approved_answers: int,
    unanswered: tuple[str, ...],
    status: Optional[ApplicationStatus],
    capability: ATSCapability,
) -> ApplyView:
    items = []
    if not job:
        items.append(CheckItem("Job", "blocked", "No job selected. Choose one in Jobs."))
    else:
        items.append(CheckItem("Job", "ok", f"{job.get('title', 'Role')} at {job.get('company', '')}"))
    url_ok = bool(job) and valid_employer_url(job.get("url"))
    items.append(CheckItem(
        "Employer application link", "ok" if url_ok else "blocked",
        "Opens the employer's own posting" if url_ok else "No valid link for this job",
    ))
    if handoff:
        validation = str(handoff.get("validation_status", "")).upper()
        state = "ok" if validation == "PASS" else "review"
        items.append(CheckItem(
            "Tailored resume", state,
            f"Version {handoff.get('version')} · {'passed validation' if state == 'ok' else 'passed with warnings to read'}",
        ))
        items.append(CheckItem(
            "Your review of the changes", "ok" if review_complete else "review",
            "Every change reviewed and rebuilt" if review_complete else "Some changes haven't been reviewed in Tailor",
        ))
    else:
        items.append(CheckItem("Tailored resume", "blocked", "No usable tailored resume for this job yet. Tailor it first."))
    items.append(CheckItem(
        "Your facts", "ok" if facts_confirmed else ("review" if has_profile else "blocked"),
        "Confirmed in Career Profile" if facts_confirmed else
        ("Not confirmed yet in Career Profile" if has_profile else "No Career Profile yet"),
    ))
    if unanswered:
        items.append(CheckItem("Application questions", "review", f"{len(unanswered)} need your answer"))
    else:
        items.append(CheckItem(
            "Application questions", "neutral",
            f"{approved_answers} saved {'answer' if approved_answers == 1 else 'answers'} ready to reuse. "
            "Any other questions are answered on the employer's site.",
        ))

    can_open = bool(job) and url_ok
    can_track = can_open and bool(handoff) and has_profile and status is None
    if status == ApplicationStatus.READY_TO_APPLY:
        stage, headline = "tracked", "Tracked as ready to apply. Finish on the employer's site, then mark it as applied."
    elif status is not None and status not in (ApplicationStatus.DISCOVERED, ApplicationStatus.INTERESTED, ApplicationStatus.PREPARING):
        stage, headline = "applied", "Marked as applied. Follow it in Tracker."
    elif can_track:
        stage, headline = "ready", "Ready. Open the employer's application and use your tailored resume."
    else:
        stage, headline = "not_ready", "Not ready yet. Resolve the items marked below."
    return ApplyView(
        checklist=tuple(items), can_open=can_open, can_track=can_track,
        can_mark_applied=stage == "tracked", stage=stage, headline=headline,
        modes=mode_options(capability),
    )


@dataclass(frozen=True)
class EmptyApplyView:
    items: tuple[tuple[str, bool], ...]
    action_label: str
    action_page: str


def empty_apply_view(has_job: bool, has_resume_for_job: bool) -> EmptyApplyView:
    """What Apply shows before anything is ready: three plain steps and the one that's next."""
    items = (
        ("Choose a real job", has_job),
        ("Review the tailored resume", has_resume_for_job),
        ("Open the employer's application", False),
    )
    if not has_job:
        return EmptyApplyView(items, "Find a job", "pages/2_Job_Search.py")
    if not has_resume_for_job:
        return EmptyApplyView(items, "Finish tailoring", "pages/5_Tailor.py")
    return EmptyApplyView(items, "Review application readiness", "pages/3_Applications.py")
