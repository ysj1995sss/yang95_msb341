"""Locate reviewable free-form sections without changing bullet pairing."""

from __future__ import annotations

from dataclasses import dataclass
import re

from resume_tailorer.models import CareerTruthProfile


@dataclass(frozen=True)
class SectionSpan:
    name: str
    start: int
    end: int
    text: str


class SectionAmbiguity(ValueError):
    """A section cannot be identified safely enough for a review decision."""


_TARGETS = {
    "SUMMARY": "summary", "PROFESSIONAL SUMMARY": "summary",
    "SKILLS": "skills", "TECHNICAL SKILLS": "skills", "CORE COMPETENCIES": "skills",
}
_BOUNDARIES = set(_TARGETS) | {
    "EXPERIENCE", "WORK EXPERIENCE", "PROFESSIONAL EXPERIENCE", "EMPLOYMENT",
    "EDUCATION", "CERTIFICATIONS", "PROJECTS", "ADDITIONAL",
    "TOOLS", "TOOLS & PLATFORMS", "TECHNICAL PROFICIENCY", "TECHNOLOGIES",
}


def find_sections(text: str) -> dict[str, SectionSpan]:
    lines = text.splitlines(keepends=True)
    offsets: list[int] = []
    position = 0
    for line in lines:
        offsets.append(position)
        position += len(line)
    headings = [(i, line.strip().upper()) for i, line in enumerate(lines)
                if line.strip().upper() in _BOUNDARIES]
    found: dict[str, SectionSpan] = {}
    for number, (i, heading) in enumerate(headings):
        name = _TARGETS.get(heading)
        if name is None:
            continue
        if name in found:
            raise SectionAmbiguity(f"More than one {name} section")
        start = offsets[i]
        end = offsets[headings[number + 1][0]] if number + 1 < len(headings) else len(text)
        found[name] = SectionSpan(name, start, end, text[start:end])
    return found


def profile_section(profile: CareerTruthProfile, name: str) -> str:
    if name == "summary":
        return f"SUMMARY\n{profile.summary.strip()}\n" if profile.summary.strip() else ""
    if name == "skills":
        terms = [term.strip() for term in profile.skills if term.strip()]
        return "SKILLS\n" + ", ".join(terms) + "\n" if terms else ""
    raise SectionAmbiguity(f"Unknown section: {name}")


def missing_section_anchor(text: str, name: str) -> int:
    if name == "summary":
        offset = 0
        for line in text.splitlines(keepends=True):
            if line.strip().upper() in _BOUNDARIES:
                return offset
            offset += len(line)
        raise SectionAmbiguity("Cannot place a removed summary without a section boundary")
    if name == "skills":
        offset = 0
        for line in text.splitlines(keepends=True):
            if line.strip().upper() in {"EDUCATION", "CERTIFICATIONS"}:
                return offset
            offset += len(line)
        if any(line.strip().upper() in _BOUNDARIES for line in text.splitlines()):
            return len(text)
        raise SectionAmbiguity("Cannot place a removed skills section without a section boundary")
    raise SectionAmbiguity(f"Unknown section: {name}")


def comparable_content(text: str, name: str) -> str | tuple[str, ...]:
    lines = text.splitlines()
    body = "\n".join(lines[1:]).strip()
    if name == "summary":
        return " ".join(body.split()).casefold()
    # Skills are a list, not prose: line wrapping and bullet markers are presentation only.
    return tuple(re.sub(r"^\s*[-*•]\s*", "", term).strip().casefold()
                 for term in body.replace("\n", ",").split(",")
                 if term.strip())


def with_skill_additions(text: str, review) -> tuple[str, list]:
    """`text` with the skills Job Copilot computes (spec 022 levels 2-3) added to the first line of
    its skills section, and those additions. The same code the Word path uses chooses them; until
    now a PDF resume never got them (2026-10-13)."""
    from resume_tailorer.analyzers.skill_additions import propose_skill_additions
    from resume_tailorer.docx_export.skills_line import append_skills

    span = find_sections(text).get("skills") if review is not None else None
    if span is None:
        return text, []
    lines = span.text.splitlines(keepends=True)
    first = next((i for i, line in enumerate(lines[1:], 1) if line.strip()), None)
    if first is None:
        return text, []
    additions = propose_skill_additions(review, "".join(lines[1:]))
    if not additions:
        return text, []
    body = lines[first].rstrip("\r\n")
    lines[first] = append_skills(body, [a.term for a in additions]) + lines[first][len(body):]
    return text[:span.start] + "".join(lines) + text[span.end:], additions


def with_certifications(text: str, profile: CareerTruthProfile) -> str:
    """`text` with every certification in the profile. A model sometimes leaves the CERTIFICATIONS
    section out "for space", which the review then proposed as removing a real credential (an AWS
    certification, for a job asking for AWS; dogfood, 2026-10-13). Credentials are facts, not space."""
    missing = [cert for cert in profile.certifications if cert.strip() and cert.strip().casefold() not in text.casefold()]
    if not missing:
        return text
    added = "".join(f"- {cert.strip()}\n" for cert in missing)
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.strip().rstrip(":").upper() == "CERTIFICATIONS":
            return "".join(lines[:index + 1]) + added + "".join(lines[index + 1:])
    return text.rstrip("\n") + "\n\nCERTIFICATIONS\n" + added
