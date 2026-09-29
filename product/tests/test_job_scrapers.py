"""Tests for job scrapers."""

import pytest
import time
from unittest import mock
from datetime import datetime

from resume_tailorer.job_search.scrapers.base_scraper import BaseScraper
from resume_tailorer.job_search.scrapers.linkedin_scraper import LinkedInScraper
from resume_tailorer.job_search.scrapers.indeed_scraper import IndeedScraper
from resume_tailorer.job_search.scrapers.handshake_scraper import HandshakeScraper
from resume_tailorer.job_search.scrapers.greenhouse_scraper import GreenhouseScraper
from resume_tailorer.job_search.models import SearchGoals, JobPosting, JobSource


class TestBaseScraper:
    """Tests for BaseScraper abstract base class."""

    def test_base_scraper_cannot_be_instantiated_directly(self):
        """BaseScraper is abstract and cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseScraper()

    def test_base_scraper_has_required_abstract_methods(self):
        """BaseScraper requires subclasses to implement abstract methods."""
        # Verify that BaseScraper is abstract
        assert hasattr(BaseScraper, '__abstractmethods__')
        assert 'get_platform_name' in BaseScraper.__abstractmethods__
        assert 'scrape' in BaseScraper.__abstractmethods__


class TestLinkedInScraper:
    """Tests for LinkedInScraper."""

    def test_linkedin_scraper_initialization(self):
        """LinkedInScraper initializes correctly."""
        scraper = LinkedInScraper()
        assert scraper is not None
        assert scraper.api_key is None

    def test_linkedin_scraper_initialization_with_api_key(self):
        """LinkedInScraper initializes with API key."""
        api_key = "test_api_key_12345"
        scraper = LinkedInScraper(api_key=api_key)
        assert scraper.api_key == api_key

    def test_linkedin_scraper_returns_job_postings(self):
        """LinkedIn scraper returns list of JobPosting objects."""
        scraper = LinkedInScraper()
        goals = SearchGoals(
            job_title="Software Engineer",
            industries=["Technology"],
            min_salary=100000,
            max_salary=150000,
            location="San Francisco, CA",
            remote_preference="remote",
            sponsorship_required=False,
            experience_level="mid",
            company_size="large"
        )

        jobs = scraper.scrape(goals)

        assert isinstance(jobs, list)
        assert len(jobs) > 0
        assert all(isinstance(job, JobPosting) for job in jobs)

    def test_linkedin_scraper_returns_correct_source(self):
        """LinkedIn scraper returns jobs with correct source."""
        scraper = LinkedInScraper()
        goals = SearchGoals(
            job_title="Data Scientist",
            industries=["Technology"],
            min_salary=120000,
            max_salary=180000,
            location="New York, NY",
            remote_preference="hybrid",
            sponsorship_required=False,
            experience_level="senior",
            company_size="large"
        )

        jobs = scraper.scrape(goals)

        assert all(job.source == JobSource.LINKEDIN for job in jobs)

    def test_linkedin_scraper_get_platform_name(self):
        """LinkedIn scraper returns correct platform name."""
        scraper = LinkedInScraper()
        assert scraper.get_platform_name() == "linkedin"


class TestIndeedScraper:
    """Tests for IndeedScraper."""

    def test_indeed_scraper_initialization(self):
        """IndeedScraper initializes correctly."""
        scraper = IndeedScraper()
        assert scraper is not None
        assert scraper.api_key is None

    def test_indeed_scraper_returns_job_postings(self):
        """Indeed scraper returns list of JobPosting objects."""
        scraper = IndeedScraper()
        goals = SearchGoals(
            job_title="Product Manager",
            industries=["Technology", "Finance"],
            min_salary=110000,
            max_salary=160000,
            location="Chicago, IL",
            remote_preference="hybrid",
            sponsorship_required=False,
            experience_level="mid",
            company_size="medium"
        )

        jobs = scraper.scrape(goals)

        assert isinstance(jobs, list)
        assert len(jobs) > 0
        assert all(isinstance(job, JobPosting) for job in jobs)

    def test_indeed_scraper_returns_correct_source(self):
        """Indeed scraper returns jobs with correct source."""
        scraper = IndeedScraper()
        goals = SearchGoals(
            job_title="Marketing Manager",
            industries=["Marketing"],
            min_salary=80000,
            max_salary=130000,
            location="Boston, MA",
            remote_preference="any",
            sponsorship_required=False,
            experience_level="mid",
            company_size="large"
        )

        jobs = scraper.scrape(goals)

        assert all(job.source == JobSource.INDEED for job in jobs)

    def test_indeed_scraper_get_platform_name(self):
        """Indeed scraper returns correct platform name."""
        scraper = IndeedScraper()
        assert scraper.get_platform_name() == "indeed"


class TestHandshakeScraper:
    """Tests for HandshakeScraper."""

    def test_handshake_scraper_initialization(self):
        """HandshakeScraper initializes correctly."""
        scraper = HandshakeScraper()
        assert scraper is not None
        assert scraper.api_key is None

    def test_handshake_scraper_returns_job_postings(self):
        """Handshake scraper returns list of JobPosting objects."""
        scraper = HandshakeScraper()
        goals = SearchGoals(
            job_title="Software Engineer Intern",
            industries=["Technology"],
            min_salary=40000,
            max_salary=70000,
            location="San Jose, CA",
            remote_preference="remote",
            sponsorship_required=True,
            experience_level="entry",
            company_size="large"
        )

        jobs = scraper.scrape(goals)

        assert isinstance(jobs, list)
        assert len(jobs) > 0
        assert all(isinstance(job, JobPosting) for job in jobs)

    def test_handshake_scraper_returns_correct_source(self):
        """Handshake scraper returns jobs with correct source."""
        scraper = HandshakeScraper()
        goals = SearchGoals(
            job_title="UX Designer",
            industries=["Design", "Technology"],
            min_salary=50000,
            max_salary=80000,
            location="Seattle, WA",
            remote_preference="remote",
            sponsorship_required=True,
            experience_level="entry",
            company_size="medium"
        )

        jobs = scraper.scrape(goals)

        assert all(job.source == JobSource.HANDSHAKE for job in jobs)

    def test_handshake_scraper_get_platform_name(self):
        """Handshake scraper returns correct platform name."""
        scraper = HandshakeScraper()
        assert scraper.get_platform_name() == "handshake"


class TestGreenhouseScraper:
    """Tests for GreenhouseScraper."""

    def test_greenhouse_scraper_initialization(self):
        """GreenhouseScraper initializes correctly."""
        scraper = GreenhouseScraper()
        assert scraper is not None
        assert scraper.api_key is None

    def test_greenhouse_scraper_returns_job_postings(self):
        """Greenhouse scraper returns list of JobPosting objects."""
        scraper = GreenhouseScraper()
        goals = SearchGoals(
            job_title="Senior Engineer",
            industries=["Technology"],
            min_salary=130000,
            max_salary=200000,
            location="Mountain View, CA",
            remote_preference="hybrid",
            sponsorship_required=False,
            experience_level="senior",
            company_size="large"
        )

        jobs = scraper.scrape(goals)

        assert isinstance(jobs, list)
        assert len(jobs) > 0
        assert all(isinstance(job, JobPosting) for job in jobs)

    def test_greenhouse_scraper_returns_correct_source(self):
        """Greenhouse scraper returns jobs with correct source."""
        scraper = GreenhouseScraper()
        goals = SearchGoals(
            job_title="Operations Manager",
            industries=["Operations"],
            min_salary=95000,
            max_salary=150000,
            location="Austin, TX",
            remote_preference="on-site",
            sponsorship_required=False,
            experience_level="mid",
            company_size="large"
        )

        jobs = scraper.scrape(goals)

        assert all(job.source == JobSource.GREENHOUSE for job in jobs)

    def test_greenhouse_scraper_get_platform_name(self):
        """Greenhouse scraper returns correct platform name."""
        scraper = GreenhouseScraper()
        assert scraper.get_platform_name() == "greenhouse"


class TestScraperRateLimiting:
    """Tests for rate limiting functionality."""

    def test_scraper_respects_rate_limit(self):
        """Scraper respects rate limiting between requests."""
        scraper = LinkedInScraper()
        goals = SearchGoals(
            job_title="Test Role",
            industries=["Technology"],
            min_salary=80000,
            max_salary=120000,
            location="Test City, ST",
            remote_preference="remote",
            sponsorship_required=False,
            experience_level="mid",
            company_size="large"
        )

        # First request
        start_time = time.time()
        scraper.scrape(goals)
        first_request_time = time.time() - start_time

        # Second request should be delayed due to rate limiting
        start_time = time.time()
        scraper.scrape(goals)
        second_request_time = time.time() - start_time

        # The rate limit should ensure at least 1 second between requests
        # (accounting for execution time)
        assert second_request_time >= 0.9  # Allow some tolerance for execution time

    def test_base_scraper_has_rate_limit_helper(self):
        """BaseScraper has a rate limiting helper method."""
        # Create a concrete subclass for testing
        class TestScraper(BaseScraper):
            def get_platform_name(self):
                return "test"

            def scrape(self, goals):
                return []

        scraper = TestScraper()
        assert hasattr(scraper, '_respect_rate_limit')
        assert callable(getattr(scraper, '_respect_rate_limit'))


class TestScraperErrorHandling:
    """Tests for error handling in scrapers."""

    def test_scraper_returns_empty_list_on_error(self):
        """Scraper returns empty list on error, doesn't crash."""
        scraper = LinkedInScraper()

        # Create an invalid goals object to trigger error
        # (actually, SearchGoals validation will catch this)
        # Instead, mock an error in the scraper
        with mock.patch.object(scraper, '_generate_mock_jobs', side_effect=Exception("Test error")):
            goals = SearchGoals(
                job_title="Test",
                industries=["Tech"],
                min_salary=50000,
                max_salary=100000,
                location="Test",
                remote_preference="remote",
                sponsorship_required=False,
                experience_level="mid",
                company_size="large"
            )

            # Should not raise exception
            jobs = scraper.scrape(goals)

            # Should return empty list on error
            assert jobs == []
            assert isinstance(jobs, list)

    def test_all_platforms_handle_errors_gracefully(self):
        """All scrapers handle errors gracefully."""
        scrapers = [
            LinkedInScraper(),
            IndeedScraper(),
            HandshakeScraper(),
            GreenhouseScraper()
        ]

        goals = SearchGoals(
            job_title="Test",
            industries=["Tech"],
            min_salary=50000,
            max_salary=100000,
            location="Test",
            remote_preference="remote",
            sponsorship_required=False,
            experience_level="mid",
            company_size="large"
        )

        for scraper in scrapers:
            failing = '_scrape_real' if isinstance(scraper, GreenhouseScraper) else '_generate_mock_jobs'
            with mock.patch.object(scraper, failing, side_effect=Exception("Test error")):
                # Even with an error, should return empty list
                jobs = scraper.scrape(goals)
                assert isinstance(jobs, list)


