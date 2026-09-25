"""Tests for dashboard filter + sort helpers (Step 7)."""

from datetime import datetime

from resume_tailorer.job_search.dashboard import (
    filter_and_sort_jobs,
    filter_api_job_dicts,
    parse_salary_min,
    sort_jobs,
)
from resume_tailorer.job_search.models import (
    DashboardFilters,
    JobPosting,
    JobQualityStatus,
    JobSource,
)


def _job(**overrides):
    defaults = dict(
        source=JobSource.LINKEDIN,
        source_id="1",
        company="Acme",
        title="Software Engineer",
        location="Remote",
        description="Python and AWS",
        posted_date=datetime(2026, 9, 1),
        salary_min=100000,
        salary_max=140000,
        sponsorship_available=True,
        work_mode="remote",
        url="https://example.com/1",
    )
    defaults.update(overrides)
    return JobPosting(**defaults)


def test_parse_salary_min_from_range_string():
    assert parse_salary_min("$100K-$150K") == 100000
    assert parse_salary_min("120000") == 120000
    assert parse_salary_min(None) is None
    assert parse_salary_min("unknown") is None


def test_filter_by_min_fit_and_keyword():
    jobs = [
        _job(source_id="1", company="Acme", title="Backend Engineer"),
        _job(source_id="2", company="Globex", title="Frontend Engineer"),
        _job(source_id="3", company="Initech", title="Data Engineer"),
    ]
    scores = {
        "linkedin_1": 90.0,
        "linkedin_2": 40.0,
        "linkedin_3": 80.0,
    }
    filters = DashboardFilters(min_fit=70, keyword="engineer", sort_by="fit_score")
    result = filter_and_sort_jobs(jobs, filters, fit_scores=scores)
    assert [j.source_id for j in result] == ["1", "3"]


def test_filter_by_sponsorship_and_source():
    jobs = [
        _job(source_id="1", sponsorship_available=True, source=JobSource.GREENHOUSE),
        _job(source_id="2", sponsorship_available=False, source=JobSource.LINKEDIN),
        _job(source_id="3", sponsorship_available=None, source=JobSource.GREENHOUSE),
    ]
    filters = DashboardFilters(sponsorship="YES", source="greenhouse")
    result = filter_and_sort_jobs(jobs, filters)
    assert len(result) == 1
    assert result[0].source_id == "1"


def test_filter_by_quality():
    jobs = [
        _job(source_id="1"),
        _job(source_id="2"),
        _job(source_id="3"),
    ]
    quality = {
        "linkedin_1": JobQualityStatus.ACTIVE,
        "linkedin_2": JobQualityStatus.STALE,
        "linkedin_3": JobQualityStatus.EXPIRED,
    }
    filters = DashboardFilters(quality="stale")
    result = filter_and_sort_jobs(jobs, filters, quality_by_id=quality)
    assert [j.source_id for j in result] == ["2"]


def test_filter_by_action_save():
    jobs = [
        _job(source_id="1"),
        _job(source_id="2"),
        _job(source_id="3"),
    ]
    actions = {
        "linkedin_1": "interested",
        "linkedin_2": None,
        "linkedin_3": "pass",
    }
    filters = DashboardFilters(action="save")
    result = filter_and_sort_jobs(jobs, filters, actions=actions)
    assert [j.source_id for j in result] == ["1"]


def test_sort_by_salary_asc():
    jobs = [
        _job(source_id="1", salary_min=150000, salary_max=180000),
        _job(source_id="2", salary_min=90000, salary_max=110000),
        _job(source_id="3", salary_min=120000, salary_max=140000),
    ]
    result = sort_jobs(jobs, sort_by="salary", sort_dir="asc")
    assert [j.source_id for j in result] == ["2", "3", "1"]


def test_sort_by_company():
    jobs = [
        _job(source_id="1", company="Zebra"),
        _job(source_id="2", company="Acme"),
        _job(source_id="3", company="Beta"),
    ]
    result = sort_jobs(jobs, sort_by="company", sort_dir="asc")
    assert [j.company for j in result] == ["Acme", "Beta", "Zebra"]


def test_filter_api_job_dicts_parity():
    items = [
        {
            "job_id": "a",
            "fit_score": 90,
            "company": "Acme",
            "title": "Backend",
            "location": "Remote",
            "description": "Python",
            "salary": "$100K-$140K",
            "sponsorship": "yes",
            "work_mode": "remote",
            "source": "greenhouse",
            "quality_status": "active",
            "posted_at": "2026-09-01",
            "deadline": "unknown",
        },
        {
            "job_id": "b",
            "fit_score": 50,
            "company": "Globex",
            "title": "Frontend",
            "location": "NYC",
            "description": "React",
            "salary": "$80K",
            "sponsorship": "no",
            "work_mode": "hybrid",
            "source": "linkedin",
            "quality_status": "stale",
            "posted_at": "2026-06-01",
            "deadline": "unknown",
        },
    ]
    result = filter_api_job_dicts(
        items,
        min_fit=60,
        sponsorship="yes",
        sort_by="fit_score",
        sort_dir="desc",
    )
    assert len(result) == 1
    assert result[0]["job_id"] == "a"

    by_quality = filter_api_job_dicts(items, quality="stale")
    assert [i["job_id"] for i in by_quality] == ["b"]
