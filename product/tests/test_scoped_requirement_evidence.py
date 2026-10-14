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
    'Experience with analytics software nebulaplatform.',
    'Proficiency in analytics tools nebulaplatform.',
    'Experience with The Trade Desk analytics.',
    'Experience with The NebulaForms analytics software.',
    'EXPERIENCE WITH NebulaForms analytics.',
])
def test_unknown_explicit_platform_patterns_do_not_inherit_analytics(requirement):
    row = review_for(requirement).rows[0]
    assert row.status == 'check' and not row.supported


@pytest.mark.parametrize('requirement', ['Experience with analytics software.', 'Experience with analytics tools and reporting.'])
def test_generic_descriptor_without_product_does_not_invent_a_named_platform(requirement):
    row = review_for(requirement).rows[0]
    assert row.status != 'check'
    assert not any(term.lower() == 'and' for term in row.terms)


def test_generic_caution_does_not_turn_any_and_unless_into_product_names():
    from resume_tailorer.analyzers.requirement_review import explicit_platform_terms
    caution = 'Do not claim experience with any platform unless it is supported by your actual work.'
    assert explicit_platform_terms(caution) == ()


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


@pytest.mark.parametrize("requirement", [
    "1+ years of technical work experience using analytical tools and writing analytical reports",
    "Experience in BaaS, DevRel or open source dev tool companies, connecting marketing spend to revenue",
    "Experience using statistical software and visualization tools",
])
def test_ordinary_words_after_tool_wording_are_not_product_names(requirement):
    # Dogfood round 4: "analytical" and "companies" were read as unknown platforms, which made
    # the rows "check yourself" instead of being judged.
    from resume_tailorer.analyzers.requirement_review import explicit_platform_terms
    assert explicit_platform_terms(requirement) == ()


def test_e_g_is_not_a_product_name():
    from resume_tailorer.analyzers.requirement_review import explicit_platform_terms
    found = explicit_platform_terms("Advanced proficiency in enterprise HR platforms e.g. Workday, ServiceNow, Greenhouse.")
    assert "e.g" not in found and "ServiceNow" in found


@pytest.mark.parametrize("requirement", [
    "Fluency in support platform data — you know how Zendesk (or equivalent) is structured",
    "Experience with BI tools administration and reporting",
    "Hands-on software engineering or platform integrations experience",
])
def test_common_nouns_after_platform_or_tool_are_not_product_names(requirement):
    # Risk-check run, 2026-10-13: "platform data" made "data" an unknown product, so every rewrite
    # containing "data" was refused as "adds data, which you haven't shown evidence for".
    from resume_tailorer.analyzers.requirement_review import explicit_platform_terms
    found = {t.lower() for t in explicit_platform_terms(requirement)}
    assert not found & {"data", "administration", "integrations", "engineering"}
