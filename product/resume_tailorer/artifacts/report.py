"""Build the canonical final report without recalculating upstream scores."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from resume_tailorer.analyzers.gap_analyzer import GapCategory, GapReport

from .models import ArtifactMetadata, ArtifactValidation, FidelityMode, FinalApplicationReport


_FIT_DIMENSIONS = (
    "eligibility",
    "core_capabilities",
    "preferred_qualifications",
    "evidence_confidence",
)


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def build_final_report(
    *,
    candidate_fit: float | None,
    fit_breakdown: Mapping[str, Any],
    original_alignment: float,
    tailored_alignment: float,
    gap_report: GapReport,
    validation: ArtifactValidation,
    artifacts: Iterable[ArtifactMetadata] = (),
    company: str = "",
    role: str = "Target Role",
    fidelity_mode: FidelityMode = FidelityMode.RECONSTRUCTED,
    unsupported_claims: Iterable[str] = (),
) -> FinalApplicationReport:
    """Assemble already-computed results into the shared report model."""
    breakdown = dict(fit_breakdown)
    for dimension in _FIT_DIMENSIONS:
        if breakdown.get(dimension) is None:
            breakdown[dimension] = "NOT_ASSESSED"

    by_category = {
        category: [item.requirement for item in gap_report.items if item.category is category]
        for category in GapCategory
    }
    strong = _unique(
        [*breakdown.get("strong_matches", ()), *by_category[GapCategory.A], *by_category[GapCategory.B]]
    )
    partial = _unique(
        [*breakdown.get("partial_matches", ()), *by_category[GapCategory.C], *by_category[GapCategory.D]]
    )
    true_gaps = _unique([*breakdown.get("true_gaps", ()), *by_category[GapCategory.E]])

    return FinalApplicationReport(
        company=company,
        role=role,
        candidate_fit=candidate_fit,
        fit_breakdown=breakdown,
        original_alignment=original_alignment,
        tailored_alignment=tailored_alignment,
        strong_matches=strong,
        partial_matches=partial,
        true_gaps=true_gaps,
        unsupported_claims=_unique(unsupported_claims),
        validation=validation,
        fidelity_mode=fidelity_mode,
        original_page_count=validation.original_page_count,
        tailored_page_count=validation.tailored_page_count,
        artifacts=tuple(artifacts),
    )
