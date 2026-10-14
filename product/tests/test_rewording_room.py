"""Item 5 (2026-10-13): tailoring proposed only tiny rewrites because the checks blocked ordinary
rewording, which decision 043 allows (level 1). Six of eight sensible rewrites of the fixture
bullets were refused. These cases must pass now, and the protections against invented claims
must still hold. Anonymized fixture (tests/fixtures/ats)."""

import json

import pytest

from resume_tailorer.analyzers.gap_analyzer import GapReport
from resume_tailorer.analyzers.job_analyzer import JobAnalyzer
from resume_tailorer.analyzers.requirement_review import build_review, requirement_wording
from resume_tailorer.artifacts.changes import build_freeform_changes
from resume_tailorer.artifacts.models import ValidationStatus
from resume_tailorer.parsers.docx_structure import Bullet
from resume_tailorer.tailorer.docx_bullet_tailorer import DocxBulletTailorer
from resume_tailorer.tailorer.resume_tailorer import ResumeTailorer
from tests.fixtures.ats import POSTING, PROVENANCE, profile

LAUNCH = "Led on-time delivery of a 6-month store launch across 4 teams, with weekly risk reviews"
DASHBOARDS = "Built SQL dashboards used by 40 regional managers to track weekly campaign results"
PM = "Acted as PM (project manager) for the 2024 loyalty program redesign"


@pytest.fixture(scope="module")
def review():
    return build_review(JobAnalyzer().analyze(POSTING), profile(), provenance=PROVENANCE, posting=POSTING)


def _check(review, original: str, new: str):
    """(changed, reason) after the Word path's checks."""
    tailorer = DocxBulletTailorer(llm=object())
    tailorer._review = review
    result = tailorer._parse_and_validate(json.dumps([{"paragraph_index": 1, "change": "rewrite", "new_text": new}]),
                                          [Bullet(1, original, "work_experience", 0)], profile())
    edit = result.edits[0]
    return edit.changed, edit.rejected_reason


# a. The job's own wording for a requirement the bullet is the evidence for.

def test_a_bullet_may_use_the_wording_of_the_requirement_it_is_evidence_for(review):
    # The review found this bullet shows "cross-team launches"; the job's own word is safe here.
    assert "cross-team" in requirement_wording(LAUNCH, review)
    changed, reason = _check(review, LAUNCH,
                             "Led on-time delivery of a 6-month cross-team store launch across 4 teams, weekly risk reviews")
    assert changed, reason


def test_that_wording_stays_blocked_on_a_bullet_that_is_not_its_evidence(review):
    changed, reason = _check(review, PM, "Acted as cross-team PM (project manager) for the 2024 loyalty program redesign")
    assert not changed and reason == "unverified content"


def test_a_requirement_term_the_evidence_does_not_show_stays_blocked(review):
    # "Tableau dashboards" is a requirement with no evidence: never added, even to the dashboards bullet.
    changed, _ = _check(review, DASHBOARDS,
                        "Built SQL and Tableau dashboards used by 40 regional managers to track weekly campaign results")
    assert not changed


def test_numbers_in_a_requirement_never_become_the_persons_numbers(review):
    changed, _ = _check(review, DASHBOARDS,
                        "Built SQL dashboards used by 40 regional managers over 4+ years to track weekly campaign results")
    assert not changed


def test_the_pdf_path_allows_the_same_wording(review):
    tailored = ("Riley Park\nAcme Retail | Marketing Analyst | Jan 2022 - Present\n"
                "- Led on-time delivery of a 6-month cross-team store launch across 4 teams, weekly risk reviews\n")
    changes = build_freeform_changes(profile(), tailored, GapReport(items=[], summary=""), review=review)
    launch = next(c for c in changes if "cross-team" in (c.proposed_text or ""))
    assert launch.validation_status is ValidationStatus.PASS, launch.reason


# b. Filler words may go; what was done, and every number, stays.

def test_a_filler_word_may_be_reworded(review):
    changed, reason = _check(review, DASHBOARDS, "Built SQL dashboards that let 40 regional managers track weekly campaign results")
    assert changed, reason


def test_a_word_that_says_what_was_done_still_must_stay(review):
    changed, reason = _check(review, LAUNCH,
                             "Led project management of an on-time 6-month store launch across 4 teams, weekly risk reviews")
    assert not changed and reason == "semantic drift"  # "delivery" is gone


def test_a_number_still_must_stay(review):
    changed, reason = _check(review, DASHBOARDS, "Built SQL dashboards that let regional managers track weekly campaign results")
    assert not changed and reason == "semantic drift"


# c. Room for a real rephrase: up to 25% longer.

def test_a_rewrite_up_to_a_quarter_longer_fits(review):
    new = "Built SQL dashboards used by 40 regional managers to track and review their weekly campaign results"
    assert 1.15 < len(new) / len(DASHBOARDS) <= 1.25
    changed, reason = _check(review, DASHBOARDS, new)
    assert changed, reason


