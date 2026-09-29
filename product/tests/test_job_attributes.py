from resume_tailorer.job_search.job_attributes import (
    NOT_SPECIFIED,
    apply_goal_filters,
    employment_type_for,
    experience_level_for,
    industry_for,
    title_matches,
)
from resume_tailorer.job_search.models import JobPosting, JobSource, SearchGoals


def _job(title, company="GitLab"):
    return JobPosting(
        source=JobSource.GREENHOUSE, source_id=title, company=company,
        title=title, location="Remote", description="d",
    )


def _goals(title="Product Manager", industries=None, level="", job_type=""):
    return SearchGoals(
        job_title=title, industries=industries or [], min_salary=0, max_salary=0,
        location="", remote_preference="any", sponsorship_required=False,
        experience_level=level, company_size="", employment_type=job_type,
    )


def test_attributes_come_only_from_stated_facts():
    assert industry_for(_job("PM", company="Oscar Health")) == "Healthcare"
    assert industry_for(_job("PM", company="Unlisted Co")) == NOT_SPECIFIED
    assert experience_level_for(_job("Senior Product Manager")) == "senior"
    assert experience_level_for(_job("Director of Product")) == "lead"
    assert experience_level_for(_job("VP, Product")) == "executive"
    assert experience_level_for(_job("Product Manager Intern")) == "internship"
    assert experience_level_for(_job("Product Manager")) == NOT_SPECIFIED
    assert employment_type_for(_job("Product Manager (Contract)")) == "contract"
    assert employment_type_for(_job("Product Manager")) == NOT_SPECIFIED


def test_title_matching_ignores_word_order():
    assert title_matches("Product Manager", "Manager, Product Growth")
    assert not title_matches("Product Manager", "Product Designer")


def test_no_filters_keeps_every_title_match():
    jobs = [_job("Product Manager"), _job("Senior Product Manager", company="Coinbase")]
    assert apply_goal_filters(jobs, _goals()) == jobs


def test_industry_filter_supports_multiple_choices():
    gitlab, coinbase, oscar = (
        _job("Product Manager"),
        _job("Product Manager", company="Coinbase"),
        _job("Product Manager", company="Oscar Health"),
    )
    kept = apply_goal_filters([gitlab, coinbase, oscar], _goals(industries=["Finance", "Healthcare"]))
    assert kept == [coinbase, oscar]


def test_unknown_industry_is_kept_not_hidden():
    job = _job("Product Manager", company="Unlisted Co")
    assert apply_goal_filters([job], _goals(industries=["Finance"])) == [job]


def test_level_filter_drops_stated_mismatches_and_keeps_unstated():
    senior, plain = _job("Senior Product Manager"), _job("Product Manager")
    assert apply_goal_filters([senior, plain], _goals(level="entry,mid")) == [plain]


def test_internship_search_requires_an_internship_title():
    intern, plain = _job("Product Manager Intern"), _job("Product Manager")
    assert apply_goal_filters([intern, plain], _goals(level="internship")) == [intern]
    assert apply_goal_filters([intern, plain], _goals(job_type="internship")) == [intern]


def test_full_time_search_keeps_unlabeled_and_drops_contract():
    contract, plain = _job("Product Manager (Contract)"), _job("Product Manager")
    assert apply_goal_filters([contract, plain], _goals(job_type="full-time")) == [plain]


def test_sort_puts_missing_values_last_in_both_directions():
    from resume_tailorer.job_search.dashboard import sort_jobs

    jobs = [_job("A"), _job("B"), _job("C")]
    scores = {"greenhouse_A": 90, "greenhouse_B": None, "greenhouse_C": 40}
    desc = sort_jobs(jobs, sort_by="fit_score", sort_dir="desc", fit_scores=scores)
    asc = sort_jobs(jobs, sort_by="fit_score", sort_dir="asc", fit_scores=scores)
    assert [j.title for j in desc] == ["A", "C", "B"]
    assert [j.title for j in asc] == ["C", "A", "B"]


def test_sort_handles_dates_with_and_without_timezone():
    from datetime import datetime, timezone
    from resume_tailorer.job_search.dashboard import sort_jobs

    aware, naive = _job("aware"), _job("naive")
    aware.posted_date = datetime(2026, 9, 20, tzinfo=timezone.utc)
    naive.posted_date = datetime(2026, 9, 25)
    assert [j.title for j in sort_jobs([aware, naive])] == ["naive", "aware"]
