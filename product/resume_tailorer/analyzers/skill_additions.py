"""Change levels 2 and 3 (spec 022, decision 043): skills Job Copilot may add to a resume's
skills line, computed from the requirement review by code, never by the model.

- Level 2: the job asks for a skill the person's experience, education or certifications show
  directly, but their skills line doesn't list it.
- Level 3: the job asks for a skill they have no evidence for, but they have a reviewed adjacent
  skill (analyzers/adjacent_skills.py).
- Never (level 4): hard gates (licenses, degrees, years of experience, clearances), broad concept
  words, weak or unconfirmed evidence, or anything outside the skills line.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from resume_tailorer.analyzers.adjacent_skills import adjacent_to
from resume_tailorer.analyzers.requirement_review import (
    DIRECT, GENERIC_TERMS, NONE, RequirementReview, RequirementRow,
)
from resume_tailorer.analyzers.term_match import mentions

MAX_ADDITIONS = 5
# A term that names a credential, a degree or an amount of experience is never a skill to add.
_LEVEL_4 = re.compile(r"licen[cs]|certif|clearance|registered|degree|bachelor|master|ph\.?d|mba|\byears?\b|\d",
                      re.IGNORECASE)


@dataclass(frozen=True)
class SkillAddition:
    term: str
    level: int  # 2 or 3
    requirement_id: str
    reason: str


def _term_statuses(row: RequirementRow) -> tuple[tuple[str, str], ...]:
    if row.term_status:
        return row.term_status
    return tuple((term, row.status) for term in row.terms)


def _evidence_source(row: RequirementRow, term: str) -> str:
    for ref in row.evidence:
        if ref.confirmed and ref.kind in ("experience", "education", "certification") and mentions(term, ref.text):
            return ref.source
    return ""


def propose_skill_additions(review: RequirementReview | None, skills_text: str,
                            *, cap: int = MAX_ADDITIONS) -> list[SkillAddition]:
    """Up to `cap` additions for the skills line, required requirements first, each once."""
    if review is None:
        return []
    has = {t.lower() for t in review.listed}
    for row in review.rows:
        has.update(t.lower() for t, st in _term_statuses(row) if st == DIRECT)

    rows = sorted(review.rows, key=lambda r: 0 if r.section == "required" else 1)
    found: list[SkillAddition] = []
    seen: set[str] = set()
    for row in rows:
        if row.hard_gate:
            continue
        for term, status in _term_statuses(row):
            key = term.lower()
            if (key in seen or term in GENERIC_TERMS or _LEVEL_4.search(term)
                    or mentions(term, skills_text or "")):
                continue
            if status == DIRECT:
                source = _evidence_source(row, term)
                if not source:
                    continue
                found.append(SkillAddition(term, 2, row.id,
                                           f"Your experience shows {term} ({source}), but your skills line doesn't list it."))
            elif status == NONE:
                near = next((n for n in adjacent_to(term) if n.lower() in has), None)
                if near is None:
                    continue
                found.append(SkillAddition(term, 3, row.id,
                                           f"You have {near}; the job asks for {term}, a closely related skill."))
            else:
                continue
            seen.add(key)
    return found[:cap]



def is_computed_skills_line(change) -> bool:
    """A skills change computed by code (levels 2-3) whose line still says exactly what was computed:
    not turned down, not kept original, not reworded by the person (spec 022 step 4)."""
    from resume_tailorer.artifacts.models import ChangeCategory, ChangeDisposition
    from resume_tailorer.artifacts.regeneration import final_text_for_change

    return (change.category is ChangeCategory.SKILLS_ADDED and change.disposition is not ChangeDisposition.MANUALLY_EDITED
            and final_text_for_change(change) == change.proposed_text)


def without_computed_skills(gap_report, changes, *, in_document: bool = False):
    """The gap report minus the terms that computed skills lines add: the one place a term without
    evidence may appear. A proposal is judged as computed; with in_document, only lines that still
    say what was computed count. Bullets, summaries and a person's own wording meet every check."""
    from dataclasses import replace

    from resume_tailorer.artifacts.models import ChangeCategory

    added = {term.casefold() for change in changes
             if change.category is ChangeCategory.SKILLS_ADDED and (not in_document or is_computed_skills_line(change))
             for term, _level, _reason in change.added_skills}
    if not added:
        return gap_report
    return replace(gap_report, items=[item for item in gap_report.items if item.requirement.casefold() not in added])
