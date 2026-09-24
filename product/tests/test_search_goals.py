import pytest
from datetime import datetime
from resume_tailorer.job_search.models import JobSource, SearchGoals, JobPosting, UserSelection


def test_search_goals_initialization():
    """SearchGoals can be created with valid data."""
    goals = SearchGoals(
        job_title="Senior Software Engineer",
        industries=["Technology", "Finance"],
        min_salary=100000,
        max_salary=150000,
        location="San Francisco, CA",
        remote_preference="remote",
        sponsorship_required=False,
        experience_level="senior",
        company_size="large"
    )
    assert goals.job_title == "Senior Software Engineer"
    assert goals.industries == ["Technology", "Finance"]
    assert goals.min_salary == 100000
    assert goals.max_salary == 150000
    assert goals.target_companies == []
    assert goals.exclude_companies == []
    assert goals.employment_type == "full-time"
    assert goals.relocation_willing is False


def test_search_goals_salary_validation():
    """min_salary > max_salary raises ValueError."""
    with pytest.raises(ValueError):
        SearchGoals(
            job_title="Software Engineer",
            industries=["Technology"],
            min_salary=150000,
            max_salary=100000,
            location="San Francisco, CA",
            remote_preference="remote",
            sponsorship_required=False,
            experience_level="mid",
            company_size="large"
        )


def test_job_posting_initialization():
    """JobPosting can be created."""
    posting = JobPosting(
        source=JobSource.LINKEDIN,
        source_id="12345",
        company="Tech Corp",
        title="Software Engineer",
        location="San Francisco, CA",
        description="We are looking for a software engineer."
    )
    assert posting.source == JobSource.LINKEDIN
    assert posting.source_id == "12345"
    assert posting.company == "Tech Corp"
    assert posting.title == "Software Engineer"
    assert posting.location == "San Francisco, CA"
    assert posting.sponsorship_available is None
    assert posting.ats_platform == "Unknown"


def test_job_source_enum():
    """JobSource enum values are correct."""
    assert JobSource.LINKEDIN.value == "linkedin"
    assert JobSource.INDEED.value == "indeed"
    assert JobSource.HANDSHAKE.value == "handshake"
    assert JobSource.GREENHOUSE.value == "greenhouse"
    assert JobSource.MONSTER.value == "monster"
    assert JobSource.LEVER.value == "lever"
    assert JobSource.ASHBY.value == "ashby"
    assert JobSource.WORKDAY.value == "workday"
    assert JobSource.COMPANY_PAGES.value == "company_pages"
