"""Pure, Streamlit-free review-state helpers for the validated artifact
pipeline's UI (Steps 16-20, spec 002 section 10 / 20). Deliberately
contains no `import streamlit` and no rendering calls -- app.py wires
these into widgets, but the state-shaping logic itself is unit-testable
without a browser, matching the pattern already established for
job_search/ui_helpers.py and applications/ui_helpers.py.
"""

from __future__ import annotations

import re
from typing import Mapping

from resume_tailorer.artifacts.models import ChangeCategory, ResumeChange

_PUNCTUATION_ONLY_RE = re.compile(r"[^a-z0-9]+")


def _normalized_for_punctuation_check(text: str) -> str:
    return _PUNCTUATION_ONLY_RE.sub("", text.lower())


def _is_punctuation_only_change(change: ResumeChange) -> bool:
    """True when original_text and proposed_text differ only in
    punctuation/whitespace/case -- retained in the full audit data (the
    advanced view) but not meaningful enough to show by default."""
    if not change.original_text or not change.proposed_text:
        return False
    return _normalized_for_punctuation_check(change.original_text) == _normalized_for_punctuation_check(
        change.proposed_text
    )


def visible_changes(changes: list[ResumeChange], advanced: bool = False) -> list[ResumeChange]:
    """The default review view shows meaningful proposed changes; an
    advanced view exposes all audited differences (spec 002 section 10).
    UNCHANGED and punctuation-only changes are hidden by default -- a
    REJECTED change is still shown by default, since a human explicitly
    needs to see and potentially reconsider it, not just an AI-authored
    diff that happens to carry no real information."""
    if advanced:
        return list(changes)
    return [
        change
        for change in changes
        if change.category is not ChangeCategory.UNCHANGED
        and not _is_punctuation_only_change(change)
    ]


def build_review_payload(
    dispositions: Mapping[str, str], manual_texts: Mapping[str, str] | None = None
) -> dict:
    """Build the exact JSON shape the API's PATCH /tailor/runs/{id}/changes
    endpoint expects (app.schemas.artifact.ReviewChangesRequest) -- shared
    shape even though the Streamlit app applies dispositions locally via
    resume_tailorer.artifacts.regeneration rather than calling the API,
    so the two adapters can never silently drift on what a disposition
    update even means."""
    manual_texts = manual_texts or {}
    changes = []
    for change_id, disposition in dispositions.items():
        entry = {"change_id": change_id, "disposition": disposition}
        if disposition == "MANUALLY_EDITED" and change_id in manual_texts:
            entry["manual_text"] = manual_texts[change_id]
        changes.append(entry)
    return {"changes": changes}
