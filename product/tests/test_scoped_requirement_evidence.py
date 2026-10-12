"""Named products cannot inherit evidence from a generic capability (spec 016)."""
import pytest

from resume_tailorer.analyzers.job_analyzer import JobAnalyzer
from resume_tailorer.analyzers.requirement_review import build_review, blocked_terms
from resume_tailorer.models import CareerTruthProfile, WorkExperience


def candidate(extra_bullet=None, listed=()):
    bullets = ["Built SQL dashboards and analytics reports."]
    if extra_bullet:
        bullets.append(extra_bullet)
    return CareerTruthProfile(
        contact_info={"name": "Synthetic Candidate"}, education=[],
        work_experience=[WorkExperience("Example", "Analyst", "2021-2025", bullets, [])],
        skills=list(listed), tools=[], certifications=[], accomplishments=[], summary="",
    )


def review_for(requirement, profile=None, provenance=None):
    posting = "Required Qualifications:\n- " + requirement
    return build_review(JobAnalyzer().analyze(posting), profile or candidate(),
                        provenance=provenance, posting=posting)


def test_generic_analytics_does_not_establish_qualtrics():
    review = review_for("Experience with analytics platforms such as Qualtrics.")
    row = review.rows[0]
    assert row.status != "direct"
    assert ("Qualtrics", "none") in row.term_status
    assert "Qualtrics" not in row.shown_terms
    assert not row.hard_gate
    assert "Qualtrics" in blocked_terms(review)[0]


def test_conjunction_requires_its_named_tools_not_just_sql():
    row = review_for("Experience with SQL and Qualtrics.").rows[0]
    assert row.status == "partial"
    assert dict(row.term_status) == {"SQL": "direct", "Qualtrics": "none"}
    assert row.shown_terms == ("SQL",)


@pytest.mark.parametrize("name", ["NebulaForms", "nebulaplatform"])
def test_an_unknown_explicit_platform_is_check_yourself(name):
    row = review_for(f"Experience with analytics platforms such as {name}.").rows[0]
    assert row.status == "check"
    assert not row.supported


@pytest.mark.parametrize('requirement', [
    'Experience with nebulaplatform analytics.',
    'Experience with analytics software NebulaForms.',
    'EXPERIENCE WITH NebulaForms analytics.',
])
def test_unknown_explicit_platform_patterns_do_not_inherit_analytics(requirement):
    row = review_for(requirement).rows[0]
    assert row.status == 'check' and not row.supported


@pytest.mark.parametrize("bullet,listed,provenance,want", [
    (None, (), None, "none"),
    (None, ("Qualtrics",), None, "mention"),
    ("Built Qualtrics surveys for customer research.", (), {"work_experience[0]": "resume"}, "unconfirmed"),
    ("Built Qualtrics surveys for customer research.", (), {"work_experience[0]": "confirmed"}, "direct"),
])
def test_qualtrics_uses_its_own_evidence(bullet, listed, provenance, want):
    row = review_for("Experience with Qualtrics.", candidate(bullet, listed), provenance).rows[0]
    assert row.status == want
    assert row.term_status == (("Qualtrics", want),)
    if want == "direct":
        assert row.evidence[0].text == "Built Qualtrics surveys for customer research."


def test_alternative_does_not_require_or_authorize_both_tools():
    review = review_for("Experience with Qualtrics or SurveyMonkey.",
                        candidate("Built SurveyMonkey surveys for customer research."))
    row = review.rows[0]
    assert row.status == "direct"
    assert row.shown_terms == ("SurveyMonkey",)
    assert row.term_status == (("Qualtrics", "none"), ("SurveyMonkey", "direct"))
    assert "Qualtrics" in blocked_terms(review)[0]


def test_an_example_explains_generic_support_without_authorizing_the_product():
    review = review_for("Experience with analytics platforms such as Qualtrics.")
    row = review.rows[0]
    assert row.status in ("partial", "check")
    assert "Qualtrics" not in row.shown_terms
    assert "Qualtrics" in blocked_terms(review)[0]
