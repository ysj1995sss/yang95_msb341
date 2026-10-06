"""Pure view models for the evidence-first Tailoring Studio."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from resume_tailorer.analyzers.gap_analyzer import (
    GapCategory,
    GapItem,
    GapReport,
    find_unsupported_claims,
)
from resume_tailorer.artifacts.models import ResumeChange
from resume_tailorer.ui.design_system import SemanticStatus, display_optional, semantic_status


@dataclass(frozen=True)
class NamedMetric:
    label: str
    value: str


@dataclass(frozen=True)
class TailoringSummary:
    candidate_fit: NamedMetric
    resume_alignment: NamedMetric
    validation: SemanticStatus
    application_ready: bool
    review_count: int


@dataclass(frozen=True)
class ChangeGroups:
    reviewable: tuple[ResumeChange, ...]
    blocked: tuple[ResumeChange, ...]
    true_gaps: tuple[str, ...]


def _percentage(value: Any, empty_label: str = "Not assessed") -> str:
    if value is None:
        return empty_label
    return f"{float(value):.0%}"


def build_tailoring_summary(state: Mapping[str, Any]) -> TailoringSummary:
    report = state["report"]
    validation = semantic_status(report.validation.status)
    return TailoringSummary(
        candidate_fit=NamedMetric("Candidate fit", _percentage(report.candidate_fit)),
        resume_alignment=NamedMetric("Keyword overlap", _percentage(report.tailored_alignment)),
        validation=validation,
        application_ready=validation.application_ready,
        review_count=len(state.get("changes") or ()),
    )


def group_changes(
    changes: Iterable[ResumeChange], true_gaps: Iterable[str] = ()
) -> ChangeGroups:
    """Keep unsupported requirements out of the proposed-change deck."""
    gaps = tuple(str(gap) for gap in true_gaps if display_optional(gap, "") != "")
    gap_report = GapReport(
        items=[GapItem(requirement=gap, category=GapCategory.E, reason="UI safety gate") for gap in gaps],
        summary="UI safety gate",
    )
    blocked = tuple(
        change
        for change in changes
        if find_unsupported_claims(gap_report, change.proposed_text)
    )
    blocked_ids = {change.change_id for change in blocked}
    reviewable = tuple(change for change in changes if change.change_id not in blocked_ids)
    return ChangeGroups(reviewable=reviewable, blocked=blocked, true_gaps=gaps)


def safe_default_dispositions(
    changes: Iterable[ResumeChange], true_gaps: Iterable[str] = ()
) -> dict[str, str]:
    """Default any proposal that introduces a true gap to keeping the original."""
    return {
        change.change_id: "REJECTED"
        for change in group_changes(changes, true_gaps).blocked
    }
