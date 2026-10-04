"""Career Profile readiness: defined required and optional sections, provenance,
and the short list of things that need the user (review by exception).

No percentages: a section is either ready or it names what is missing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

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
