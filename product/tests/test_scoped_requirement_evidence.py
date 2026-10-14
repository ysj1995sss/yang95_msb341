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


AI_TOOLS = ("Experience with generative AI and LLM-based tools (Claude Code, Cursor, GitHub Copilot) to perform "
            "and accelerate analyses, automated reporting, and build self-service data tools.")
KPI = "Automated monthly KPI reporting in Python, saving 6 hours a week"


def test_products_named_in_brackets_are_named_platforms_not_generic_evidence():
    """Round 6 bug hunt (a real Brex posting): this row was direct evidence through the word "reporting",
    so a rewrite claiming GitHub Copilot on a reporting bullet passed every check."""
    from resume_tailorer.analyzers.requirement_review import explicit_platform_terms, introduced_unsupported

    assert {"Claude Code", "Cursor", "GitHub Copilot"} <= set(explicit_platform_terms(AI_TOOLS))
    review = review_for(AI_TOOLS, candidate(KPI), {"work_experience[0]": "confirmed"})
    row = review.rows[0]
    assert not row.supported
    assert introduced_unsupported(KPI, KPI.replace("in Python", "in Python with GitHub Copilot"), review)


def test_a_broad_word_alone_does_not_lend_the_rest_of_the_requirement():
    """The same hole without brackets: one broad word ("reporting") made the whole requirement the
    bullet's own wording, so "using LLM-based tools" counted as grounded."""
    from resume_tailorer.analyzers.requirement_review import requirement_wording
    from resume_tailorer.diff_generator import DiffGenerator

    requirement = "Experience using generative AI and LLM-based tools to accelerate analyses and automated reporting."
    profile = candidate(KPI)
    review = review_for(requirement, profile, {"work_experience[0]": "confirmed"})
    row = review.rows[0]
    assert row.status == "partial" and "Shown only as" in row.reason
    assert row not in review.targets
    grounded = requirement_wording(KPI, review)
    assert "LLM" not in grounded
    fake = KPI.replace("in Python", "in Python using LLM-based tools")
    assert DiffGenerator().check_bullet_pair_fabrication_risk(KPI, fake, profile, grounded=grounded)


def test_one_of_several_named_tools_shown_is_direct_evidence():
    """Round 6: "(Looker, Hex, Tableau, or similar)" was "check yourself" though Tableau is shown: the
    "and" in "business intelligence and data visualization" read as "all of these tools"."""
    profile = candidate("Led a team of 3 analysts building weekly sales dashboards in Tableau")
    review = review_for("Experience with business intelligence and data visualization tools (Looker, Hex, Tableau, "
                        "or similar).", profile, {"work_experience[0]": "confirmed"})
    row = review.rows[0]
    assert row.status == "direct" and row.term_relation == "any"
    assert "Tableau" in row.shown_terms
    assert {"Looker", "Hex"} <= set(blocked_terms(review)[0])  # alternatives you don't show stay unclaimed


def test_transferable_evidence_is_named_in_the_requirement_s_own_words():
    """Round 6 bug hunt: "Strong communication skills…" was shown as "Partly shows “executive
    communication”": a qualifier the posting never used."""
    profile = candidate("Partnered with merchandising leads to explain sales trends")
    row = review_for("Strong communication skills and the ability to work effectively with stakeholders.", profile,
                     {"work_experience[0]": "confirmed"}).rows[0]
    assert row.status == "transferable"
    assert "“communication”" in row.reason and "executive" not in row.reason


def test_a_product_the_posting_names_is_never_borrowed_onto_the_evidence_bullet():
    """Round 6 bug hunt: "dashboards for regional managers in Hex and Mode" lent its whole wording,
    product names included, to a dashboards bullet, so "…in Tableau and Hex" passed every check."""
    from resume_tailorer.analyzers.requirement_review import requirement_wording
    from resume_tailorer.diff_generator import DiffGenerator

    bullet = "Built weekly sales dashboards for regional managers in Tableau"
    profile = candidate(bullet)
    review = review_for("Experience building weekly dashboards for regional managers in Hex and Mode", profile,
                        {"work_experience[0]": "confirmed"})
    grounded = requirement_wording(bullet, review)
    assert "regional" in grounded and "Hex" not in grounded and "Mode" not in grounded
    for fake in (bullet.replace("in Tableau", "in Tableau and Hex"), bullet.replace("in Tableau", "in Tableau and Mode")):
        assert DiffGenerator().check_bullet_pair_fabrication_risk(bullet, fake, profile, grounded=grounded), fake


def test_a_short_new_name_is_checked_but_an_opening_verb_is_not():
    from resume_tailorer.diff_generator import DiffGenerator

    bullet = "Built weekly sales dashboards in Tableau"
    profile = candidate(bullet)
    check = DiffGenerator().check_bullet_pair_fabrication_risk
    assert check(bullet, "Built weekly sales dashboards in Tableau and Hex", profile)
    assert check(bullet, "Built weekly AI sales dashboards in Tableau", profile)
    assert not check(bullet, "Led weekly sales dashboards in Tableau", profile)
