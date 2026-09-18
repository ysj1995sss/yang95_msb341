"""Tests for pure-logic helper functions backing the Job Search Streamlit page."""

from datetime import datetime

import pytest

from resume_tailorer.job_search.models import JobPosting, JobSource, SearchGoals
from resume_tailorer.job_search.ui_helpers import (
    build_search_goals_from_form,
    filter_jobs_by_action,
    format_job_for_display,
)


def _valid_form():
    return {
        "job_title": "Software Engineer",
        "industries": ["Technology", "Finance"],
        "min_salary": 80000,
        "max_salary": 150000,
        "location": "San Francisco, CA",
        "remote_preference": "hybrid",
        "sponsorship_required": False,
        "experience_level": "mid",
        "company_size": "large",
        "target_companies": "Google, Microsoft",
        "exclude_companies": "",
        "employment_type": "full-time",
        "relocation_willing": False,
    }


def _job(**overrides):
    defaults = dict(
        source=JobSource.LINKEDIN,
        source_id="123",
        company="Acme Corp",
        title="Software Engineer",
        location="Remote",
        description="Build things.",
        posted_date=datetime(2026, 9, 1),
        salary_min=None,
        salary_max=None,
        sponsorship_available=False,
        work_mode=None,
        url="https://example.com/job/123",
    )
    defaults.update(overrides)
    return JobPosting(**defaults)


class TestBuildSearchGoalsFromForm:
    def test_build_search_goals_from_valid_form(self):
        goals = build_search_goals_from_form(_valid_form())

        assert isinstance(goals, SearchGoals)
        assert goals.job_title == "Software Engineer"
        assert goals.location == "San Francisco, CA"
        assert goals.min_salary == 80000
        assert goals.max_salary == 150000
        assert goals.industries == ["Technology", "Finance"]
        assert goals.remote_preference == "hybrid"
        assert goals.experience_level == "mid"
        assert goals.company_size == "large"
        assert goals.employment_type == "full-time"
        assert goals.sponsorship_required is False
        assert goals.relocation_willing is False

    def test_build_search_goals_missing_required_field(self):
        form = _valid_form()
        form["job_title"] = ""

        with pytest.raises(ValueError):
            build_search_goals_from_form(form)

    def test_build_search_goals_invalid_salary_range(self):
        form = _valid_form()
        form["min_salary"] = 200000
        form["max_salary"] = 100000

        with pytest.raises(ValueError):
            build_search_goals_from_form(form)

    def test_build_search_goals_parses_comma_separated_companies(self):
        form = _valid_form()
        form["target_companies"] = "Google, Microsoft"
        form["exclude_companies"] = "Amazon,  Meta "

        goals = build_search_goals_from_form(form)

        assert goals.target_companies == ["Google", "Microsoft"]
        assert goals.exclude_companies == ["Amazon", "Meta"]


class TestFormatJobForDisplay:
    def test_format_job_for_display_with_salary(self):
        job = _job(salary_min=100000, salary_max=150000)

        display = format_job_for_display(job)

        assert display["Salary"] == "$100K-$150K"

    def test_format_job_for_display_no_salary(self):
        job = _job(salary_min=None, salary_max=None)

        display = format_job_for_display(job)

        assert display["Salary"] == "Not specified"

    def test_format_job_for_display_with_fit_score(self):
        job = _job()

        display = format_job_for_display(job, fit_score=85.5)

        assert display["Fit Score"] == "86%"

    def test_format_job_for_display_no_fit_score(self):
        job = _job()

        display = format_job_for_display(job, fit_score=None)

        assert display["Fit Score"] == "N/A"


class TestFilterJobsByAction:
    def test_filter_jobs_by_action_all(self):
        job1 = _job(source_id="1", company="Acme")
        job2 = _job(source_id="2", company="Globex")
        job3 = _job(source_id="3", company="Initech")
        jobs_with_selections = [(job1, "interested"), (job2, None), (job3, "skipped")]

        result = filter_jobs_by_action(jobs_with_selections, "all")

        assert result == [job1, job2, job3]

    def test_filter_jobs_by_action_specific(self):
        job1 = _job(source_id="1", company="Acme")
        job2 = _job(source_id="2", company="Globex")
        job3 = _job(source_id="3", company="Initech")
        jobs_with_selections = [(job1, "interested"), (job2, "saved"), (job3, "interested")]

        result = filter_jobs_by_action(jobs_with_selections, "interested")

        assert result == [job1, job3]

    def test_filter_jobs_by_action_unreviewed(self):
        job1 = _job(source_id="1", company="Acme")
        job2 = _job(source_id="2", company="Globex")
        job3 = _job(source_id="3", company="Initech")
        jobs_with_selections = [(job1, "interested"), (job2, None), (job3, None)]

        result = filter_jobs_by_action(jobs_with_selections, "unreviewed")

        assert result == [job2, job3]
