"""Spec 010 acceptance cases for the requirement review, on an anonymized posting and profile
(tests/fixtures/ats). Each status must cite the exact passage it rests on."""

from dataclasses import replace

import pytest

from resume_tailorer.analyzers.job_analyzer import JobAnalyzer
from resume_tailorer.analyzers.requirement_review import (
    CHECK, DIRECT, MENTION, NONE, TRANSFERABLE, UNCONFIRMED, build_review, with_resume,
)
from tests.fixtures.ats import POSTING, PROVENANCE, profile


@pytest.fixture(scope="module")
def analysis():
    return JobAnalyzer().analyze(POSTING)


@pytest.fixture(scope="module")
def review(analysis):
    return build_review(analysis, profile(), provenance=PROVENANCE, posting=POSTING)


def row(review, start):
    return next(r for r in review.rows if r.text.startswith(start))


def test_exact_term_present_but_unsupported_is_mentioned_only(review):
    snowflake = row(review, "Experience with Snowflake")
    assert snowflake.status == MENTION and snowflake.section == "required"
    assert [e.source for e in snowflake.evidence] == ["Skills list"] and snowflake.evidence[0].text == "Snowflake"
    assert snowflake not in review.targets  # never built into a new claim


def test_equivalent_wording_genuinely_supported_is_transferable_with_the_exact_bullet(review):
    pm = row(review, "Proven project management")
    assert pm.status == TRANSFERABLE
    bullet = "Led on-time delivery of a 6-month store launch across 4 teams, with weekly risk reviews"
    assert pm.evidence[0].text == bullet  # quoted exactly, never paraphrased
    assert pm.evidence[0].source == "Marketing Analyst at Acme Retail, bullet 2" and pm.evidence[0].confirmed
    assert pm in review.targets


def test_ambiguous_acronym_is_never_counted_as_evidence(review):
    pm = row(review, "PM experience partnering")
    assert pm.status == CHECK and "can mean different things" in pm.reason
    assert pm not in review.targets


def test_ambiguous_acronym_with_the_same_meaning_on_both_sides_counts(analysis):
    p = profile()
    p.work_experience[0].responsibilities[2] = "Acted as PM (product manager) for the loyalty app roadmap"
    pm = row(build_review(analysis, p, provenance=PROVENANCE, posting=POSTING), "PM experience partnering")
    assert pm.status != CHECK


def test_preferred_skill_missing_stays_a_visible_preferred_gap(review):
    tableau = row(review, "Tableau dashboards")
    assert tableau.status == NONE and tableau.section == "preferred" and not tableau.hard_gate
    assert tableau.evidence == ()
    assert tableau not in review.targets and tableau in review.not_to_add


def test_generic_word_never_stands_in_for_a_named_tool(review):
    # "dashboards" appears in a SQL bullet; that is not evidence of Tableau.
    assert row(review, "Tableau dashboards").status == NONE


def test_required_credential_absent_is_a_hard_gate_shown_first(review):
    cpa = row(review, "Active CPA license")
    assert cpa.status == NONE and cpa.hard_gate and cpa.section == "required"
    assert "won't be added" in cpa.reason
    required = [r for r in review.rows if r.section == "required"]
    assert required[0] is cpa  # missing hard gates are never buried
    assert "required credential or threshold not found" in review.summary


def test_evidence_only_in_unconfirmed_facts_is_unconfirmed_until_confirmed(analysis, review):
    sf = row(review, "Experience with Salesforce")
    assert sf.status == UNCONFIRMED and not sf.evidence[0].confirmed
    assert sf.evidence[0].text == "Cleaned Salesforce campaign data before each quarterly review"
    assert sf not in review.targets and "Confirm them in Career Profile" in sf.reason

    confirmed = {**PROVENANCE, "work_experience[1]": "confirmed"}
    after = row(build_review(analysis, profile(), provenance=confirmed, posting=POSTING), "Experience with Salesforce")
    assert after.status == DIRECT and after.evidence[0].confirmed


