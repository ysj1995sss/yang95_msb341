"""Job goals: the one-question-at-a-time wizard and how saved goals reach Jobs.

Goals are stored in the Career Profile record (preferences), so they survive
sessions. Work authorization answers are stored separately and only ever come
from what the user chose. Pure; no Streamlit import.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, MutableMapping

GOALS_APPLIED_KEY = "job_goals_applied_signature"
WIZARD_STEP_KEY = "goals_wizard_step"
WIZARD_DRAFT_KEY = "goals_wizard_draft"

WORK_MODES = ["any", "remote", "hybrid", "onsite"]
WORK_MODE_LABELS = {"any": "No preference", "remote": "Remote", "hybrid": "Hybrid", "onsite": "On-site"}
YES_NO_LATER = ["Yes", "No", "I'll answer later"]

# Keys that go into the Jobs search form. Authorization answers are kept apart.
SEARCH_KEYS = (
    "job_title", "location", "remote_preference", "experience_level", "min_salary",
    "industries", "relocation_willing",
)


@dataclass(frozen=True)
class WizardStep:
    key: str
    title: str
    help: str
    required: bool = False


WIZARD_STEPS = (
    WizardStep("job_title", "What role are you looking for?", "Pick one of your past titles or type a new one.", True),
    WizardStep("location", "Where do you want to work?", "A city, state or country. Leave blank for anywhere."),
    WizardStep("remote_preference", "How do you want to work?", "Remote, hybrid, on-site, or no preference."),
    WizardStep("experience_level", "What level are you aiming for?", "Pick all that fit, or none for any level."),
    WizardStep("min_salary", "What is the lowest salary you'd consider?", "Yearly, in US dollars. Leave at 0 for no minimum."),
    WizardStep("industries", "Any industries you prefer?", "Leave empty to stay open to anything."),
    WizardStep(
        "authorization", "Work authorization",
        "Employers ask these on most applications. Only you can answer them; Job Copilot never guesses.",
    ),
)


def suggested_titles(profile: Mapping[str, Any] | None, limit: int = 4) -> list[str]:
    """The user's own job titles, most recent first. Suggestions, never assumptions."""
    seen: list[str] = []
    for job in (profile or {}).get("work_experience") or []:
        title = (job.get("title") or "").strip()
        if title and title.lower() not in {t.lower() for t in seen}:
            seen.append(title)
    return seen[:limit]


def step_valid(step: WizardStep, goals: Mapping[str, Any]) -> bool:
    if not step.required:
        return True
    return bool(str(goals.get(step.key) or "").strip())


def draft_from_record(record: Mapping[str, Any]) -> dict:
    draft = dict(record.get("preferences") or {})
    auth = record.get("authorization") or {}
    draft["authorized_to_work"] = auth.get("authorized_to_work")
    draft["sponsorship_required"] = auth.get("sponsorship_required")
    return draft


def answer_to_bool(answer: str) -> bool | None:
    return {"Yes": True, "No": False}.get(answer)


def bool_to_answer(value: bool | None) -> str:
    return {True: "Yes", False: "No"}.get(value, "I'll answer later")


def save_goals(record: MutableMapping[str, Any], goals: Mapping[str, Any]) -> None:
    """Write wizard answers into the record. Empty answers mean no preference."""
    prefs = dict(record.get("preferences") or {})
    for key in SEARCH_KEYS:
        value = goals.get(key)
        if value in (None, "", [], 0, False) and key != "remote_preference":
            prefs.pop(key, None)
        else:
            prefs[key] = value
    prefs.setdefault("remote_preference", "any")
    record["preferences"] = prefs
    auth = dict(record.get("authorization") or {})
    for key in ("authorized_to_work", "sponsorship_required"):
        if key in goals:
            auth[key] = goals[key]
    record["authorization"] = auth


def _signature(record: Mapping[str, Any]) -> str:
    payload = {
        "prefs": record.get("preferences") or {},
        "sponsor": (record.get("authorization") or {}).get("sponsorship_required"),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def apply_goals_to_search_form(session: MutableMapping[str, Any], record: Mapping[str, Any] | None) -> bool:
    """Seed the Jobs form from saved goals whenever the saved goals change.

    Edits made on the Jobs page stay until the saved goals change again.
    """
    if not record or not (record.get("preferences") or {}).get("job_title"):
        return False
    signature = _signature(record)
    if session.get(GOALS_APPLIED_KEY) == signature:
        return False
    for key, value in (record.get("preferences") or {}).items():
        if key in SEARCH_KEYS:
            session[key] = value
    session["sponsorship_required"] = bool((record.get("authorization") or {}).get("sponsorship_required"))
    session[GOALS_APPLIED_KEY] = signature
    return True


def form_to_goals(form: Mapping[str, Any]) -> dict:
    """The Jobs form's current values as goals worth saving."""
    return {key: form.get(key) for key in SEARCH_KEYS}


def goals_summary(record: Mapping[str, Any]) -> list[tuple[str, str]]:
    goals = record.get("preferences") or {}
    auth = record.get("authorization") or {}

    def join(v: Any) -> str:
        return ", ".join(v) if isinstance(v, (list, tuple)) else str(v)

    rows = [
        ("Role", goals.get("job_title") or "Not set"),
        ("Location", goals.get("location") or "Anywhere"),
        ("Work mode", WORK_MODE_LABELS.get(goals.get("remote_preference") or "any", "No preference")),
        ("Level", join(goals["experience_level"]) if goals.get("experience_level") else "Any"),
        ("Minimum salary", f"${int(goals['min_salary']):,}" if goals.get("min_salary") else "No minimum"),
        ("Industries", join(goals["industries"]) if goals.get("industries") else "Open to anything"),
        ("Authorized to work", bool_to_answer(auth.get("authorized_to_work"))),
        ("Needs sponsorship", bool_to_answer(auth.get("sponsorship_required"))),
    ]
    return rows
