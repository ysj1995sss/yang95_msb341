"""Guided setup: the checklist and one-question-per-screen goals wizard.

Pure logic lives here so it can be tested without Streamlit. The Start Here
page renders it. Goals are kept in session state under GOALS_KEY and copied into
the Job Search form's widget keys once (Streamlit drops widget state for widgets
that are not on the current page, so the form cannot be the store).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, MutableMapping

GOALS_KEY = "job_goals"
GOALS_APPLIED_KEY = "job_goals_applied"
WIZARD_STEP_KEY = "goals_wizard_step"

WORK_MODES = ["any", "remote", "hybrid", "onsite"]


@dataclass(frozen=True)
class WizardStep:
    key: str
    title: str
    help: str
    required: bool = False


WIZARD_STEPS = (
    WizardStep("job_title", "What role are you looking for?", "One title is enough to start. You can refine it later.", True),
    WizardStep("location", "Where do you want to work?", "A city, state or country. Leave blank for anywhere."),
    WizardStep("remote_preference", "How do you want to work?", "Remote, hybrid, on-site, or no preference."),
    WizardStep("experience_level", "What level are you aiming for?", "Pick all that fit."),
    WizardStep("min_salary", "What is the lowest salary you would consider?", "Yearly, in USD. 0 means no minimum."),
    WizardStep("sponsorship_required", "Work authorization", "Do you need an employer to sponsor your work visa now or later? Answer for yourself; we will not guess."),
    WizardStep("industries", "Any industries you prefer?", "Leave empty to be open to anything."),
)


@dataclass(frozen=True)
class ChecklistItem:
    label: str
    detail: str
    done: bool
    page: str
    action: str


START_PAGE = "pages/0_Start_Here.py"


def _has(session: Mapping[str, Any], *keys: str) -> bool:
    return any(bool(session.get(k)) for k in keys)


def build_checklist(session: Mapping[str, Any]) -> tuple[ChecklistItem, ...]:
    artifact = session.get("artifact_run_state") or {}
    reviewed = bool(isinstance(artifact, Mapping) and artifact.get("reviewed"))
    handoff = _has(session, "launchpad_handoff", "tailored_resume_handoff")
    return (
        ChecklistItem("Add and verify your facts", "Upload a resume and confirm what is true.", _has(session, "career_profile"), "pages/1_Profile_Review.py", "Open Fact Vault"),
        ChecklistItem("Set your job goals", "Seven short questions, one at a time.", bool(session.get(GOALS_KEY)), START_PAGE, "Answer questions"),
        ChecklistItem("Pick a role", "Find postings and save the ones worth tailoring for.", _has(session, "selected_job", "pending_tailor_job", "job_description_text"), "pages/2_Job_Search.py", "Find jobs"),
        ChecklistItem("Review your tailored resume", "Accept or reject each proposed edit.", reviewed, "app.py", "Open Tailoring Studio"),
        ChecklistItem("Stage your application", "Preview, then apply yourself or hand off.", handoff, "pages/3_Applications.py", "Open Launchpad"),
    )


def progress(items: tuple[ChecklistItem, ...]) -> tuple[int, int]:
    return sum(i.done for i in items), len(items)


def next_item(items: tuple[ChecklistItem, ...]) -> ChecklistItem | None:
    return next((i for i in items if not i.done), None)


def step_valid(step: WizardStep, goals: Mapping[str, Any]) -> bool:
    if not step.required:
        return True
    return bool(str(goals.get(step.key) or "").strip())


def save_goals(session: MutableMapping[str, Any], goals: Mapping[str, Any]) -> None:
    session[GOALS_KEY] = {
        k: v for k, v in goals.items() if v not in (None, "", [], 0, False) or k == "remote_preference"
    }
    session[GOALS_APPLIED_KEY] = False


def apply_goals_to_search_form(session: MutableMapping[str, Any]) -> bool:
    """Seed Job Search's widget keys from saved goals, once. Returns True if applied."""
    goals = session.get(GOALS_KEY)
    if not goals or session.get(GOALS_APPLIED_KEY):
        return False
    for key, value in goals.items():
        session[key] = value
    session[GOALS_APPLIED_KEY] = True
    return True


def goals_summary(goals: Mapping[str, Any]) -> list[tuple[str, str]]:
    def join(v: Any) -> str:
        return ", ".join(v) if isinstance(v, (list, tuple)) else str(v)

    rows = [
        ("Role", goals.get("job_title")),
        ("Location", goals.get("location") or "Anywhere"),
        ("Work mode", goals.get("remote_preference") or "any"),
        ("Level", join(goals["experience_level"]) if goals.get("experience_level") else "Any"),
        ("Minimum salary", f"${int(goals['min_salary']):,}" if goals.get("min_salary") else "No minimum"),
        ("Needs sponsorship", "Yes" if goals.get("sponsorship_required") else "No"),
        ("Industries", join(goals["industries"]) if goals.get("industries") else "Open to anything"),
    ]
    return [(k, str(v)) for k, v in rows if v]


HOW_IT_WORKS = (
    ("1", "Verify your facts", "Upload a resume. You confirm every fact once, and only those facts are ever used."),
    ("2", "Find and match a role", "Search live company boards and see what each posting wants that you lack."),
    ("3", "Review, then apply", "Accept or reject each edit. Apply yourself; nothing is submitted without your approval."),
)

BEFORE_AFTER = (
    ("Rewriting your resume for every posting", "A tailored resume in about a minute, from your verified facts"),
    ("Guessing whether you fit", "A fit score with the missing requirements spelled out"),
    ("Tools that may invent experience", "Every edit shown next to the evidence, blocked if unsupported"),
    ("Losing track of what you sent", "A tracker that saves the exact resume and answers you used"),
)
