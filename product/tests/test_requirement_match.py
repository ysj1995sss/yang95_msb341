"""Decision 047: Match is the share of a posting's stated requirements a person's facts show. A
profile that shows one requirement in ten matches about 10%, not the 85-96% the old fit gave
almost every job (builder, 2026-10-13). Synthetic posting and profile."""

from dataclasses import replace

import pytest

from resume_tailorer.analyzers.requirement_review import (
    CHECK, DIRECT, MENTION, NONE, PARTIAL, TRANSFERABLE, UNCONFIRMED, RequirementReview, RequirementRow,
)
from resume_tailorer.job_search.models import JobPosting, JobSource
from resume_tailorer.job_search.requirement_match import MatchScorer, match_from_review, quick_match_score
from resume_tailorer.models import CareerTruthProfile, WorkExperience

TEN_REQUIRED = """Data Engineer

Requirements:
- Experience with SQL
- Experience with Kubernetes
- Experience with Terraform
- Experience with Kafka
- Experience with Scala
- Experience with Airflow
- Experience with Spark
- Experience with Hadoop
- Experience with Golang
- Experience with Snowflake
"""


def _profile(skills=("SQL",)) -> CareerTruthProfile:
    return CareerTruthProfile(
        contact_info={"name": "Sam Example"}, education=[],
        work_experience=[WorkExperience(employer="Example Co", title="Analyst", dates="2021 - Present",
                                        responsibilities=["Built SQL reports for the finance team"],
                                        accomplishments=[])],
        skills=list(skills), tools=[], certifications=[], accomplishments=[],
    )


def _job(description: str) -> JobPosting:
    return JobPosting(source=JobSource.GREENHOUSE, source_id="m1", title="Data Engineer", company="Example Co",
                      location="Remote", description=description)


def _row(n: int, status: str, section: str = "required", term_status=()) -> RequirementRow:
    return RequirementRow(f"r{n}", f"Requirement {n}", section, False, status, (), (), "", term_status=term_status)


def test_one_requirement_shown_in_ten_is_about_ten_percent():
    fit = MatchScorer().score_fit_detailed(_profile(), _job(TEN_REQUIRED))
    assert fit.overall_fit == pytest.approx(10, abs=0.5)
    assert fit.scoring_version.startswith("match")
    assert any("SQL" in m for m in fit.strong_matches)
    assert len(fit.true_gaps) == 9


def test_required_requirements_count_twice_as_much_as_preferred():
    review = RequirementReview((_row(1, DIRECT), _row(2, NONE, "preferred")))
    assert match_from_review(review).percent == pytest.approx(200 / 3)
    review = RequirementReview((_row(1, NONE), _row(2, DIRECT, "preferred")))
    assert match_from_review(review).percent == pytest.approx(100 / 3)


def test_related_or_only_listed_evidence_counts_half_and_unconfirmed_counts_nothing():
    for status, expected in ((TRANSFERABLE, 50), (MENTION, 50), (UNCONFIRMED, 0), (NONE, 0), (DIRECT, 100)):
        assert match_from_review(RequirementReview((_row(1, status),))).percent == expected, status


def test_a_partly_supported_requirement_counts_the_share_of_its_named_terms_shown():
    row = _row(1, PARTIAL, term_status=(("SQL", DIRECT), ("Python", NONE), ("Tableau", NONE), ("Excel", DIRECT)))
    assert match_from_review(RequirementReview((row,))).percent == 50
    # General capability shown, the named example not: half credit, never full.
    example = _row(1, PARTIAL, term_status=(("Salesforce", NONE),))
    assert match_from_review(RequirementReview((example,))).percent == 50


def test_requirements_to_check_yourself_are_left_out_of_the_count():
    review = RequirementReview((_row(1, DIRECT), _row(2, CHECK)))
    match = match_from_review(review)
    assert match.percent == 100 and match.to_check == 1
    assert match_from_review(RequirementReview((_row(1, CHECK),))).percent is None


def test_no_stated_requirements_is_not_assessed():
    assert match_from_review(RequirementReview(())).percent is None
    assert MatchScorer().score_fit_detailed(_profile(), _job("")).overall_fit is None


def test_a_posting_that_only_names_skills_in_a_sentence_counts_those_skills():
    fit = MatchScorer().score_fit_detailed(_profile(skills=("Python",)), _job(
        "We need Python, Go, AWS, Docker, Kubernetes experience. 5+ years required."))
    assert fit.overall_fit is not None and 0 < fit.overall_fit < 50


def test_facts_not_yet_confirmed_do_not_count():
    unconfirmed = {"work_experience[0]": "resume", "skills": "resume"}
    fit = MatchScorer().score_fit_detailed(_profile(), _job(TEN_REQUIRED), provenance=unconfirmed)
    assert fit.overall_fit == 0


def test_the_quick_first_pass_ranks_jobs_in_the_same_order_as_the_full_match():
    profile = _profile(skills=("SQL", "Kafka", "Spark"))
    jobs = [_job(TEN_REQUIRED), _job("Requirements:\n- Experience with SQL\n- Experience with Java\n"),
            _job("Requirements:\n- Experience with Java\n")]
    quick = [quick_match_score(profile, job) for job in jobs]
    full = [MatchScorer().score_fit_detailed(profile, job).overall_fit for job in jobs]
    assert sorted(range(3), key=lambda i: -quick[i]) == sorted(range(3), key=lambda i: -full[i]) == [1, 0, 2]


def test_match_results_are_a_drop_in_for_the_old_fit_snapshot():
    fit = MatchScorer().score_fit_detailed(_profile(), _job(TEN_REQUIRED))
    snapshot = fit.to_dict()
    assert snapshot["overall_fit"] == fit.overall_fit and snapshot["scoring_version"] == fit.scoring_version
    assert replace(fit, overall_fit=None).overall_fit is None
