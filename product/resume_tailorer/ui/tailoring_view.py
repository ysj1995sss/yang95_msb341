"""Pure view models for the evidence-first Tailoring Studio."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

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
        resume_alignment=NamedMetric("Resume alignment", _percentage(report.tailored_alignment)),
        validation=validation,
        application_ready=validation.application_ready,
        review_count=len(state.get("changes") or ()),
    )


def group_changes(
    changes: Iterable[ResumeChange], true_gaps: Iterable[str] = ()
) -> ChangeGroups:
    """Keep unsupported requirements out of the proposed-change deck."""
    gaps = tuple(str(gap) for gap in true_gaps if display_optional(gap, "") != "")
    lowered = tuple(gap.casefold() for gap in gaps)
    reviewable = tuple(
        change
        for change in changes
        if not any(gap in change.proposed_text.casefold() for gap in lowered)
    )
    return ChangeGroups(reviewable=reviewable, true_gaps=gaps)
