from resume_tailorer.artifacts.models import (
    ArtifactValidation,
    ChangeCategory,
    ChangeDisposition,
    FidelityMode,
    FinalApplicationReport,
    ResumeChange,
    ValidationStatus,
)
from resume_tailorer.ui.tailoring_view import (
    build_tailoring_summary,
    group_changes,
    safe_default_dispositions,
)


def _change(proposed: str = "Built reliable GraphQL APIs") -> ResumeChange:
    return ResumeChange(
        change_id="c1",
        section="experience",
        source_index=0,
        original_text="Built reliable APIs",
        proposed_text=proposed,
        category=ChangeCategory.REPHRASED,
        reason="Make the demonstrated result clearer",
        job_requirement="Reliable API delivery",
        evidence_source="resume",
        evidence_text="Built reliable APIs",
        validation_status=ValidationStatus.PASS,
        disposition=ChangeDisposition.PENDING,
    )


def _report() -> FinalApplicationReport:
    return FinalApplicationReport(
        company="Example Co",
        role="Platform Engineer",
        candidate_fit=0.82,
        fit_breakdown={},
        original_alignment=0.48,
        tailored_alignment=0.71,
        strong_matches=("Python",),
        partial_matches=("Cloud",),
        true_gaps=("GraphQL",),
        unsupported_claims=(),
        validation=ArtifactValidation(status=ValidationStatus.WARNING),
        fidelity_mode=FidelityMode.PRESERVED,
        original_page_count=1,
        tailored_page_count=1,
    )


def test_candidate_fit_and_alignment_stay_separate():
    summary = build_tailoring_summary({"report": _report(), "changes": [_change()]})
    assert summary.candidate_fit.label == "Candidate fit"
    assert summary.candidate_fit.value == "82%"
    assert summary.resume_alignment.label == "Keyword overlap"  # spec 010: not an ATS score
    assert summary.resume_alignment.value == "71%"


def test_warning_artifact_is_not_application_ready():
    summary = build_tailoring_summary({"report": _report(), "changes": [_change()]})
    assert summary.validation.label == "Review required"
    assert summary.application_ready is False


def test_missing_requirements_never_enter_change_deck():
    groups = group_changes([_change()], true_gaps=("GraphQL",))
    assert groups.true_gaps == ("GraphQL",)
    assert groups.reviewable == ()
    assert groups.blocked == (_change(),)


def test_gap_containing_proposal_is_rejected_before_regeneration():
    assert safe_default_dispositions([_change()], ("GraphQL",)) == {"c1": "REJECTED"}


def test_short_gap_does_not_reject_a_substring_inside_a_real_word():
    assert safe_default_dispositions([_change("Built reliable APIs")], ("R",)) == {}
    assert safe_default_dispositions([_change("Led governance reviews")], ("Go",)) == {}


def test_a_proposal_that_failed_its_truth_check_starts_as_original_kept():
    """Dogfood, 2026-10-13: a summary rewrite that failed its check was built into the first resume,
    so the whole resume read "Failed validation: not usable" and couldn't be downloaded, though a
    failed change can't even be accepted. It starts kept-original, like a missing-requirement claim."""
    from dataclasses import replace

    failed = replace(_change("Built reliable APIs and led platform work"), validation_status=ValidationStatus.FAIL)
    assert safe_default_dispositions([failed], ()) == {"c1": "REJECTED"}
    assert safe_default_dispositions([_change("Built reliable, tested APIs")], ()) == {}


def test_a_proposal_the_model_checks_already_turned_down_needs_no_default():
    """Code review, 2026-10-13: a REJECTED-category change (the tailorer's own checks restored the
    original) also has a FAIL status; defaulting it forced a needless rebuild on most runs."""
    from dataclasses import replace

    turned_down = replace(_change("Built reliable APIs"), category=ChangeCategory.REJECTED,
                          validation_status=ValidationStatus.FAIL)
    assert safe_default_dispositions([turned_down], ()) == {}
