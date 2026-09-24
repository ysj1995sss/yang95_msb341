"""Handshake job scraper."""

import uuid
from typing import List
from datetime import datetime, timedelta
from resume_tailorer.job_search.models import SearchGoals, JobPosting, JobSource
from resume_tailorer.job_search.scrapers.base_scraper import BaseScraper


class HandshakeScraper(BaseScraper):
    """Scraper for Handshake job postings (college job portal)."""

    availability = "LIMITED"
    capabilities = ("SEARCH",)

    def __init__(self, api_key: str = None):
        """Initialize Handshake scraper.

        Args:
            api_key: Optional Handshake API key for authentication
        """
        super().__init__(api_key=api_key)

    def get_platform_name(self) -> str:
        """Get platform name.

        Returns:
            "handshake"
        """
        return "handshake"

    def scrape(self, goals: SearchGoals) -> List[JobPosting]:
        """Scrape Handshake job postings matching search goals.

        For MVP, returns mock data simulating Handshake job listings.
        Handshake is a college-focused job portal. Production implementation would
        use Handshake API or web scraping.

        Args:
            goals: SearchGoals object with search criteria

        Returns:
            List of JobPosting objects (empty list on error)
        """
        try:
            self._respect_rate_limit()

            # Mock job listings for Handshake
            mock_jobs = self._generate_mock_jobs(goals)
            return mock_jobs

        except Exception as error:
            self._handle_error(error, "scrape")
            return []

    def _generate_mock_jobs(self, goals: SearchGoals) -> List[JobPosting]:
        """Generate mock Handshake job postings for testing.

        Args:
            goals: SearchGoals object with search criteria

        Returns:
            List of mock JobPosting objects
        """
        # Sample job data typical for Handshake (college-focused)
        job_titles = [
            f"{goals.job_title} Internship",
            f"{goals.job_title} - Entry Level",
            f"Graduate {goals.job_title}",
        ]

        companies = [
            "Tech Careers Academy",
            "StartupHub",
            "Fortune 500 Tech",
            "Innovation Labs",
            "Future Tech Co",
            "Career Development Inc",
            "GrowthPath Solutions",
        ]

        locations = [
            goals.location,
            f"{goals.location} (Virtual)",
            "On-campus",
            "Virtual Internship",
        ]

        descriptions = [
            f"Great opportunity for students! Join us as a {goals.job_title}. "
            f"Learn industry skills and build your career.",
            f"Internship/Entry-level {goals.job_title} position. "
            f"Mentorship provided. Perfect for recent graduates.",
            f"Launch your career with a {goals.job_title} role. "
            f"We invest in developing our young talent.",
        ]

        jobs = []
        for i in range(3):
            salary_min = 35000 if goals.min_salary < 50000 else goals.min_salary - 20000
            salary_max = 65000 if goals.max_salary < 80000 else goals.max_salary - 30000

            # Ensure valid salary range
            if salary_min > salary_max:
                salary_min = max(35000, salary_max - 20000)

            job = JobPosting(
                source=JobSource.HANDSHAKE,
                source_id=f"handshake_{i+1}_{uuid.uuid4().hex[:8]}",
                company=companies[i % len(companies)],
                title=job_titles[i % len(job_titles)],
                location=locations[i % len(locations)],
                description=descriptions[i % len(descriptions)],
                salary_min=salary_min,
                salary_max=salary_max,
                posted_date=datetime.now() - timedelta(days=i),
                url=f"https://www.joinhandshake.com/jobs/{i+1}",
                experience_required="Entry level" if i == 0 else "Recent Graduate",
                sponsorship_available=True,
                work_mode="Remote" if "Virtual" in locations[i % len(locations)] else "On-site",
                ats_platform="Handshake",
            )
            jobs.append(job)

        return jobs
