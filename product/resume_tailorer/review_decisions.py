"""Atomic, shared mutations of a saved Tailor review.

The API and Streamlit use this instead of independently updating dispositions.
The lock is the same per-user OS lock that fences batch publication.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Mapping

from resume_tailorer.artifacts.models import ValidationStatus
from resume_tailorer.batch_runner import _file_lock
from resume_tailorer.review_store import discard_review, load_review, save_review
from resume_tailorer.ui.artifact_review import visible_changes
from resume_tailorer.ui.tailor_progress import change_title
from resume_tailorer.ui.tailoring_view import group_changes


class ReviewConflict(ValueError):
    """The submitted review revision is no longer current."""


class ReviewSelectionError(ValueError):
    """The selection is empty, invalid, or unsafe for a batch decision."""


class ReviewStorageError(OSError):
    """The saved review could not be read or replaced."""


def new_review_revision() -> int:
    """The starting revision of a newly tailored review.

    Change IDs are positional (``paragraph:3``), so a fresh run must never start at a
    revision an older tab could still hold, or that tab's choices would land on a
    different proposal at the same position. Milliseconds since the epoch are unique
    per run and stay exact in JavaScript numbers.
    """
    return time.time_ns() // 1_000_000


def apply_decisions(
    state: dict,
    entries: list[tuple[str, str]],
    *,
    origin: str,
    expected_revision: int,
    manual_texts: Mapping[str, str] | None = None,
    reasons: Mapping[str, str] | None = None,
    allow_blank_manual: bool = False,
) -> dict:
    """Validate every selected ID, then return a copy with one revision change."""
    revision = int(state.get("review_revision", 0))
    if expected_revision != revision:
        raise ReviewConflict("This review changed in another tab. Reload it and choose again.")
    if origin not in {"person", "AI-assisted"}:
        raise ReviewSelectionError("Choose a valid review origin.")
    ids = [change_id for change_id, _ in entries]
    if not ids or len(set(ids)) != len(ids):
        raise ReviewSelectionError("Select each reviewable change only once.")

    report = state["report"]
    shown = visible_changes(state["changes"])
    reviewable = group_changes(shown, report.true_gaps).reviewable
    eligible = {change.change_id: change for change in reviewable}
    for change_id, decision in entries:
        change = eligible.get(change_id)
        if change is None:
            raise ReviewSelectionError("Select only changes shown in this review.")
        if decision not in {"ACCEPTED", "REJECTED", "MANUALLY_EDITED"}:
            raise ReviewSelectionError("Choose Accept, Keep original, or Edit manually.")
        if decision == "ACCEPTED" and change.validation_status is ValidationStatus.FAIL:
            title = change_title(change, reviewable.index(change) + 1)
            raise ReviewSelectionError(
                f"“{title}” failed its truth check, so it can't be accepted. "
                "Unselect it, keep its original, or edit it, then try again.")
        if decision == "MANUALLY_EDITED" and not allow_blank_manual and not (manual_texts or {}).get(change_id, "").strip():
            raise ReviewSelectionError("Write the manual wording before saving it.")

    dispositions = dict(state.get("dispositions") or {})
    decided = set(state.get("decided") or set())
    edited = dict(state.get("manual_texts") or {})
    origins = dict(state.get("decision_origins") or {})
    changed = False
    for change_id, decision in entries:
        manual = None
        if decision == "MANUALLY_EDITED":
            given = (manual_texts or {}).get(change_id)
            # No text sent means "edit manually" again: keep the wording already saved.
            manual = (given if given is not None else edited.get(change_id, "")).strip()
        reason = (reasons or {}).get(change_id) or ("Chosen by you" if origin == "person" else "Supported by verified facts")
        was_changed = (change_id not in decided or dispositions.get(change_id) != decision or
                       (decision == "MANUALLY_EDITED" and edited.get(change_id) != manual) or
                       origins.get(change_id) != {"by": origin, "reason": reason})
        changed = changed or was_changed
        dispositions[change_id] = decision
        decided.add(change_id)
        if decision == "MANUALLY_EDITED":
            edited[change_id] = manual
        else:
            edited.pop(change_id, None)
        origins[change_id] = {"by": origin, "reason": reason}

    result = dict(state)
    result.update(dispositions=dispositions, decided=decided, manual_texts=edited,
                  decision_origins=origins, review_revision=revision + int(changed),
                  dirty=bool(state.get("dirty", False) or changed))
    return result


def mutate_saved_review(
    folder: str,
    job_id: str,
    expected_revision: int | None,
    entries: list[tuple[str, str]],
    origin: str,
    *,
    manual_texts: Mapping[str, str] | None = None,
    reasons: Mapping[str, str] | None = None,
    allow_blank_manual: bool = False,
) -> dict:
    """One cross-process read/check/write; no partial decision is published."""
    if not job_id:
        raise ReviewStorageError("The review location is invalid.")
    artifacts = _artifacts_folder(folder)
    with _file_lock(artifacts.parent):
        state = load_review(str(artifacts), job_id)
        if state is None:
            raise ReviewStorageError("This review is no longer available. Reload Tailor.")
        revision = int(state.get("review_revision", 0)) if expected_revision is None else expected_revision
        updated = apply_decisions(state, entries, origin=origin, expected_revision=revision,
                                  manual_texts=manual_texts, reasons=reasons,
                                  allow_blank_manual=allow_blank_manual)
        if updated["review_revision"] == int(state.get("review_revision", 0)):
            return state
        if not save_review(str(artifacts), job_id, updated):
            raise ReviewStorageError("The review could not be saved. Try again.")
        return updated


def _artifacts_folder(folder: str) -> Path:
    artifacts = Path(folder).resolve()
    if artifacts.name != "artifacts":
        raise ReviewStorageError("The review location is invalid.")
    return artifacts


def save_review_locked(folder: str, job_id: str, state: dict, wait: float = 30.0) -> bool:
    """Replace the saved review under the same per-user lock as decisions, so a decision
    that is mid-transaction can't write the old review back over this one."""
    artifacts = _artifacts_folder(folder)
    with _file_lock(artifacts.parent, wait=wait):
        return save_review(str(artifacts), job_id, state)


def discard_review_locked(folder: str, job_id: str, wait: float = 30.0) -> None:
    """Delete the saved review under the decision lock, so it can't be resurrected."""
    artifacts = _artifacts_folder(folder)
    with _file_lock(artifacts.parent, wait=wait):
        discard_review(str(artifacts), job_id)
