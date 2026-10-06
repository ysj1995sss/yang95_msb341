"""Spec 010: unsupported claims are never added, on both tailoring paths. A stubbed model tries
to slip in terms the requirement review doesn't support; every attempt must be rejected."""

import json
from unittest.mock import MagicMock

import pytest

from resume_tailorer.analyzers.gap_analyzer import GapReport
from resume_tailorer.analyzers.job_analyzer import JobAnalyzer
from resume_tailorer.analyzers.requirement_review import build_review, format_for_prompt, introduced_unsupported
from resume_tailorer.llm.client import LLMClient
from resume_tailorer.parsers.docx_structure import Bullet
from resume_tailorer.tailorer.docx_bullet_tailorer import DocxBulletTailorer
from tests.fixtures.ats import POSTING, PROVENANCE, profile

SQL = "Built SQL dashboards used by 40 regional managers to track weekly campaign results"
LAUNCH = "Led on-time delivery of a 6-month store launch across 4 teams, with weekly risk reviews"
EMAIL = "Raised email campaign conversion 12% by redesigning audience segments"


@pytest.fixture(scope="module")
def analysis():
    return JobAnalyzer().analyze(POSTING)


@pytest.fixture(scope="module")
def review(analysis):
    return build_review(analysis, profile(), provenance=PROVENANCE, posting=POSTING)


def _tailorer(edits):
    llm = MagicMock(spec=LLMClient)
    llm.complete.return_value = json.dumps(edits)
    return DocxBulletTailorer(llm=llm), llm


def _bullets():
    return [Bullet(10, SQL, "work_experience", 0), Bullet(11, LAUNCH, "work_experience", 0),
            Bullet(12, EMAIL, "work_experience", 0)]


def test_word_path_rejects_unsupported_terms_and_keeps_safe_edits(analysis, review):
    tailorer, _llm = _tailorer([
        {"paragraph_index": 10, "change": "rewrite", "new_text": SQL + " (Snowflake)"},  # only listed
        {"paragraph_index": 11, "change": "rewrite", "new_text": LAUNCH + " as a CPA"},  # no evidence
        {"paragraph_index": 12, "change": "rewrite", "new_text": EMAIL + " (Tableau)"},  # preferred, missing
    ])
    result = tailorer.tailor_bullets(_bullets(), profile(), analysis, GapReport([], ""), review=review,
                                     max_repair_attempts=0)
    by_index = {e.paragraph_index: e for e in result.edits}
    for index in (10, 11, 12):
        assert by_index[index].changed is False, by_index[index]
        assert by_index[index].rejected_reason  # rejected by a guard, whichever caught it first
    # Snowflake is in the profile's skills list, so the older fabrication check lets it through;
    # only the requirement review knows it is merely listed.
    assert by_index[10].rejected_reason == "unsupported requirement term"
    final = " ".join(e.new_text for e in result.edits)
    for term in ("Snowflake", "CPA", "Tableau"):
        assert term not in final


def test_word_path_prompt_names_targets_with_evidence_and_a_do_not_add_list(analysis, review):
    tailorer, llm = _tailorer([])
    tailorer.tailor_bullets(_bullets(), profile(), analysis, GapReport([], ""), review=review)
    prompt = llm.complete.call_args.args[1]
    assert "REQUIREMENT REVIEW" in prompt and "MAKE CLEARER" in prompt and "DO NOT ADD" in prompt
    make_clearer = prompt.split("MAKE CLEARER")[1].split("DO NOT ADD")[0]
    for absent in ("Active CPA license", "Tableau dashboards", "Experience with Snowflake"):
        assert absent not in make_clearer  # never a target


def test_without_a_review_the_word_path_behaves_as_before(analysis):
    tailorer, _llm = _tailorer([{"paragraph_index": 10, "change": "rewrite", "new_text": SQL + " weekly"}])
    result = tailorer.tailor_bullets(_bullets(), profile(), analysis, GapReport([], ""))
    assert {e.paragraph_index: e for e in result.edits}[10].rejected_reason != "unsupported requirement term"


def test_a_listed_skill_may_stay_in_a_list_but_not_become_a_claim(review):
    assert introduced_unsupported("", "SQL, Snowflake, Excel, Segmentation", review) == []
    problems = introduced_unsupported(SQL, SQL + " in Snowflake", review)
    assert problems and "only listed" in problems[0]
    assert introduced_unsupported("", "Active CPA license holder", review)
    # Terms the candidate genuinely supports are never blocked.
    assert introduced_unsupported("Built dashboards", "Built SQL dashboards", review) == []


def test_free_form_changes_block_unsupported_terms(review):
    from resume_tailorer.artifacts.changes import build_freeform_changes
    from resume_tailorer.artifacts.models import ValidationStatus

    tailored = "\n".join([
        "Riley Park", "riley.park@example.com", "EXPERIENCE", "Marketing Analyst, Acme Retail, Jan 2022 - Present",
        f"- {SQL} in Snowflake",
        f"- {LAUNCH}",
        "SKILLS", "SQL, Snowflake, Excel, Segmentation",
    ])
    changes = build_freeform_changes(profile(), tailored, GapReport([], ""), review=review)
    flagged = [c for c in changes if "Snowflake" in (c.proposed_text or "") and "only listed" in (c.reason or "")]
    assert flagged and all(c.validation_status == ValidationStatus.FAIL for c in flagged)


def test_prompt_text_never_asks_to_add_a_missing_requirement(review):
    text = format_for_prompt(review)
    clearer, do_not = text.split("DO NOT ADD")
    assert "CPA" not in clearer and "CPA" in do_not
    assert "Evidence (Marketing Analyst at Acme Retail, bullet 2)" in clearer