def test_direct_evidence_names_what_was_found(review):
    sql = row(review, "Advanced SQL")
    assert sql.status == DIRECT and sql.evidence[0].text.startswith("Built SQL dashboards")
    degree = row(review, "Bachelor's degree")
    assert degree.status == DIRECT and degree.evidence[0].kind == "education"


def test_years_are_left_for_the_person_to_check(review):
    years = row(review, "4+ years")
    assert "check your dates" in years.reason


def test_shown_in_resume_marks_supported_rows_only(review):
    resume = "Built SQL dashboards used by 40 regional managers. Snowflake. Excel."
    rows = {r.text[:20]: r for r in with_resume(review, resume).rows}
    assert rows["Advanced SQL for ana"].shown_in_resume is True
    assert rows["Proven project manag"].shown_in_resume is False  # supported but not shown yet
    assert rows["Experience with Snow"].shown_in_resume is None  # not supported: not a "shown" question


def test_untracked_profiles_count_as_the_persons_own_facts(analysis):
    review = build_review(analysis, profile(), provenance=None, posting=POSTING)
    assert row(review, "Experience with Salesforce").status == DIRECT


def test_summary_counts_required_and_preferred(review):
    assert review.summary.startswith("Required: 4 of 7 with evidence · Preferred: 0 of 2")


def test_a_review_survives_the_review_file_round_trip(review):
    from resume_tailorer.review_store import decode, encode
    import json

    restored = decode(json.loads(json.dumps(encode({"requirement_review": review}))))["requirement_review"]
    assert restored == review and restored.rows[0].label


def test_posting_without_requirement_sections_falls_back_to_listed_skills():
    analysis = JobAnalyzer().analyze("Marketing Analyst\nWe use SQL and Tableau every day to report on campaigns.")
    analysis = replace(analysis, structured_requirements=[], required_qualifications=[], preferred_qualifications=[])
    review = build_review(analysis, profile(), posting="")
    assert review.rows or review.summary == "No requirement list was found in this posting."


def test_a_bachelors_requirement_matches_a_bs_even_when_the_degree_wasnt_split_out(analysis):
    """Found in the spec 010 supervised run: "BS Economics, State University" parsed as one
    institution string, so "Bachelor's degree in Business, Economics" showed no evidence."""
    from resume_tailorer.models import EducationEntry

    p = profile()
    p.education = [EducationEntry(degree="", field="", institution="BS Economics, State University, 2019", year=2019)]
    degree = row(build_review(analysis, p, provenance=PROVENANCE, posting=POSTING), "Bachelor's degree")
    assert degree.status == DIRECT and "Check that the field matches" in degree.reason


def test_transferable_evidence_is_not_shown_until_the_requirement_is_named(review):
    rows = {r.text[:20]: r for r in with_resume(review, LAUNCH_ONLY).rows}
    assert rows["Proven project manag"].shown_in_resume is False  # evidence there, term not named
    named = with_resume(review, LAUNCH_ONLY + " Project management of the launch.").rows
    assert next(r for r in named if r.text.startswith("Proven project")).shown_in_resume is True


LAUNCH_ONLY = "Led on-time delivery of a 6-month store launch across 4 teams, with weekly risk reviews."


def test_a_state_abbreviation_is_never_read_as_a_masters_degree():
    from resume_tailorer.analyzers.requirement_review import _Passage, _degree_evidence

    boston = _Passage("BS Economics, Boston University, Boston, MA, 2019", "Education", "education[0]", "education")
    assert _degree_evidence("Master's degree in Marketing", [boston]) is None
    assert _degree_evidence("Bachelor's degree required", [boston])[1] == "bachelor's"
    ms = _Passage("MS in Business Analytics, State University, 2021", "Education", "education[0]", "education")
    assert _degree_evidence("Master's degree preferred", [ms])[1] == "master's"
    assert _degree_evidence("Bachelor's degree", [ms])[1] == "master's"  # a higher degree meets it
