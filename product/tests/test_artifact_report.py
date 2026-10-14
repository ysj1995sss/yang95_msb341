from resume_tailorer.analyzers.gap_analyzer import GapCategory, GapItem, GapReport
from resume_tailorer.artifacts.changes import build_freeform_changes
from resume_tailorer.artifacts.models import (
    ArtifactValidation,
    ChangeCategory,
    ValidationStatus,
)
from resume_tailorer.artifacts.report import build_final_report
from resume_tailorer.models import CareerTruthProfile, WorkExperience


def _profile(accomplishment: str) -> CareerTruthProfile:
    return CareerTruthProfile(
        contact_info={},
        education=[],
        work_experience=[
            WorkExperience(
                employer="Example Co",
                title="Manager",
                dates="2022-2025",
                responsibilities=[],
                accomplishments=[accomplishment],
            )
        ],
        skills=[],
        tools=[],
        certifications=[],
        accomplishments=[],
    )


def _gaps() -> GapReport:
    return GapReport(
        items=[
            GapItem(
                requirement="Cross-functional leadership",
                category=GapCategory.B,
                reason="Supported by verified team leadership",
                candidate_evidence="Led a 10-person team across launches",
            ),
            GapItem(
                requirement="Kubernetes administration",
                category=GapCategory.E,
                reason="Not found in profile; do not add",
                candidate_evidence="None",
            ),
        ],
        summary="One supported match and one true gap.",
    )


def test_final_report_copies_cf_v2_score_and_marks_unassessed_dimensions():
    report = build_final_report(
        candidate_fit=0.78,
        fit_breakdown={
            "scoring_version": "cf-v2",
            "eligibility": 0.9,
            "core_capabilities": 0.8,
            "preferred_qualifications": None,
            "evidence_confidence": 0.7,
        },
        original_alignment=0.52,
        tailored_alignment=0.81,
        gap_report=_gaps(),
        validation=ArtifactValidation(status=ValidationStatus.PASS),
        artifacts=(),
    )

    assert report.candidate_fit == 0.78
    assert report.fit_breakdown["scoring_version"] == "cf-v2"
    assert report.fit_breakdown["preferred_qualifications"] == "NOT_ASSESSED"
    assert report.fit_breakdown["eligibility"] == 0.9
    assert report.strong_matches == ("Cross-functional leadership",)
    assert report.true_gaps == ("Kubernetes administration",)


def test_freeform_change_is_linked_to_requirement_and_evidence():
    changes = build_freeform_changes(
        _profile("Led a 10-person team across launches"),
        "- Led a 10-person cross-functional team across launches\n",
        _gaps(),
    )

    assert len(changes) == 1
    assert changes[0].job_requirement == "Cross-functional leadership"
    assert changes[0].evidence_text == "Led a 10-person team across launches"
    # "cross-functional" is not in the verified facts, so the change needs review.
    assert changes[0].validation_status is ValidationStatus.FAIL
    assert "cross-functional" in changes[0].reason


def test_ambiguous_freeform_pairing_requires_review_instead_of_being_accepted():
    changes = build_freeform_changes(
        _profile("Built financial models for annual planning"),
        "- Managed Kubernetes clusters in production\n",
        _gaps(),
    )

    assert len(changes) == 1
    assert changes[0].category is ChangeCategory.REJECTED
    assert changes[0].validation_status is ValidationStatus.FAIL
    assert "ambiguous" in changes[0].reason.lower()


def test_a_rephrased_bullet_is_supported_by_itself_not_by_another_bullet():
    # Dogfood round 4: a rewrite of "Built SQL pipelines…" showed "Led a team… dashboards" as its
    # supporting fact, because that was the evidence of the requirement the wording matched best.
    profile = CareerTruthProfile(
        contact_info={}, education=[], skills=[], tools=[], certifications=[], accomplishments=[],
        work_experience=[WorkExperience(employer="Example Co", title="Analyst", dates="2021-2024", accomplishments=[],
                                        responsibilities=["Led a team of 3 analysts building weekly dashboards",
                                                          "Built SQL pipelines feeding pricing reviews for 120 stores"])])
    gaps = GapReport(items=[GapItem(requirement="SQL and dashboards for pricing teams", category=GapCategory.A,
                                    reason="Shown", candidate_evidence="Led a team of 3 analysts building weekly dashboards")],
                     summary="")
    tailored = ("- Led a team of 3 analysts building weekly dashboards\n"
                "- Built SQL pipelines supporting pricing reviews across 120 stores\n")
    change = next(c for c in build_freeform_changes(profile, tailored, gaps) if "pipelines" in (c.proposed_text or ""))
    assert change.evidence_text == "Built SQL pipelines feeding pricing reviews for 120 stores"
