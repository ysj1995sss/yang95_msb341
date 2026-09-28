from dataclasses import FrozenInstanceError

import pytest

from resume_tailorer.artifacts.models import (
    ArtifactValidation,
    ChangeCategory,
    ChangeDisposition,
    FindingCategory,
    FindingSeverity,
    ResumeChange,
    ValidationFinding,
    ValidationStatus,
)


def test_validation_status_is_derived_from_findings():
    warning = ValidationFinding(
        "VISUAL_CHECK_SKIPPED",
        FindingSeverity.WARNING,
        FindingCategory.VISUAL,
        "Visual check unavailable",
    )

    result = ArtifactValidation.from_findings([warning])

    assert result.status is ValidationStatus.WARNING
    assert result.has_code("VISUAL_CHECK_SKIPPED")


def test_fail_takes_precedence_over_warning():
    findings = [
        ValidationFinding(
            "LINK_LOST", FindingSeverity.WARNING, FindingCategory.ATS, "Link lost"
        ),
        ValidationFinding(
            "PAGE_COUNT_CHANGED",
            FindingSeverity.FAIL,
            FindingCategory.VISUAL,
            "Page count changed",
        ),
    ]

    result = ArtifactValidation.from_findings(findings)

    assert result.status is ValidationStatus.FAIL


def test_no_findings_is_a_pass():
    assert ArtifactValidation.from_findings([]).status is ValidationStatus.PASS


def test_shared_models_are_immutable():
    change = ResumeChange(
        change_id="run-1:paragraph-7",
        section="work_experience",
        source_index=7,
        original_text="Led launch",
        proposed_text="Led cross-functional launch",
        category=ChangeCategory.REPHRASED,
        reason="Matches verified job language",
        job_requirement="cross-functional leadership",
        evidence_source="original_resume",
        evidence_text="Led launch",
        validation_status=ValidationStatus.PASS,
        disposition=ChangeDisposition.PENDING,
    )

    with pytest.raises(FrozenInstanceError):
        change.proposed_text = "Changed after creation"

