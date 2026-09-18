"""Tests for job deduplicator."""

import pytest
from datetime import datetime
from resume_tailorer.job_search.deduplicator import JobDeduplicator
from resume_tailorer.job_search.models import JobPosting, JobSource


@pytest.fixture
def deduplicator():
    """Create a JobDeduplicator instance."""
    return JobDeduplicator()


class TestJobDeduplicatorInitialization:
    """Tests for JobDeduplicator initialization."""

    def test_deduplicator_initialization(self):
        """JobDeduplicator can be instantiated."""
        dedup = JobDeduplicator()
        assert dedup is not None


class TestJobDeduplicatorNoDuplicates:
    """Tests for deduplicator with no duplicates."""

    def test_no_duplicates(self, deduplicator):
        """Single source jobs returned as-is."""
        postings = [
            JobPosting(
                source=JobSource.LINKEDIN,
                source_id="1",
                company="Tech Corp",
                title="Software Engineer",
                location="San Francisco, CA",
                description="A great job",
                url="https://linkedin.com/job/1"
            ),
            JobPosting(
                source=JobSource.INDEED,
                source_id="2",
                company="Another Corp",
                title="Data Scientist",
                location="New York, NY",
                description="Data science role",
                url="https://indeed.com/job/2"
            )
        ]
        result = deduplicator.deduplicate(postings)
        assert len(result) == 2
        assert result[0].company == "Tech Corp"
        assert result[1].company == "Another Corp"


class TestJobDeduplicatorMergeTwoSources:
    """Tests for deduplicator with two sources."""

    def test_merge_same_job_two_sources(self, deduplicator):
        """Same job from LinkedIn + Indeed → prefer LinkedIn."""
        postings = [
            JobPosting(
                source=JobSource.LINKEDIN,
                source_id="1",
                company="Tech Corp",
                title="Software Engineer",
                location="San Francisco, CA",
                description="A great job from LinkedIn",
                url="https://linkedin.com/job/1"
            ),
            JobPosting(
                source=JobSource.INDEED,
                source_id="2",
                company="Tech Corp",
                title="Software Engineer",
                location="San Francisco, CA",
                description="A great job from Indeed",
                url="https://indeed.com/job/2"
            )
        ]
        result = deduplicator.deduplicate(postings)
        assert len(result) == 1
        assert result[0].source == JobSource.LINKEDIN
        assert result[0].url == "https://linkedin.com/job/1"
        assert "https://indeed.com/job/2" in result[0].alternative_sources


class TestJobDeduplicatorGreenhousePriority:
    """Tests for deduplicator preferring Greenhouse."""

    def test_merge_same_job_greenhouse(self, deduplicator):
        """Same job from Greenhouse + Indeed → prefer Greenhouse."""
        postings = [
            JobPosting(
                source=JobSource.INDEED,
                source_id="2",
                company="Tech Corp",
                title="Software Engineer",
                location="San Francisco, CA",
                description="A great job from Indeed",
                url="https://indeed.com/job/2"
            ),
            JobPosting(
                source=JobSource.GREENHOUSE,
                source_id="1",
                company="Tech Corp",
                title="Software Engineer",
                location="San Francisco, CA",
                description="A great job from Greenhouse",
                url="https://greenhouse.io/job/1"
            )
        ]
        result = deduplicator.deduplicate(postings)
        assert len(result) == 1
        assert result[0].source == JobSource.GREENHOUSE
        assert result[0].url == "https://greenhouse.io/job/1"
        assert "https://indeed.com/job/2" in result[0].alternative_sources


class TestJobDeduplicatorMultipleDuplicates:
    """Tests for deduplicator with multiple duplicates."""

    def test_multiple_duplicates(self, deduplicator):
        """3 sources with 2 duplicate groups → correct dedup."""
        postings = [
            # Group 1: Software Engineer at Tech Corp
            JobPosting(
                source=JobSource.LINKEDIN,
                source_id="1",
                company="Tech Corp",
                title="Software Engineer",
                location="San Francisco, CA",
                description="Job 1",
                url="https://linkedin.com/job/1"
            ),
            JobPosting(
                source=JobSource.INDEED,
                source_id="2",
                company="Tech Corp",
                title="Software Engineer",
                location="San Francisco, CA",
                description="Job 2",
                url="https://indeed.com/job/2"
            ),
            # Group 2: Data Scientist at Another Corp
            JobPosting(
                source=JobSource.LINKEDIN,
                source_id="3",
                company="Another Corp",
                title="Data Scientist",
                location="New York, NY",
                description="Job 3",
                url="https://linkedin.com/job/3"
            )
        ]
        result = deduplicator.deduplicate(postings)
        assert len(result) == 2

        # Check first group (Tech Corp - Software Engineer)
        tech_corp_jobs = [j for j in result if j.company == "Tech Corp"]
        assert len(tech_corp_jobs) == 1
        assert tech_corp_jobs[0].source == JobSource.LINKEDIN
        assert len(tech_corp_jobs[0].alternative_sources) == 1

        # Check second group (Another Corp - Data Scientist)
        another_corp_jobs = [j for j in result if j.company == "Another Corp"]
        assert len(another_corp_jobs) == 1
        assert another_corp_jobs[0].source == JobSource.LINKEDIN
        assert len(another_corp_jobs[0].alternative_sources) == 0


class TestJobDeduplicatorPreserveBestPosting:
    """Tests for preserving best posting's fields."""

    def test_preserve_best_posting_fields(self, deduplicator):
        """Merged posting uses best source's fields."""
        postings = [
            JobPosting(
                source=JobSource.INDEED,
                source_id="2",
                company="Tech Corp",
                title="Software Engineer",
                location="San Francisco, CA",
                description="Incomplete job from Indeed",
                salary_min=100000,
                salary_max=120000,
                url="https://indeed.com/job/2"
            ),
            JobPosting(
                source=JobSource.LINKEDIN,
                source_id="1",
                company="Tech Corp",
                title="Software Engineer",
                location="San Francisco, CA",
                description="Better job description from LinkedIn",
                salary_min=120000,
                salary_max=150000,
                experience_required="3+ years",
                url="https://linkedin.com/job/1"
            )
        ]
        result = deduplicator.deduplicate(postings)
        assert len(result) == 1
        assert result[0].source == JobSource.LINKEDIN
        assert result[0].description == "Better job description from LinkedIn"
        assert result[0].salary_min == 120000
        assert result[0].salary_max == 150000
        assert result[0].experience_required == "3+ years"
        assert "https://indeed.com/job/2" in result[0].alternative_sources
