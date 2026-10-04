"""Career Profile readiness: defined required and optional sections, provenance,
and the short list of things that need the user (review by exception).

No percentages: a section is either ready or it names what is missing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from resume_tailorer.profile_store import CONFIRMED, EDITED, FROM_RESUME, provenance_of

PROVENANCE_LABELS = {
    FROM_RESUME: "From resume",
    EDITED: "Edited by you",
    CONFIRMED: "Confirmed by you",
    "missing": "Missing",
}
PROVENANCE_TONES = {FROM_RESUME: "", EDITED: "action", CONFIRMED: "verified", "missing": "review"}


@dataclass(frozen=True)
class SectionReadiness:
    key: str
    name: str
    required: bool
    ready: bool
    issues: tuple[str, ...]


@dataclass(frozen=True)
class ProfileReadiness:
    has_resume: bool
    sections: tuple[SectionReadiness, ...]
    required_ready: int
    required_total: int
    attention: tuple[str, ...]
    facts_confirmed: bool

    @property
    def summary(self) -> str:
        if not self.has_resume:
            return "Not started: import a resume"
        return f"{self.required_ready} of {self.required_total} required sections ready"


def _contact(profile: Mapping[str, Any]) -> SectionReadiness:
    contact = profile.get("contact_info") or {}
    issues = tuple(f"Add your {k}" for k in ("name", "email") if not (contact.get(k) or "").strip())
    return SectionReadiness("contact", "Contact", True, not issues, issues)


def _work(profile: Mapping[str, Any]) -> SectionReadiness:
    jobs = profile.get("work_experience") or []
    if not jobs:
        return SectionReadiness("work", "Work history", True, False, ("Add at least one role",))
    issues = []
    for job in jobs:
        who = f"{job.get('title') or 'A role'} at {job.get('employer') or 'an employer'}"
        if not (job.get("dates") or "").strip():
            issues.append(f"{who}: dates are missing")
        if not (job.get("responsibilities") or job.get("accomplishments")):
            issues.append(f"{who}: no bullet points were found")
    return SectionReadiness("work", "Work history", True, not any("dates" in i for i in issues), tuple(issues))


def _education(profile: Mapping[str, Any], no_education: bool) -> SectionReadiness:
    entries = profile.get("education") or []
    if not entries:
        if no_education:
            return SectionReadiness("education", "Education", True, True, ())
        return SectionReadiness("education", "Education", True, False, ("Add a degree, or mark that you have none to list",))
    issues = []
    for e in entries:
        who = e.get("institution") or "An education entry"
        if not (e.get("degree") or "").strip():
            issues.append(f"{who}: the degree wasn't recognized")
        if not e.get("year"):
            issues.append(f"{who}: graduation year is missing")
    return SectionReadiness("education", "Education", True, not issues, tuple(issues))


def _skills(profile: Mapping[str, Any]) -> SectionReadiness:
    ready = bool(profile.get("skills") or profile.get("tools"))
    return SectionReadiness("skills", "Skills and tools", True, ready, () if ready else ("Add the skills you would stand behind in an interview",))


def build_readiness(record: Mapping[str, Any] | None) -> ProfileReadiness:
    record = record or {}
    profile = record.get("profile") or {}
    has_resume = bool(record.get("resume") or profile)
    prefs = record.get("preferences") or {}
    auth = record.get("authorization") or {}
    links = record.get("links") or {}
    required = (
        _contact(profile),
        _work(profile),
        _education(profile, bool(record.get("no_education"))),
        _skills(profile),
    )
    optional = (
        SectionReadiness("summary", "Professional summary", False, bool((profile.get("summary") or "").strip()), ()),
        SectionReadiness("certifications", "Certifications", False, bool(profile.get("certifications")), ()),
        SectionReadiness("links", "Links", False, any((v or "").strip() for v in links.values()), ()),
        SectionReadiness("preferences", "Job goals", False, bool((prefs.get("job_title") or "").strip()), ()),
        SectionReadiness(
            "authorization", "Work authorization", False,
            auth.get("authorized_to_work") is not None and auth.get("sponsorship_required") is not None, (),
        ),
    )
    attention = tuple(issue for section in required for issue in section.issues) if has_resume else ()
    return ProfileReadiness(
        has_resume=has_resume,
        sections=required + optional,
        required_ready=sum(s.ready for s in required),
        required_total=len(required),
        attention=attention,
        facts_confirmed=bool(record.get("facts_confirmed_at")),
    )


def readiness_line(session: Mapping[str, Any]) -> str:
    record = session.get("profile_record")
    if record is None and session.get("career_profile") is not None:
        profile = session["career_profile"]
        record = {"profile": profile.to_dict() if hasattr(profile, "to_dict") else profile}
    return build_readiness(record).summary


def provenance_label(record: Mapping[str, Any], path: str) -> tuple[str, str]:
    state = provenance_of(dict(record), path)
    return PROVENANCE_LABELS[state], PROVENANCE_TONES[state]


# --- spec 008: section summary list and review-by-exception ----------------

@dataclass(frozen=True)
class SectionRow:
    key: str
    name: str
    detail: str  # "4 roles", "Not added", ...
    status: str  # "Ready", "Incomplete", "2 to review", "Optional"
    tone: str  # verified, review, "" (neutral)
    action: str  # Edit, Review, Add, Manage
    issues: tuple[str, ...] = ()


SECTION_PATHS = {
    "contact": ("contact_info.",),
    "summary": ("summary",),
    "work": ("work_experience[",),
    "education": ("education[",),
    "skills": ("skills", "tools"),
    "certifications": ("certifications",),
}


def review_items(profile: Mapping[str, Any]) -> dict[str, tuple[str, ...]]:
    """Likely parse problems worth a look, by section. Never blocks anything."""
    out: dict[str, list[str]] = {"work": [], "education": [], "skills": []}
    for job in profile.get("work_experience") or []:
        title = (job.get("title") or "").strip()
        if len(title) > 80:
            out["work"].append(f"“{title[:40]}…” looks like a sentence, not a job title")
    for entry in profile.get("education") or []:
        if (entry.get("degree") or "").strip() and not (entry.get("field") or "").strip():
            out["education"].append(f"{entry.get('institution') or 'An entry'}: field of study is empty")
    skills = [s.strip() for s in profile.get("skills") or [] if s.strip()]
    seen, dupes = set(), []
    for skill in skills:
        if skill.lower() in seen and skill not in dupes:
            dupes.append(skill)
        seen.add(skill.lower())
    out["skills"] += [f"“{d}” is listed twice" for d in dupes]
    tools = {t.strip().lower() for t in profile.get("tools") or []}
    out["skills"] += [f"“{s}” is in both skills and tools" for s in dict.fromkeys(skills) if s.lower() in tools]
    return {k: tuple(v) for k, v in out.items() if v}


def provenance_summary(record: Mapping[str, Any], section: str) -> str:
    """One line per section instead of a badge on every field."""
    prefixes = SECTION_PATHS.get(section, ())
    states = [state for path, state in (record.get("provenance") or {}).items()
              if any(path.startswith(p) for p in prefixes)]
    if not states:
        return ""
    parts = []
    if states.count(FROM_RESUME):
        parts.append("from your resume")
    if states.count(EDITED):
        parts.append(f"{states.count(EDITED)} edited by you")
    if states.count(CONFIRMED):
        parts.append("confirmed by you" if states.count(CONFIRMED) == len(states) else
                     f"{states.count(CONFIRMED)} confirmed by you")
    text = ", ".join(parts)
    return text[0].upper() + text[1:]


def section_rows(record: Mapping[str, Any], answers: int = 0) -> tuple[SectionRow, ...]:
    record = record or {}
    profile = record.get("profile") or {}
    readiness = build_readiness(record)
    by_key = {s.key: s for s in readiness.sections}
    extra = review_items(profile)

    def row(key, name, detail, required_ready=None, optional_done=None, action_done="Edit", action_new="Add"):
        issues = (by_key[key].issues if key in by_key and by_key[key].required else ()) + extra.get(key, ())
        if issues:
            n = len(issues)
            return SectionRow(key, name, detail, f"{n} to review", "review", "Review", issues)
        if required_ready is not None:
            return SectionRow(key, name, detail, "Ready" if required_ready else "Incomplete",
                              "verified" if required_ready else "review", action_done if required_ready else "Add")
        return SectionRow(key, name, detail, "Added" if optional_done else "Optional",
                          "verified" if optional_done else "", action_done if optional_done else action_new)

    jobs = profile.get("work_experience") or []
    edu = profile.get("education") or []
    skills = profile.get("skills") or []
    tools = profile.get("tools") or []
    certs = profile.get("certifications") or []
    links = [v for v in (record.get("links") or {}).values() if (v or "").strip()]
    prefs = record.get("preferences") or {}
    auth = record.get("authorization") or {}
    contact = profile.get("contact_info") or {}
    return (
        row("contact", "Contact", contact.get("email") or "No email yet", by_key["contact"].ready),
        row("summary", "Professional summary", "Added" if (profile.get("summary") or "").strip() else "Not added",
            optional_done=bool((profile.get("summary") or "").strip())),
        row("work", "Work history", f"{len(jobs)} {'role' if len(jobs) == 1 else 'roles'}", by_key["work"].ready,
            action_done="Review"),
        row("education", "Education",
            f"{len(edu)} {'school' if len(edu) == 1 else 'schools'}" if edu else
            ("No degree to list" if record.get("no_education") else "None yet"), by_key["education"].ready,
            action_done="Review"),
        row("skills", "Skills and tools", f"{len(skills)} skills · {len(tools)} tools", by_key["skills"].ready),
        row("certifications", "Certifications", f"{len(certs)}" if certs else "None", optional_done=bool(certs)),
        row("links", "Links", f"{len(links)} added" if links else "Not added", optional_done=bool(links)),
        row("goals", "Job goals", prefs.get("job_title") or "Not set", optional_done=bool(prefs.get("job_title"))),
        row("authorization", "Work authorization",
            "Answered" if by_key["authorization"].ready else "Not answered", optional_done=by_key["authorization"].ready),
        SectionRow("answers", "Saved answers", f"{answers} {'answer' if answers == 1 else 'answers'}",
                   "Added" if answers else "Optional", "verified" if answers else "", "Manage"),
    )


def first_section_needing_review(rows: tuple[SectionRow, ...]) -> Optional[str]:
    return next((r.key for r in rows if r.issues), None)
