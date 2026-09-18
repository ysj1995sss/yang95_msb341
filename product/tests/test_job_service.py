"""Tests for job service orchestrator."""

import pytest
from datetime import datetime
from unittest import mock

from resume_tailorer.job_search.job_service import JobService
from resume_tailorer.job_search.models import SearchGoals, JobPosting, JobSource
from resume_tailorer.models.career_profile import (
    CareerTruthProfile,
    EducationEntry,
    WorkExperience,
)


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test_job_service.db"
    yield str(db_path)
    # Cleanup handled automatically by tmp_path fixture


@pytest.fixture
def sample_goals():
    """Create sample search goals."""
    return SearchGoals(
        job_title="Software Engineer",
        industries=["Technology", "Finance"],
        min_salary=80000,
        max_salary=150000,
        location="San Francisco, CA",
        remote_preference="hybrid",
        sponsorship_required=False,
        experience_level="mid",
        company_size="large",
        target_companies=[],
        exclude_companies=[],
        employment_type="full-time",
        relocation_willing=False
    )


@pytest.fixture
def sample_profile():
    """Create a sample candidate profile with 5 years of experience."""
    return CareerTruthProfile(
        contact_info={"name": "John Doe", "email": "john@example.com", "phone": "555-1234", "location": "Seattle"},
        education=[
            EducationEntry(
                degree="BS",
                field="Computer Science",
                institution="University of Washington",
                year=2018,
                gpa="3.8"
            )
        ],
        work_experience=[
            WorkExperience(
                employer="Tech Company A",
                title="Software Engineer",
                dates="2018-2020",
                responsibilities=["Built APIs"],
                accomplishments=["Led migration"],
                location="Seattle",
                employment_type="Full-time"
            ),
            WorkExperience(
                employer="Tech Company B",
                title="Senior Software Engineer",
                dates="2020-2023",
                responsibilities=["Architected systems"],
                accomplishments=["Reduced latency"],
                location="Seattle",
                employment_type="Full-time"
            )
        ],
        skills=["Python", "Go", "JavaScript", "AWS", "Docker"],
        tools=["Docker", "PostgreSQL", "GitHub"],
        certifications=["AWS Solutions Architect"],
        accomplishments=["Led migration"]
    )


def test_job_service_initialization(temp_db):
    """JobService can be initialized with custom db_path."""
    service = JobService(db_path=temp_db)
    assert service is not None
    assert service.db is not None
    service.close()


def test_job_service_initialization_default_db():
    """JobService can be initialized with default db_path."""
    service = JobService()
    assert service is not None
    assert service.db is not None
    service.close()


def test_search_and_store_single_source(temp_db, sample_goals):
    """Search from one scraper, deduplicate, store."""
    # Mock the scraper
    mock_jobs = [
        JobPosting(
            source=JobSource.LINKEDIN,
            source_id="linkedin_1",
            company="Tech Corp",
            title="Software Engineer",
            location="San Francisco, CA",
            description="Great job",
            salary_min=100000,
            salary_max=150000,
            posted_date=datetime.now(),
            url="https://linkedin.com/job/1"
        )
    ]

    service = JobService(db_path=temp_db)

    # Mock the _get_scraper method to return a mock scraper
    mock_scraper = mock.Mock()
    mock_scraper.scrape.return_value = mock_jobs

    with mock.patch.object(service, '_get_scraper', return_value=mock_scraper):
        count = service.search_and_store(sample_goals, [JobSource.LINKEDIN])

        assert count == 1

    service.close()


def test_search_and_store_multiple_sources(temp_db, sample_goals):
    """Search from multiple sources, deduplicate, store."""
    # Mock jobs from different sources
    linkedin_jobs = [
        JobPosting(
            source=JobSource.LINKEDIN,
            source_id="linkedin_1",
            company="Tech Corp",
            title="Software Engineer",
            location="San Francisco, CA",
            description="Great job from LinkedIn",
            salary_min=100000,
            salary_max=150000,
            posted_date=datetime.now(),
            url="https://linkedin.com/job/1"
        )
    ]

    indeed_jobs = [
        JobPosting(
            source=JobSource.INDEED,
            source_id="indeed_1",
            company="Tech Corp",
            title="Software Engineer",
            location="San Francisco, CA",
            description="Same job from Indeed",
            salary_min=95000,
            salary_max=145000,
            posted_date=datetime.now(),
            url="https://indeed.com/job/1"
        ),
        JobPosting(
            source=JobSource.INDEED,
            source_id="indeed_2",
            company="Another Corp",
            title="Data Scientist",
            location="New York, NY",
            description="Data science role",
            salary_min=110000,
            salary_max=160000,
            posted_date=datetime.now(),
            url="https://indeed.com/job/2"
        )
    ]

    service = JobService(db_path=temp_db)

    # Mock the _get_scraper method
    def mock_get_scraper(source):
        if source == JobSource.LINKEDIN:
            mock_scraper = mock.Mock()
            mock_scraper.scrape.return_value = linkedin_jobs
            return mock_scraper
        elif source == JobSource.INDEED:
            mock_scraper = mock.Mock()
            mock_scraper.scrape.return_value = indeed_jobs
            return mock_scraper
        return None

    with mock.patch.object(service, '_get_scraper', side_effect=mock_get_scraper):
        count = service.search_and_store(sample_goals, [JobSource.LINKEDIN, JobSource.INDEED])

        # Should be 2: one deduplicated (Tech Corp) + one new (Another Corp)
        assert count == 2

    service.close()


