"""Assist mode, kit form (decision 027): every value an application form usually asks
for, in the order forms ask, ready to copy. Pure.

Values come only from the confirmed Career Profile, the tailored resume handed off for
this job, and answers the user approved. Nothing is guessed: a value that isn't there
is shown as missing, and legal answers (work authorization, sponsorship) appear only
when the user chose them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Optional

READY, MISSING, OPTIONAL = "ready", "missing", "optional"


@dataclass(frozen=True)
class KitField:
    label: str
    value: str
    source: str
    state: str  # READY, MISSING (the form will likely require it) or OPTIONAL (often asked, not required)
    fix: str = ""  # where to add it when it's missing


def _split_name(name: str) -> tuple[str, str]:
    parts = (name or "").split()
    if not parts:
        return "", ""
    return parts[0], " ".join(parts[1:])


def _yes_no(value: Optional[bool]) -> str:
    return {True: "Yes", False: "No"}.get(value, "")


def _field(label: str, value: Any, source: str, required: bool = True, fix: str = "Career Profile") -> KitField:
    text = str(value or "").strip()
    if text:
        return KitField(label, text, source, READY)
    return KitField(label, "", source, MISSING if required else OPTIONAL, fix)


def build_kit(
    record: Optional[Mapping[str, Any]],
    handoff: Optional[Mapping[str, Any]],
    answers: Iterable[Mapping[str, Any]] = (),
) -> tuple[KitField, ...]:
    record = record or {}
    profile = record.get("profile") or {}
    contact = profile.get("contact_info") or {}
    links = record.get("links") or {}
    authorization = record.get("authorization") or {}
    first, last = _split_name(contact.get("name", ""))
    jobs = profile.get("work_experience") or []
    schools = profile.get("education") or []
    latest_job = jobs[0] if jobs else {}
    school = schools[0] if schools else {}
    degree = " ".join(str(school.get(k) or "") for k in ("degree", "field")).strip() if school else ""

    resume = ""
    if handoff and str(handoff.get("validation_status", "")).upper() != "FAIL":
        resume = f"tailored_resume_v{handoff.get('version', 1)}.pdf"

    fields = [
        _field("First name", first, "Career Profile"),
        _field("Last name", last, "Career Profile"),
        _field("Email", contact.get("email"), "Career Profile"),
        _field("Phone", contact.get("phone"), "Career Profile"),
        _field("Location", contact.get("location"), "Career Profile"),
        _field("Resume", resume, "Tailor", fix="Tailor"),
        _field("LinkedIn", links.get("linkedin"), "Career Profile", required=False),
        _field("Website or portfolio", links.get("portfolio"), "Career Profile", required=False),
        _field("Current or most recent employer", latest_job.get("employer"), "Career Profile", required=False),
        _field("Current or most recent title", latest_job.get("title"), "Career Profile", required=False),
        _field("School", school.get("institution"), "Career Profile", required=False),
        _field("Degree", degree, "Career Profile", required=False),
        _field("Legally authorized to work here?", _yes_no(authorization.get("authorized_to_work")),
               "Your answer in Career Profile"),
        _field("Will you need visa sponsorship?", _yes_no(authorization.get("sponsorship_required")),
               "Your answer in Career Profile"),
    ]
    if (links.get("github") or "").strip():  # not editable in Career Profile yet; shown only when present
        fields.insert(8, _field("GitHub", links.get("github"), "Career Profile"))
    for entry in answers:
        question, answer = str(entry.get("question") or "").strip(), str(entry.get("answer") or "").strip()
        if question and answer:
            fields.append(KitField(question, answer, "Your saved answers", READY))
    return tuple(fields)


def kit_summary(fields: Iterable[KitField]) -> str:
    fields = tuple(fields)
    ready = sum(f.state == READY for f in fields)
    missing = [f.label for f in fields if f.state == MISSING]
    line = f"{ready} answers ready to copy."
    if missing:
        line += f" Missing: {', '.join(missing)}."
    return line


# Kit labels -> the browser helper's field keys (extension/fill.js).
_HELPER_KEYS = {
    "First name": "first_name", "Last name": "last_name", "Email": "email", "Phone": "phone",
    "Location": "location", "LinkedIn": "linkedin", "Website or portfolio": "portfolio", "GitHub": "github",
    "Current or most recent employer": "current_company", "Current or most recent title": "current_title",
    "School": "school", "Degree": "degree",
    "Legally authorized to work here?": "authorized_to_work",
    "Will you need visa sponsorship?": "needs_sponsorship",
}


def helper_payload(fields: Iterable[KitField]) -> str:
    """The code the user pastes into the browser helper: only ready values, nothing guessed."""
    import json

    fields = tuple(fields)
    values = {_HELPER_KEYS[f.label]: f.value for f in fields if f.state == READY and f.label in _HELPER_KEYS}
    if values.get("first_name"):
        values["full_name"] = " ".join(v for v in (values.get("first_name"), values.get("last_name")) if v)
    answers = [{"question": f.label, "answer": f.value} for f in fields
               if f.state == READY and f.source == "Your saved answers"]
    return json.dumps({"jobCopilotKit": 1, "fields": values, "answers": answers}, ensure_ascii=False)
