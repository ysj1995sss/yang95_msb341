"""Conservative automatic decisions for a newly created Tailor review.

This is automation over the existing model proposal and deterministic checks,
not an independent second model or a substitute for final PDF validation.
"""

from __future__ import annotations

from collections import Counter
import re
from typing import Iterable

from resume_tailorer.artifacts.models import ChangeCategory, ResumeChange, ValidationStatus
from resume_tailorer.review_decisions import apply_decisions
from resume_tailorer.ui.artifact_review import visible_changes
from resume_tailorer.ui.tailor_progress import duplicate_key
from resume_tailorer.ui.tailoring_view import group_changes


_TOKEN = re.compile(r"[a-z0-9]+")
_FUNCTION_WORDS = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "into",
                   "of", "on", "or", "the", "to", "with"}


def preserves_original_details(original: str, proposed: str) -> bool:
    """A conservative lexical gate: changed wording can stay open for the person.

    The individual truth check prevents new claims; this separate gate prevents an
    AI decision from silently dropping dates, metrics, tools, or other content.
    Exact words are intentionally strict: a synonym is not proof of preservation.
    """
    original_terms = {word for word in _TOKEN.findall(original.lower()) if word not in _FUNCTION_WORDS}
    proposed_terms = set(_TOKEN.findall(proposed.lower()))
    return bool(original_terms) and original_terms <= proposed_terms


def recommend_decisions(
    changes: Iterable[ResumeChange], blocked_ids: set[str]
) -> tuple[list[tuple[str, str]], dict[str, str]]:
    """Return only clearly safe accepts and clear rejects; uncertainty stays open."""
    candidates = list(changes)
    keys = [duplicate_key(change) for change in candidates]
    repeated = {key for key, count in Counter(key for key in keys if key is not None).items() if count > 1}
    entries: list[tuple[str, str]] = []
    reasons: dict[str, str] = {}
    for change, key in zip(candidates, keys):
        if change.change_id in blocked_ids or key in repeated:
            continue
        if change.validation_status is ValidationStatus.FAIL:
            entries.append((change.change_id, "REJECTED"))
            reasons[change.change_id] = "The proposed wording did not pass its individual truth check; original kept."
            continue
        safe = (change.validation_status is ValidationStatus.PASS
                and change.category is ChangeCategory.REPHRASED
                and bool(change.original_text.strip() and change.proposed_text.strip())
                and preserves_original_details(change.original_text, change.proposed_text)
                and key is not None
                and not change.scope_issues)
        if safe:
            entries.append((change.change_id, "ACCEPTED"))
            reasons[change.change_id] = "Anchored rephrase with a passing individual truth check."
    return entries, reasons


def apply_assisted_review(state: dict) -> dict:
    """Decide once at review creation; never overwrite later human choices."""
    if state.get("review_mode", "manual") != "assisted" or state.get("assisted_review_applied"):
        return state
    groups = group_changes(visible_changes(state["changes"]), state["report"].true_gaps)
    blocked_ids = {change.change_id for change in groups.blocked}
    undecided = [change for change in groups.reviewable if change.change_id not in (state.get("decided") or set())]
    entries, reasons = recommend_decisions(undecided, blocked_ids)
    result = (apply_decisions(state, entries, origin="AI-assisted",
                              expected_revision=int(state.get("review_revision", 0)), reasons=reasons)
              if entries else dict(state))
    result["assisted_review_applied"] = True
    return result
