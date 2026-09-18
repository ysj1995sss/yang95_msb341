"""Greenhouse job scraper."""

from typing import List
from datetime import datetime, timedelta
from resume_tailorer.job_search.models import SearchGoals, JobPosting, JobSource
from resume_tailorer.job_search.scrapers.base_scraper import BaseScraper


class GreenhouseScraper(BaseScraper):
    """Scraper for Greenhouse job postings (ATS provider)."""

    def __init__(self, api_key: str = None):
        """Initialize Greenhouse scraper.

        Args:
            api_key: Optional Greenhouse API key for authentication
        """
        super().__init__(api_key=api_key)

    def get_platform_name(self) -> str:
        """Get platform name.

        Returns:
            "greenhouse"
        """
        return "greenhouse"

    def scrape(self, goals: SearchGoals) -> List[JobPosting]:
        """Scrape Greenhouse job postings matching search goals.

        For MVP, returns mock data simulating Greenhouse job listings.
        Greenhouse is an ATS provider. Many companies publish jobs on their
        public Greenhouse boards. Production implementation would use Greenhouse API
        or parse company-specific Greenhouse job boards.

        Args:
            goals: SearchGoals object with search criteria

        Returns:
            List of JobPosting objects (empty list on error)
        """
        try:
            self._respect_rate_limit()

            # Mock job listings for Greenhouse
            mock_jobs = self._generate_mock_jobs(goals)
            return mock_jobs

        except Exception as error:
            self._handle_error(error, "scrape")
            return []

    def _generate_mock_jobs(self, goals: SearchGoals) -> List[JobPosting]:
        """Generate mock Greenhouse job postings for testing.

        Args:
            goals: SearchGoals object with search criteria

        Returns:
            List of mock JobPosting objects
        """
        # Sample job data from Greenhouse board
        job_titles = [
            f"{goals.job_title}",
            f"Senior {goals.job_title}",
            f"{goals.job_title} - Strategic",
        ]

        companies = [
            "Acme Corp",
            "Global Enterprises",
            "Tech Worldwide",
            "Enterprise Solutions",
            "Business Innovations",
            "Corporate Tech Group",
            "Professional Services Inc",
        ]

        locations = [
            goals.location,
            f"{goals.location}, Regional",
            "Multi-location",
            "HQ + Remote",
        ]

        descriptions = [
            f"Exciting {goals.job_title} opportunity at an industry leader. "
            f"We're committed to innovation and growth.",
            f"Join our {goals.job_title} team in this high-impact role. "
            f"Lead strategic initiatives and drive business results.",
            f"Opening for {goals.job_title} with our expanding organization. "
            f"Competitive compensation and comprehensive benefits.",
        ]

        jobs = []
        for i in range(3):
            salary_min = goals.min_salary if goals.min_salary else 90000
            salary_max = goals.max_salary if goals.max_salary else 160000

            job = JobPosting(
                source=JobSource.GREENHOUSE,
                source_id=f"greenhouse_{i+1}",
                company=companies[i % len(companies)],
                title=job_titles[i % len(job_titles)],
                location=locations[i % len(locations)],
                description=descriptions[i % len(descriptions)],
                salary_min=salary_min + (i * 8000),
                salary_max=salary_max + (i * 8000),
                posted_date=datetime.now() - timedelta(days=i*3),
                url=f"https://boards.greenhouse.io/company/jobs/{i+1}",
                experience_required="5+ years" if i > 1 else "3+ years",
                sponsorship_available=False,
                work_mode="Hybrid" if i % 2 == 0 else "On-site",
                ats_platform="Greenhouse",
            )
            jobs.append(job)

        return jobs
