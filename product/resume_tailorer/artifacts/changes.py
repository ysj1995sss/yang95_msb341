"""Convert freeform resume diffs into evidence-linked shared changes."""

from __future__ import annotations

import re

from resume_tailorer.analyzers.gap_analyzer import GapItem, GapReport
from resume_tailorer.diff_generator import BulletChange, DiffGenerator
from resume_tailorer.models import CareerTruthProfile

from .models import ChangeCategory, ChangeDisposition, ResumeChange, ValidationStatus


AMBIGUOUS_PAIRING_THRESHOLD = 0.45
_TOKENS = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return {token for token in _TOKENS.findall(text.lower()) if len(token) > 2}


def _related_gap(change: BulletChange, gap_report: GapReport) -> GapItem | None:
    change_tokens = _tokens(f"{change.original} {change.tailored}")
    ranked: list[tuple[int, int, GapItem]] = []
    for index, item in enumerate(gap_report.items):
        evidence_tokens = _tokens(f"{item.requirement} {item.candidate_evidence}")
        ranked.append((len(change_tokens & evidence_tokens), -index, item))
    if not ranked:
        return None
    overlap, _position, item = max(ranked, key=lambda value: (value[0], value[1]))
    return item if overlap else None


def _category(change: BulletChange) -> ChangeCategory:
    if change.change_type == "reordered":
        return ChangeCategory.REORDERED
    if change.change_type == "rephrased":
        return ChangeCategory.REPHRASED
    if change.change_type == "removed":
        return ChangeCategory.CONDENSED
    if change.change_type in {"modified", "added"}:
        return ChangeCategory.COMPETENCY_CHANGED
    return ChangeCategory.UNCHANGED


def build_freeform_changes(
    profile: CareerTruthProfile,
    tailored_text: str,
    gap_report: GapReport,
) -> list[ResumeChange]:
    """Build deterministic, reviewable changes for the freeform/PDF path."""
    diff_generator = DiffGenerator()
    diff = diff_generator.generate_diff(profile, tailored_text)
    changes: list[ResumeChange] = []
    for index, change in enumerate(diff.changes):
        similarity = change.similarity
        ambiguous = (
            bool(change.original and change.tailored)
            and similarity is not None
            and similarity < AMBIGUOUS_PAIRING_THRESHOLD
        )
        related = _related_gap(change, gap_report)
        reason = change.reasoning
        category = _category(change)
        status = ValidationStatus.PASS
        disposition = ChangeDisposition.PENDING
        unverified = (
            diff_generator.check_bullet_pair_fabrication_risk(change.original, change.tailored, profile)
            if change.tailored
            else []
        )
        if unverified:
            # Left PENDING so the user decides; the content gate blocks the
            # artifact while this text is still in it.
            status = ValidationStatus.FAIL
            reason = " ".join(unverified)
        if ambiguous:
            category = ChangeCategory.REJECTED
            status = ValidationStatus.FAIL
            disposition = ChangeDisposition.REJECTED
            reason = (
                f"Ambiguous bullet pairing ({similarity:.0%} similarity); "
                "review the source and proposed text before accepting this change."
            )

        changes.append(
            ResumeChange(
                change_id=f"freeform:{index}",
                section="work_experience",
                source_index=index,
                original_text=change.original,
                proposed_text=change.tailored,
                category=category,
                reason=reason,
                job_requirement=related.requirement if related else "",
                evidence_source=(
                    f"gap_category_{related.category.name}" if related else "career_profile"
                ),
                evidence_text=related.candidate_evidence if related else change.original,
                validation_status=status,
                disposition=disposition,
            )
        )
    return changes
