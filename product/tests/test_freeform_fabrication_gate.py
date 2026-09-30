"""Fabricated freeform claims must block the artifact until the user removes them."""

from dataclasses import replace

from resume_tailorer.analyzers.gap_analyzer import GapReport
from resume_tailorer.artifacts.changes import build_freeform_changes
from resume_tailorer.artifacts.models import ChangeDisposition, ValidationStatus
from resume_tailorer.models import CareerTruthProfile, WorkExperience
from resume_tailorer.pdf.content_validator import validate_pdf_content

PROFILE = CareerTruthProfile(
    contact_info={"name": "Alex Kim"},
    education=[],
    work_experience=[
        WorkExperience(
            employer="Acme",
            title="Analyst",
            dates="2020-2023",
            responsibilities=["Built weekly sales dashboards in SQL"],
            accomplishments=[],
        )
    ],
    skills=["SQL"],
    tools=[],
    certifications=[],
    accomplishments=[],
)
FABRICATED = "Awarded the Nobel Prize in Economics for pricing research"
TAILORED = f"Alex Kim\nAcme | Analyst | 2020-2023\n- Built weekly sales dashboards in SQL\n- {FABRICATED}\n"


def _fabricated_change():
    changes = build_freeform_changes(PROFILE, TAILORED, GapReport(items=[], summary=""))
    return next(c for c in changes if c.proposed_text == FABRICATED), changes


def test_fabricated_bullet_is_marked_failed_and_left_for_review():
    change, _ = _fabricated_change()
    assert change.validation_status is ValidationStatus.FAIL
    assert change.disposition is ChangeDisposition.PENDING
    assert "nobel" in change.reason.lower()


def test_fabricated_claim_in_pdf_blocks_validation():
    _, changes = _fabricated_change()
    findings = validate_pdf_content(TAILORED, PROFILE, changes)
    assert "UNSUPPORTED_CLAIM_PRESENT" in {f.code for f in findings}


def test_explicit_acceptance_downgrades_to_a_visible_warning():
    change, changes = _fabricated_change()
    accepted = [replace(c, disposition=ChangeDisposition.ACCEPTED) if c is change else c for c in changes]
    codes = {f.code for f in validate_pdf_content(TAILORED, PROFILE, accepted)}
    assert "UNSUPPORTED_CLAIM_PRESENT" not in codes
    assert "USER_CONFIRMED_UNVERIFIED_CLAIM" in codes


def test_rejecting_and_regenerating_unblocks():
    change, changes = _fabricated_change()

    rejected = [replace(c, disposition=ChangeDisposition.REJECTED) if c is change else c for c in changes]
    regenerated = TAILORED.replace(f"- {FABRICATED}\n", "")
    assert "UNSUPPORTED_CLAIM_PRESENT" not in {f.code for f in validate_pdf_content(regenerated, PROFILE, rejected)}


def test_manual_edit_is_validated_against_the_users_text():
    from resume_tailorer.artifacts.models import ChangeCategory, ResumeChange

    change = ResumeChange(
        change_id="c1", section="work_experience", source_index=0,
        original_text="Built weekly sales dashboards in SQL",
        proposed_text="Built weekly revenue dashboards in SQL and Python",
        category=ChangeCategory.REPHRASED, reason="", job_requirement="",
        evidence_source="career_profile", evidence_text="",
        validation_status=ValidationStatus.PASS,
        disposition=ChangeDisposition.MANUALLY_EDITED,
        manual_text="Built weekly sales dashboards in SQL for 3 regions",
    )
    text = "Alex Kim\nAcme | Analyst | 2020-2023\n- Built weekly sales dashboards in SQL for 3 regions\n"
    assert "ACCEPTED_CHANGE_MISSING" not in {f.code for f in validate_pdf_content(text, PROFILE, [change])}

    missing = "Alex Kim\nAcme | Analyst | 2020-2023\n- Something else entirely\n"
    assert "ACCEPTED_CHANGE_MISSING" in {f.code for f in validate_pdf_content(missing, PROFILE, [change])}
