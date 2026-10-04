"""Tailor review room: queue order, review progress, supporting facts, and when
the user may continue to Apply. Pure; app code passes the run state in."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Optional

from resume_tailorer.artifacts.models import ChangeCategory, ResumeChange, ValidationStatus

# One vocabulary everywhere (spec 007).
VERBS = {"ACCEPTED": "Accept change", "MANUALLY_EDITED": "Edit manually", "REJECTED": "Keep original"}
DECISION_DONE = {"ACCEPTED": "Accepted", "MANUALLY_EDITED": "Edited by you", "REJECTED": "Original kept"}


@dataclass(frozen=True)
class ReviewProgress:
    reviewed: int
    total: int
    needs_rebuild: bool
    can_continue: bool
    blocker: str  # why Continue is unavailable, "" when it is available

    @property
    def label(self) -> str:
        if self.total == 0:
            return "No changes need your review"
        return f"{self.reviewed} of {self.total} changes reviewed"


def review_progress(
    reviewable: Iterable[ResumeChange], decided: Iterable[str], dirty: bool, status: Any
) -> ReviewProgress:
    ids = [c.change_id for c in reviewable]
    done = len(set(ids) & set(decided))
    status_value = str(getattr(status, "value", status) or "").upper()
    if status_value == ValidationStatus.FAIL.value:
        blocker = "This resume failed validation. Fix the blocked items and rebuild."
    elif done < len(ids):
        blocker = f"Review the remaining {len(ids) - done} {'change' if len(ids) - done == 1 else 'changes'} first."
    elif dirty:
        blocker = "Rebuild the resume so it includes your decisions."
    else:
        blocker = ""
    return ReviewProgress(done, len(ids), dirty, blocker == "", blocker)


def next_undecided(reviewable: Iterable[ResumeChange], decided: Iterable[str], after: Optional[str] = None) -> Optional[str]:
    ids = [c.change_id for c in reviewable]
    decided = set(decided)
    start = ids.index(after) + 1 if after in ids else 0
    for change_id in ids[start:] + ids[:start]:
        if change_id not in decided:
            return change_id
    return None


_WORD = re.compile(r"[a-z0-9+#.]+")


def _words(text: str) -> set[str]:
    return set(_WORD.findall((text or "").lower()))


def supporting_fact(change: ResumeChange, profile: Any) -> str:
    """The verified fact that justifies a change, in plain words.

    A skills, tools or certifications entry counts only when the change
    actually adds it (decision 021's open item: the evidence line used to
    repeat the bullet). Otherwise the recorded evidence or the original line.
    """
    data = profile.to_dict() if hasattr(profile, "to_dict") else (profile or {})
    proposed = (change.proposed_text or "").lower()
    original = (change.original_text or "").lower()
    for label, key in (("your skills", "skills"), ("your tools", "tools"), ("your certifications", "certifications")):
        for entry in data.get(key) or []:
            needle = entry.strip().lower()
            if needle and needle in proposed and needle not in original:
                return f"Listed in {label}: {entry}"
    evidence = (change.evidence_text or "").strip()
    if evidence.lower() in ("none", "null", "n/a"):
        evidence = ""
    if evidence and evidence != (change.original_text or "").strip():
        return evidence
    return f"Your original bullet: {change.original_text}" if change.original_text else "No supporting fact recorded"


def readable_requirement(change: ResumeChange, limit: int = 160) -> str:
    text = (change.job_requirement or "").strip()
    if not text:
        return "General fit with the posting"
    return text if len(text) <= limit else text[: limit - 3].rsplit(" ", 1)[0] + "…"


def validation_word(status: Any) -> str:
    value = str(getattr(status, "value", status) or "").upper()
    return {"PASS": "Verified", "WARNING": "Needs a look", "FAIL": "We could not verify this claim"}.get(value, "Not checked")


def artifact_tone(status: Any) -> str:
    value = str(getattr(status, "value", status) or "").upper()
    return {"PASS": "verified", "WARNING": "review", "FAIL": "blocked"}.get(value, "")


def artifact_status_text(status: Any) -> str:
    value = str(getattr(status, "value", status) or "").upper()
    return {
        "PASS": "Passed validation",
        "WARNING": "Passed with warnings to review",
        "FAIL": "Failed validation: not usable",
    }.get(value, "Not built yet")


def rejected_by_checks(changes: Iterable[ResumeChange]) -> tuple[ResumeChange, ...]:
    """Proposals the truth or length checks turned down; the original wording was kept."""
    return tuple(c for c in changes if getattr(c.category, "value", c.category) == ChangeCategory.REJECTED.value)


def empty_queue_message(changes: Iterable[ResumeChange]) -> str:
    """What to say when nothing needs review, without claiming more than is known."""
    rejected = rejected_by_checks(changes)
    if rejected:
        n = len(rejected)
        return (f"Job Copilot proposed {n} {'change' if n == 1 else 'changes'}, but "
                f"{'it' if n == 1 else 'none'} {'did not pass' if n == 1 else 'passed'} the truth and length checks, "
                "so your original wording was kept. See what was turned down below.")
    return "The writing model didn't propose any changes for this job. Your original wording is unchanged."
