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
