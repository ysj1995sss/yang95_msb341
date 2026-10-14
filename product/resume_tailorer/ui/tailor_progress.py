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


def _listed(raw: str) -> str:
    return ", ".join(term.strip().strip("'\"") for term in raw.split(",") if term.strip())


def _as_written(term: str, text: str) -> str:
    """The check's lower-case term as the proposed text spells it ("kubernetes" -> "Kubernetes")."""
    found = re.search(re.escape(term), text, re.IGNORECASE)
    return found.group(0) if found else term


# The checks' own messages (diff_generator) name the whole bullet and print Python lists; the review
# showed them as they were (dogfood round 5). Each becomes what the person needs to know.
_WARNING = "⚠️?\\s*"
_RAW_CHECKS = (
    (re.compile(_WARNING + r"POSSIBLY UNVERIFIED: new term\(s\) \[(.*?)\] in '.*?' not grounded in the original "
                r"bullet or profile -- review before using", re.S),
     lambda m: f"Adds words your facts don't show: {_listed(m.group(1))}."),
    (re.compile(_WARNING + r"FABRICATION RISK: metric '(.*?)' mentioned in '.*?' but not in the original bullet or "
                r"profile", re.S),
     lambda m: f"Adds a number your facts don't show: {m.group(1)}."),
    (re.compile(_WARNING + r"FABRICATION RISK: '(.*?)' mentioned in '(.*?)' but not in the original bullet or "
                r"profile", re.S),
     lambda m: f"Names {_as_written(m.group(1), m.group(2))}, which your facts don't show."),
    (re.compile(r"SEMANTIC DRIFT: dropped metric\(s\) \[(.*?)\] from the original bullet '.*?' -- a number/scale "
                r"disappearing changes the claim", re.S),
     lambda m: f"Drops a number from your original: {_listed(m.group(1))}."),
    (re.compile(r"SEMANTIC DRIFT: dropped word\(s\) \[(.*?)\] from the original bullet's core claim '.*?' -- "
                r"rewrite changes what was claimed, not just how it's phrased", re.S),
     lambda m: f"Drops part of what you did: {_listed(m.group(1))}."),
)


# The Word path's short labels for a rewrite its checks turned down (docx_bullet_tailorer).
_TURN_DOWN_LABELS = {
    "semantic drift": "It dropped part of what your original says.",
    "length cap exceeded": "It made the line too long.",
    "unverified content": "It added words your facts don't show.",
    "unsupported requirement term": "It named a skill you haven't shown evidence for.",
}


def readable_reason(reason: str) -> str:
    """A change's reason or a check finding in plain words; other text is left as written."""
    if (reason or "").strip() in _TURN_DOWN_LABELS:  # "— semantic drift" in the list (round 6 bug hunt)
        return _TURN_DOWN_LABELS[reason.strip()]
    text = reason or ""
    for pattern, plain in _RAW_CHECKS:
        text = pattern.sub(plain, text)
    if text == (reason or ""):
        return text
    text = " ".join(text.split())
    # Each issue starts a sentence: "…don't show. adds “dbt”…" -> "…don't show. Adds “dbt”…".
    text = re.sub(r"(^|[.!?] )([a-z])", lambda m: m.group(1) + m.group(2).upper(), text)
    return text if text.endswith((".", "!", "?")) else text + "."


def change_section_label(change: ResumeChange) -> str:
    return {"summary": "Summary", "skills": "Skills"}.get(change.section, "Work experience")


def change_title(change: ResumeChange, ordinal: int) -> str:
    """A review-row label about the edit itself, not its reusable job requirement."""
    def excerpt(value: str, fallback: str) -> str:
        words = " ".join((value or "").split()) or fallback
        return words if len(words) <= 64 else words[:61].rstrip() + "…"

    return (f"{ordinal}. {change_section_label(change)} · "
            f"{excerpt(change.original_text, '(new line)')} → "
            f"{excerpt(change.proposed_text, '(removed)')}")


def duplicate_key(change: ResumeChange) -> tuple | None:
    """Only a real source occurrence can establish an exact duplicate edit."""
    anchor = change.baseline_span if change.baseline_span is not None else (
        change.source_index if not change.change_id.startswith("freeform:") else None
    )
    if anchor is None:
        return None
    return change.section, anchor, change.original_text, change.proposed_text


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
        return f"{self.reviewed} of {self.total} meaningful changes reviewed"


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
    if change.section == "summary":
        return f"Your Career Profile summary: {data.get('summary') or change.evidence_text}"
    if change.section == "skills":
        return "Your Career Profile skills: " + ", ".join(data.get("skills") or [])
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
