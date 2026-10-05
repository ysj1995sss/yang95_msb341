"""Home: a readiness checklist (setup) or a command center (returning), and the one next best action.

Setup items can be completed in any order, so they are a checklist with
Ready / Needs attention / Not started, never a numbered sequence (spec 008).

Pure. The Home page gathers plain facts into HomeInputs; everything shown is
derived here and tested without Streamlit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from resume_tailorer.ui.profile_readiness import ProfileReadiness
from resume_tailorer.job_search.job_attributes import LIVE_BOARD_COUNT

PROFILE_PAGE = "pages/1_Profile_Review.py"
JOBS_PAGE = "pages/2_Job_Search.py"
TAILOR_PAGE = "pages/5_Tailor.py"
APPLY_PAGE = "pages/3_Applications.py"
TRACKER_PAGE = "pages/4_Application_Tracker.py"

CHECKLIST = (
    "Resume imported",
    "Facts confirmed",
    "Job goals set",
    "A role chosen",
    "An application tracked",
)
READY, ATTENTION, NOT_STARTED = "ready", "attention", "not_started"
STATE_LABELS = {READY: "Ready", ATTENTION: "Needs attention", NOT_STARTED: "Not started"}


@dataclass(frozen=True)
class ChecklistEntry:
    label: str
    state: str
    detail: str = ""


@dataclass(frozen=True)
class Item:
    title: str
    detail: str = ""
    page: str = ""


@dataclass(frozen=True)
class HomeInputs:
    readiness: ProfileReadiness
    goals_set: bool
    role_chosen: bool
    application_prepared: bool
    active_job: Optional[Item] = None
    artifact_status: Optional[str] = None  # PASS / WARNING / FAIL for the active job's resume
    artifact_reviewed: bool = False
    handoff_ready: bool = False
    saved_jobs: tuple[Item, ...] = ()
    ready_to_finish: tuple[Item, ...] = ()
    followups_due: tuple[Item, ...] = ()
    searched_this_week: bool = False


@dataclass(frozen=True)
class NextAction:
    title: str
    why: str
    value: str
    label: str
    page: str = ""
    inline: str = ""  # "upload" or "goals": done on Home itself


@dataclass(frozen=True)
class HomeView:
    mode: str  # "first_time" or "returning"
    checklist: tuple[ChecklistEntry, ...]
    completed: int
    next_action: NextAction
    drafts: tuple[Item, ...] = ()
    saved_jobs: tuple[Item, ...] = ()
    ready_to_finish: tuple[Item, ...] = ()
    followups_due: tuple[Item, ...] = ()


def milestone_flags(inputs: HomeInputs) -> tuple[bool, ...]:
    return (
        inputs.readiness.has_resume,
        inputs.readiness.has_resume and inputs.readiness.facts_confirmed,
        inputs.goals_set,
        inputs.role_chosen,
        inputs.application_prepared,
    )


def checklist_entries(inputs: HomeInputs, flags: tuple[bool, ...]) -> tuple[ChecklistEntry, ...]:
    entries = []
    for index, (label, done) in enumerate(zip(CHECKLIST, flags)):
        if done:
            entries.append(ChecklistEntry(label, READY))
        elif index == 1 and inputs.readiness.has_resume:
            n = len(inputs.readiness.attention)
            detail = f"{n} {'item' if n == 1 else 'items'} to review" if n else "Give it a quick look and confirm"
            entries.append(ChecklistEntry(label, ATTENTION, detail))
        else:
            entries.append(ChecklistEntry(label, NOT_STARTED))
    return tuple(entries)


def _first_time_action(index: int, inputs: HomeInputs) -> NextAction:
    if index == 0:
        return NextAction(
            "Import your resume",
            "Everything else builds on it.",
            "Job Copilot reads it once and fills in your profile. You won't type your history again.",
            "Import resume", inline="upload",
        )
    if index == 1:
        attention = len(inputs.readiness.attention)
        why = (
            f"{attention} {'thing needs' if attention == 1 else 'things need'} your attention; the rest only needs a quick look."
            if attention else "Nothing looks wrong. Give it a quick look and confirm."
        )
        return NextAction(
            "Confirm your important facts", why,
            "Only facts you confirm are ever used in a tailored resume.",
            "Review my profile", page=PROFILE_PAGE,
        )
    if index == 2:
        return NextAction(
            "Set your job goals", "A few short questions, one at a time.",
            "Your search starts ready to go, and fit scores reflect what you want.",
            "Answer questions", inline="goals",
        )
    if index == 3:
        return NextAction(
            "Choose a real role", f"Search live openings on {LIVE_BOARD_COUNT} company boards with your goals.",
            "See why each role matches you and what is genuinely missing.",
            "Find jobs", page=JOBS_PAGE,
        )
    return _prepare_action(inputs)


def _prepare_action(inputs: HomeInputs) -> NextAction:
    job = inputs.active_job
    name = f"{job.title}" if job else "your chosen role"
    if inputs.handoff_ready:
        return NextAction(
            f"Finish your application for {name}", "Your tailored resume passed validation.",
            "Open the employer's application with everything ready, then mark it as applied.",
            "Go to Apply", page=APPLY_PAGE,
        )
    return NextAction(
        f"Prepare your application for {name}", "Tailor your resume to this job and review each change.",
        "About a minute to tailor; you approve every change.",
        "Tailor my resume", page=TAILOR_PAGE,
    )


def returning_action(inputs: HomeInputs) -> NextAction:
    """Priority order from spec 007."""
    job = inputs.active_job
    if job and inputs.artifact_status == "FAIL":
        return NextAction(
            f"Fix the resume for {job.title}", "It failed validation, so it can't be used yet.",
            "Review the blocked changes and rebuild.", "Open Tailor", page=TAILOR_PAGE,
        )
    if inputs.followups_due:
        first = inputs.followups_due[0]
        more = len(inputs.followups_due) - 1
        return NextAction(
            f"Follow up: {first.title}", first.detail + (f" (+{more} more due)" if more > 0 else ""),
            "Staying on top of follow-ups keeps applications moving.", "Open Tracker", page=TRACKER_PAGE,
        )
    if job and inputs.artifact_status and not inputs.artifact_reviewed:
        return NextAction(
            f"Review resume changes for {job.title}", "A tailored draft is waiting for your decisions.",
            "Accept, edit or keep each change; nothing is used until you do.", "Open Tailor", page=TAILOR_PAGE,
        )
    if inputs.ready_to_finish:
        first = inputs.ready_to_finish[0]
        return NextAction(
            f"Finish applying: {first.title}", first.detail or "Staged and ready.",
            "Open the employer's application and mark it as applied when you're done.", "Go to Apply", page=APPLY_PAGE,
        )
    if inputs.saved_jobs:
        return NextAction(
            f"Review {len(inputs.saved_jobs)} saved {'job' if len(inputs.saved_jobs) == 1 else 'jobs'}",
            "Decide which are worth an application.", "Prepare an application for the best match.",
            "Open Jobs", page=JOBS_PAGE,
        )
    if not inputs.searched_this_week:
        return NextAction(
            "Search for new roles", "You haven't searched this week.",
            "New postings appear daily on the boards Job Copilot reads.", "Find jobs", page=JOBS_PAGE,
        )
    return NextAction(
        "You're caught up", "Nothing needs you right now.",
        "Search again later, or check your tracker.", "Open Tracker", page=TRACKER_PAGE,
    )


def build_home_view(inputs: HomeInputs) -> HomeView:
    flags = milestone_flags(inputs)
    steps = checklist_entries(inputs, flags)
    completed = sum(flags)
    drafts = ()
    if inputs.active_job and inputs.artifact_status and not inputs.artifact_reviewed:
        drafts = (Item(inputs.active_job.title, inputs.active_job.detail, TAILOR_PAGE),)
    if completed < len(CHECKLIST):
        first_open = flags.index(False)
        action = _first_time_action(first_open, inputs)
        mode = "first_time"
    else:
        action = returning_action(inputs)
        mode = "returning"
    return HomeView(
        mode=mode,
        checklist=steps,
        completed=completed,
        next_action=action,
        drafts=drafts,
        saved_jobs=inputs.saved_jobs,
        ready_to_finish=inputs.ready_to_finish,
        followups_due=inputs.followups_due,
    )


def due_items(rows: list[dict], today: date) -> tuple[Item, ...]:
    """Follow-ups whose due date is today or earlier, oldest first.

    rows: {"title", "company", "next_action", "due", "closed"} with due as ISO date or "".
    """
    due = []
    for row in rows:
        if row.get("closed") or not row.get("due"):
            continue
        try:
            when = date.fromisoformat(str(row["due"])[:10])
        except ValueError:
            continue
        if when <= today:
            label = "overdue since" if when < today else "due today"
            detail = f"{row.get('next_action') or 'Next action'} · {label} {when:%b %d}" if when < today else f"{row.get('next_action') or 'Next action'} · due today"
            due.append((when, Item(f"{row.get('title')} at {row.get('company')}", detail, TRACKER_PAGE)))
    return tuple(item for _, item in sorted(due, key=lambda pair: pair[0]))