class TestJobPostingRequiredFields:
    """Tests for JobPosting object completeness."""

    def test_all_returned_postings_have_required_fields(self):
        """All returned JobPosting objects have required fields."""
        scrapers = [
            LinkedInScraper(),
            IndeedScraper(),
            HandshakeScraper(),
            GreenhouseScraper()
        ]

        goals = SearchGoals(
            job_title="Software Engineer",
            industries=["Technology"],
            min_salary=80000,
            max_salary=150000,
            location="San Francisco, CA",
            remote_preference="remote",
            sponsorship_required=False,
            experience_level="mid",
            company_size="large"
        )

        required_fields = ['source', 'source_id', 'company', 'title', 'location', 'description', 'url']

        for scraper in scrapers:
            jobs = scraper.scrape(goals)

            for job in jobs:
                assert job.source is not None, f"{scraper.get_platform_name()}: source is missing"
                assert job.source_id is not None, f"{scraper.get_platform_name()}: source_id is missing"
                assert job.company is not None, f"{scraper.get_platform_name()}: company is missing"
                assert job.title is not None, f"{scraper.get_platform_name()}: title is missing"
                assert job.location is not None, f"{scraper.get_platform_name()}: location is missing"
                assert job.description is not None, f"{scraper.get_platform_name()}: description is missing"
                assert job.url is not None, f"{scraper.get_platform_name()}: url is missing"

    def test_linkedin_posting_has_all_fields(self):
        """LinkedIn posting includes all expected fields."""
        scraper = LinkedInScraper()
        goals = SearchGoals(
            job_title="Engineer",
            industries=["Tech"],
            min_salary=80000,
            max_salary=150000,
            location="SF",
            remote_preference="remote",
            sponsorship_required=False,
            experience_level="mid",
            company_size="large"
        )

        jobs = scraper.scrape(goals)
        assert len(jobs) > 0

        job = jobs[0]
        assert job.source == JobSource.LINKEDIN
        assert job.company is not None and job.company != ""
        assert job.title is not None and job.title != ""
        assert job.url.startswith("https://")

    def test_indeed_posting_has_all_fields(self):
        """Indeed posting includes all expected fields."""
        scraper = IndeedScraper()
        goals = SearchGoals(
            job_title="Manager",
            industries=["Tech"],
            min_salary=80000,
            max_salary=150000,
            location="Chicago",
            remote_preference="hybrid",
            sponsorship_required=False,
            experience_level="mid",
            company_size="medium"
        )

        jobs = scraper.scrape(goals)
        assert len(jobs) > 0

        job = jobs[0]
        assert job.source == JobSource.INDEED
        assert job.ats_platform == "Indeed"
        assert "indeed.com" in job.url

    def test_handshake_posting_sponsorship_flag(self):
        """Handshake posting includes sponsorship availability."""
        scraper = HandshakeScraper()
        goals = SearchGoals(
            job_title="Intern",
            industries=["Tech"],
            min_salary=40000,
            max_salary=70000,
            location="SF",
            remote_preference="remote",
            sponsorship_required=True,
            experience_level="entry",
            company_size="large"
        )

        jobs = scraper.scrape(goals)
        assert len(jobs) > 0

        job = jobs[0]
        assert job.source == JobSource.HANDSHAKE
        # Handshake should offer sponsorship
        assert job.sponsorship_available is True

    def test_greenhouse_posting_has_ats_platform(self):
        """Greenhouse posting includes ATS platform info."""
        scraper = GreenhouseScraper()
        goals = SearchGoals(
            job_title="Director",
            industries=["Tech"],
            min_salary=130000,
            max_salary=200000,
            location="Mountain View",
            remote_preference="hybrid",
            sponsorship_required=False,
            experience_level="senior",
            company_size="large"
        )

        jobs = scraper.scrape(goals)
        assert len(jobs) > 0

        job = jobs[0]
        assert job.source == JobSource.GREENHOUSE
        assert job.ats_platform == "Greenhouse"