def test_a_rewrite_much_longer_than_that_is_still_refused(review):
    new = DASHBOARDS + " across every region, reviewed in each weekly sales call with the team"
    changed, reason = _check(review, DASHBOARDS, new)
    assert not changed and reason == "length cap exceeded"


# d. The PDF instructions ask for every supported rephrase, as the Word ones do.

def test_the_pdf_instructions_no_longer_ask_to_leave_most_bullets_unchanged():
    prompt = ResumeTailorer(llm=object())._build_system_prompt()
    assert "most bullets should end up here" not in prompt and "2-4 bullets" not in prompt
    assert "EVERY bullet" in prompt and "MAKE CLEARER" in prompt
    for rule in ("NEVER fabricate", "SEMANTIC PRESERVATION", "CERTIFICATIONS", "SUMMARY TOOLS"):
        assert rule in prompt
    conservative = ResumeTailorer(llm=object())._build_system_prompt(conservative=True)
    assert "CONSERVATIVE MODE" in conservative  # the person's choice of minimal edits still holds


# Dogfood round 4: a real run proposed nothing because every target was "[already shown; keep it]".
# Requirements shown "in other words" counted as shown just because their evidence bullet was there.

def test_a_requirement_shown_only_in_other_words_is_not_yet_shown():
    from resume_tailorer.analyzers.requirement_review import (
        TRANSFERABLE, EvidenceRef, RequirementRow, shown_in,
    )
    bullet = "Led a team of 3 analysts building weekly sales dashboards in Tableau"
    row = RequirementRow("r4", "Collaboration: Demonstrated success working cross-functionally and building "
                         "relationships across business teams. Comfortable engaging stakeholders.", "required", False,
                         TRANSFERABLE, (), (EvidenceRef(bullet, "Analyst, bullet 1", "work_experience[0]", "experience", True),),
                         "Partly shows “collaboration” in other words.")
    assert shown_in(row, f"EXPERIENCE\n- {bullet}\n") is False  # the evidence is there; the requirement isn't named
    named = ("Led a cross-functionally aligned team of 3 analysts building relationships with business teams and "
             "engaging stakeholders through weekly sales dashboards")
    assert shown_in(row, f"EXPERIENCE\n- {named}\n") is True


def test_a_rewrite_that_changes_only_grammar_is_not_proposed(review):
    # Dogfood round 4: "to explain sales trends" -> ", explaining sales trends" cost a review for nothing.
    changed, reason = _check(review, "Partnered with merchandising leads to explain sales trends",
                             "Partnered with merchandising leads, explaining sales trends")
    assert not changed and reason is None
    changed, reason = _check(review, DASHBOARDS, "Built SQL dashboards that let 40 regional managers track weekly campaign results")
    assert changed, reason  # different words: still a proposal


def test_the_requirements_word_family_is_grounded_too():
    # Dogfood round 4: "to communicate sales insights" was refused for a job asking for a "clear and
    # effective communicator", because "communicate" and "communicator" didn't match.
    from resume_tailorer.diff_generator import DiffGenerator
    issues = DiffGenerator().check_bullet_pair_fabrication_risk(
        LAUNCH, LAUNCH + " to communicate risks", profile(), grounded="Clear and effective communicator.")
    assert issues == []
    unrelated = DiffGenerator().check_bullet_pair_fabrication_risk(
        LAUNCH, LAUNCH + " to communicate risks", profile(), grounded="Strong commercial instincts.")
    assert unrelated  # "communicate" isn't in the family of anything grounded


def test_a_grammar_only_rewrite_on_a_pdf_resume_is_undone_before_review():
    from resume_tailorer.artifacts.changes import revert_grammar_only_rewrites
    from resume_tailorer.models import CareerTruthProfile, WorkExperience

    person = CareerTruthProfile(
        contact_info={"name": "Sam Example"}, education=[], skills=[], tools=[], certifications=[], accomplishments=[],
        work_experience=[WorkExperience(employer="Example Co", title="Analyst", dates="2021 - Present", accomplishments=[],
                                        responsibilities=["Partnered with merchandising leads to explain sales trends",
                                                          "Built SQL pipelines feeding pricing reviews for 120 stores"])])
    tailored = ("Sam Example\nExample Co | Analyst | 2021 - Present\n"
                "- Partnered with merchandising leads, explaining sales trends\n"
                "- Built SQL pipelines supporting pricing reviews across 120 stores\n")
    cleaned = revert_grammar_only_rewrites(person, tailored)
    assert "- Partnered with merchandising leads to explain sales trends" in cleaned
    assert "supporting pricing reviews across 120 stores" in cleaned  # a real rewrite stays
    changes = build_freeform_changes(person, cleaned, GapReport(items=[], summary=""))
    assert [c.proposed_text for c in changes] == ["Built SQL pipelines supporting pricing reviews across 120 stores"]
