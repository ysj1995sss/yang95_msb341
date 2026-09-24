"""LinkedIn job scraper."""

import uuid
from typing import List
from datetime import datetime, timedelta
from resume_tailorer.job_search.models import SearchGoals, JobPosting, JobSource
from resume_tailorer.job_search.scrapers.base_scraper import BaseScraper


class LinkedInScraper(BaseScraper):
    """Scraper for LinkedIn job postings."""

    availability = "LIMITED"
    capabilities = ("SEARCH",)

    def __init__(self, api_key: str = None):
        """Initialize LinkedIn scraper.

        Args:
            api_key: Optional LinkedIn API key for authentication
        """
        super().__init__(api_key=api_key)

    def get_platform_name(self) -> str:
        """Get platform name.

        Returns:
            "linkedin"
        """
        return "linkedin"

    def scrape(self, goals: SearchGoals) -> List[JobPosting]:
        """Scrape LinkedIn job postings matching search goals.

        For MVP, returns mock data simulating LinkedIn job listings.
        Production implementation would use LinkedIn API or web scraping.

        Args:
            goals: SearchGoals object with search criteria

        Returns:
            List of JobPosting objects (empty list on error)
        """
        try:
            self._respect_rate_limit()

            # Mock job listings for LinkedIn
            mock_jobs = self._generate_mock_jobs(goals)
            return mock_jobs

        except Exception as error:
            self._handle_error(error, "scrape")
            return []

    def _generate_mock_jobs(self, goals: SearchGoals) -> List[JobPosting]:
        """Generate mock LinkedIn job postings for testing.

        Args:
            goals: SearchGoals object with search criteria

        Returns:
            List of mock JobPosting objects
        """
        # Sample job titles and companies for realistic mock data
        job_titles = [
            f"{goals.job_title}",
            f"Senior {goals.job_title}",
            f"{goals.job_title} - Remote",
        ]

        companies = [
            "Google",
            "Meta",
            "Microsoft",
            "Apple",
            "Amazon",
            "Tesla",
            "Stripe",
            "Airbnb",
            "Netflix",
        ]

        locations = [
            goals.location,
            f"{goals.location} (Remote)",
            "San Francisco, CA",
            "New York, NY",
            "Seattle, WA",
        ]

        descriptions = [
            f"We are looking for a talented {goals.job_title} to join our growing team. "
            f"You will be responsible for developing and maintaining our platform.",
            f"Join our {goals.job_title} team and help us build the future. "
            f"Experience with modern tech stack required.",
            f"Exciting opportunity for a {goals.job_title} in a fast-paced environment. "
            f"Work with cutting-edge technologies and brilliant minds.",
        ]

        jobs = []
        for i in range(3):
            salary_min = goals.min_salary if goals.min_salary else 80000
            salary_max = goals.max_salary if goals.max_salary else 150000

            job = JobPosting(
                source=JobSource.LINKEDIN,
                source_id=f"linkedin_{i+1}_{uuid.uuid4().hex[:8]}",
                company=companies[i % len(companies)],
                title=job_titles[i % len(job_titles)],
                location=locations[i % len(locations)],
                description=descriptions[i % len(descriptions)],
                salary_min=salary_min + (i * 10000),
                salary_max=salary_max + (i * 10000),
                posted_date=datetime.now() - timedelta(days=i),
                url=f"https://www.linkedin.com/jobs/view/{i+1}/",
                experience_required="3+ years" if i > 0 else "Entry level",
                sponsorship_available=False,
                work_mode="Remote" if "Remote" in locations[i % len(locations)] else "Hybrid",
            )
            jobs.append(job)

        return jobs
