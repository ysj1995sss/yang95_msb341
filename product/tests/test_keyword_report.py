"""Spec 011: each named term has its own status, and Tailor's keyword report says what a version
added and what is still left out, and why. Anonymized fixtures."""

import pytest

from resume_tailorer.analyzers.job_analyzer import JobAnalyzer
from resume_tailorer.analyzers.requirement_review import (
    DIRECT, NONE, PARTIAL, blocked_terms, build_review, keyword_report, profile_text_for_report, unshown_targets,
)
from tests.fixtures.ats import POSTING, PROVENANCE, profile

MIXED = ("Data Analyst at Northwind.\nRequirements:\n- SQL, Tableau and dashboard reporting for business partners.\n"
         "- Active CPA license.\nPreferred Qualifications:\n- Experience with Snowflake.\n")


@pytest.fixture(scope="module")
def mixed():
    return build_review(JobAnalyzer().analyze(MIXED), profile(), provenance=PROVENANCE, posting=MIXED)


def test_a_requirement_with_one_of_two_named_tools_is_partly_supported(mixed):
    row = next(r for r in mixed.rows if r.text.startswith("SQL, Tableau"))
    assert row.status == PARTIAL and row.label == "Partly supported"
    assert dict(row.term_status) == {"SQL": DIRECT, "Tableau": NONE}
    assert "Shown: SQL" in row.reason and "Tableau (no evidence)" in row.reason
    assert row.shown_terms == ("SQL",)
    assert "only partly" in mixed.summary


def test_the_supported_term_is_a_target_and_the_missing_one_is_blocked(mixed):
    never, _listed = blocked_terms(mixed)
    assert "Tableau" in never and "SQL" not in never
    targets = unshown_targets(mixed, "Marketing analyst. Excel.")
    assert any(r.text.startswith("SQL, Tableau") for r in targets)


def test_keyword_report_lists_added_already_and_left_out_with_reasons(mixed):
    original = profile_text_for_report(profile())
    tailored = original + "\nBuilt SQL dashboards for business partners."
    report = keyword_report(mixed, original.replace("SQL", "S Q L"), tailored)
    assert "SQL" in report.added
    reasons = dict(report.left_out)
    assert reasons["Tableau"] == NONE and reasons["CPA"] == NONE
    assert reasons.get("Snowflake") is None  # in the skills list, so already named by the resume
    assert "Snowflake" in report.already


def test_keyword_report_groups_left_out_terms_by_why(analysis_and_review=None):
    review = build_review(JobAnalyzer().analyze(POSTING), profile(), provenance=PROVENANCE, posting=POSTING)
    resume = "Marketing analyst. Excel."  # a resume that names almost nothing
    reasons = dict(keyword_report(review, resume, resume).left_out)
    assert reasons["SQL"] == "not_named"  # evidence exists, just not named in this text
    assert reasons["Snowflake"] == "mention" and reasons["Salesforce"] == "unconfirmed"
    assert reasons["Tableau"] == "none" and reasons["CPA"] == "none"


def test_the_view_links_an_added_term_to_the_change_that_added_it(mixed):
    from types import SimpleNamespace

    from resume_tailorer.ui.requirement_review_view import keyword_report_view

    change = SimpleNamespace(change_id="c7", original_text="Built dashboards for partners",
                             proposed_text="Built SQL dashboards for partners", manual_text=None)
    p = profile()
    p.work_experience[0].responsibilities = ["Built dashboards for partners"]
    p.skills = ["Excel"]
    view = keyword_report_view(mixed, {"profile": p, "tailored_text": "Built SQL dashboards for partners",
                                       "changes": [change]})
    assert {"term": "SQL", "change_id": "c7"} in view["added"]
    labels = {group["label"]: group["terms"] for group in view["left_out"]}
    assert "Tableau" in labels["No evidence (never added)"]