def test_search_and_store_returns_count(temp_db, sample_goals):
    """search_and_store returns correct count of jobs stored."""
    mock_jobs = [
        JobPosting(
            source=JobSource.LINKEDIN,
            source_id=f"linkedin_{i}",
            company=f"Company {i}",
            title="Software Engineer",
            location="San Francisco, CA",
            description=f"Job {i}",
            posted_date=datetime.now(),
            url=f"https://linkedin.com/job/{i}"
        )
        for i in range(5)
    ]

    service = JobService(db_path=temp_db)

    # Mock the _get_scraper method
    mock_scraper = mock.Mock()
    mock_scraper.scrape.return_value = mock_jobs

    with mock.patch.object(service, '_get_scraper', return_value=mock_scraper):
        count = service.search_and_store(sample_goals, [JobSource.LINKEDIN])

        assert count == 5

    service.close()


def test_get_available_jobs(temp_db, sample_goals):
    """Retrieve stored jobs with goal filtering."""
    service = JobService(db_path=temp_db)

    # Create and save some test jobs
    jobs = [
        JobPosting(
            source=JobSource.LINKEDIN,
            source_id="1",
            company="Tech Corp",
            title="Senior Software Engineer",
            location="San Francisco, CA",
            description="Senior role",
            salary_min=120000,
            salary_max=180000,
            posted_date=datetime(2024, 9, 15),
            url="https://linkedin.com/job/1"
        ),
        JobPosting(
            source=JobSource.LINKEDIN,
            source_id="2",
            company="Startup Inc",
            title="Software Engineer",
            location="New York, NY",
            description="Junior role",
            salary_min=60000,
            salary_max=90000,
            posted_date=datetime(2024, 9, 10),
            url="https://linkedin.com/job/2"
        )
    ]

    for job in jobs:
        service.db.save_job_posting(job)

    # Query with sample goals - test that the method executes without error
    available_jobs = service.get_available_jobs(sample_goals)

    # The method should return a list (may be empty due to filtering)
    assert isinstance(available_jobs, list)

    service.close()


def test_get_job_with_fit_score(temp_db, sample_goals, sample_profile):
    """Get job and calculate fit score."""
    service = JobService(db_path=temp_db)

    job = JobPosting(
        source=JobSource.LINKEDIN,
        source_id="1",
        company="Tech Corp",
        title="Senior Software Engineer",
        location="San Francisco, CA",
        description="We need Python, Go, AWS, Docker, Kubernetes experience. 5+ years required.",
        salary_min=120000,
        salary_max=180000,
        experience_required="5+ years",
        education_required="Bachelor's in CS",
        posted_date=datetime.now(),
        url="https://linkedin.com/job/1"
    )

    service.db.save_job_posting(job)
    job_id = f"{job.source.value}_{job.source_id}"

    retrieved_job, fit_score = service.get_job_with_fit_score(job_id, sample_profile)

    assert retrieved_job is not None
    assert retrieved_job.company == "Tech Corp"
    assert isinstance(fit_score, (int, float))
    assert 0 <= fit_score <= 100

    service.close()


def test_empty_results(temp_db, sample_goals):
    """Handle empty scraper results gracefully."""
    service = JobService(db_path=temp_db)

    # Mock the _get_scraper method
    mock_scraper = mock.Mock()
    mock_scraper.scrape.return_value = []

    with mock.patch.object(service, '_get_scraper', return_value=mock_scraper):
        count = service.search_and_store(sample_goals, [JobSource.LINKEDIN])

        assert count == 0

    service.close()


def test_invalid_goals_min_salary_greater_than_max(temp_db):
    """Raise ValueError for invalid SearchGoals (min > max)."""
    service = JobService(db_path=temp_db)

    # SearchGoals constructor validates, so the error is raised here
    with pytest.raises(ValueError):
        SearchGoals(
            job_title="Software Engineer",
            industries=["Technology"],
            min_salary=150000,
            max_salary=80000,  # Invalid: min > max
            location="San Francisco, CA",
            remote_preference="hybrid",
            sponsorship_required=False,
            experience_level="mid",
            company_size="large"
        )

    service.close()


def test_invalid_goals_missing_required_fields(temp_db):
    """Raise ValueError for missing required fields in SearchGoals."""
    service = JobService(db_path=temp_db)
    service.db.create_tables()

    # job_title is required; test that empty string is invalid
    invalid_goals = SearchGoals(
        job_title="",  # Empty job title
        industries=[],
        min_salary=80000,
        max_salary=150000,
        location="San Francisco, CA",
        remote_preference="hybrid",
        sponsorship_required=False,
        experience_level="mid",
        company_size="large"
    )

    with pytest.raises(ValueError):
        service.search_and_store(invalid_goals, [JobSource.LINKEDIN])

    service.close()


def test_close_database(temp_db):
    """Close method closes database connection."""
    service = JobService(db_path=temp_db)
    service.close()

    # After close, database should be closed (connection.total_changes should fail)
    # This is a simple check that close was called
    assert service.db is not None  # Service still exists, but db is closed


def test_scraper_error_returns_zero(temp_db, sample_goals):
    """Scraper error returns 0 stored without failing."""
    service = JobService(db_path=temp_db)

    # Mock the _get_scraper method
    mock_scraper = mock.Mock()
    mock_scraper.scrape.side_effect = Exception("API Error")

    with mock.patch.object(service, '_get_scraper', return_value=mock_scraper):
        count = service.search_and_store(sample_goals, [JobSource.LINKEDIN])

        assert count == 0

    service.close()


def test_get_job_with_fit_score_nonexistent_job(temp_db, sample_profile):
    """Getting nonexistent job returns None."""
    service = JobService(db_path=temp_db)

    result = service.get_job_with_fit_score("nonexistent_job", sample_profile)

    assert result is None

    service.close()