class TestScraperIntegration:
    """Integration tests for scrapers working together."""

    def test_all_scrapers_work_with_same_goals(self):
        """All scrapers can process the same SearchGoals object."""
        goals = SearchGoals(
            job_title="Data Engineer",
            industries=["Technology", "Data"],
            min_salary=100000,
            max_salary=180000,
            location="Seattle, WA",
            remote_preference="hybrid",
            sponsorship_required=False,
            experience_level="mid",
            company_size="large",
            target_companies=["Google", "Microsoft", "Amazon"],
            exclude_companies=["Old Company"],
            employment_type="full-time",
            relocation_willing=True
        )

        scrapers = {
            "LinkedIn": LinkedInScraper(),
            "Indeed": IndeedScraper(),
            "Handshake": HandshakeScraper(),
            "Greenhouse": GreenhouseScraper(),
        }

        for name, scraper in scrapers.items():
            jobs = scraper.scrape(goals)
            assert isinstance(jobs, list), f"{name} did not return a list"
            assert len(jobs) > 0, f"{name} returned empty list"
            assert all(isinstance(job, JobPosting) for job in jobs), f"{name} returned non-JobPosting objects"

    def test_scraper_consistency(self):
        """All scrapers maintain consistency in data structure."""
        goals = SearchGoals(
            job_title="QA Engineer",
            industries=["Technology"],
            min_salary=70000,
            max_salary=120000,
            location="Austin, TX",
            remote_preference="remote",
            sponsorship_required=False,
            experience_level="mid",
            company_size="medium"
        )

        scrapers = [
            LinkedInScraper(),
            IndeedScraper(),
            HandshakeScraper(),
            GreenhouseScraper()
        ]

        all_jobs = []
        for scraper in scrapers:
            jobs = scraper.scrape(goals)
            all_jobs.extend(jobs)

        # Verify consistency across all scrapers
        for job in all_jobs:
            assert isinstance(job, JobPosting)
            assert isinstance(job.source, JobSource)
            assert isinstance(job.source_id, str) and len(job.source_id) > 0
            assert isinstance(job.company, str) and len(job.company) > 0
            assert isinstance(job.title, str) and len(job.title) > 0
            assert isinstance(job.location, str) and len(job.location) > 0
            assert isinstance(job.description, str) and len(job.description) > 0
            assert isinstance(job.url, str) and len(job.url) > 0
