"""Indeed job scraper."""

from typing import List
from datetime import datetime, timedelta
from resume_tailorer.job_search.models import SearchGoals, JobPosting, JobSource
from resume_tailorer.job_search.scrapers.base_scraper import BaseScraper


class IndeedScraper(BaseScraper):
    """Scraper for Indeed job postings."""

    def __init__(self, api_key: str = None):
        """Initialize Indeed scraper.

        Args:
            api_key: Optional Indeed API key (not currently required for public jobs)
        """
        super().__init__(api_key=api_key)

    def get_platform_name(self) -> str:
        """Get platform name.

        Returns:
            "indeed"
        """
        return "indeed"

    def scrape(self, goals: SearchGoals) -> List[JobPosting]:
        """Scrape Indeed job postings matching search goals.

        For MVP, returns mock data simulating Indeed job listings.
        Production implementation would parse Indeed.com pages or use their API.

        Args:
            goals: SearchGoals object with search criteria

        Returns:
            List of JobPosting objects (empty list on error)
        """
        try:
            self._respect_rate_limit()

            # Mock job listings for Indeed
            mock_jobs = self._generate_mock_jobs(goals)
            return mock_jobs

        except Exception as error:
            self._handle_error(error, "scrape")
            return []

    def _generate_mock_jobs(self, goals: SearchGoals) -> List[JobPosting]:
        """Generate mock Indeed job postings for testing.

        Args:
            goals: SearchGoals object with search criteria

        Returns:
            List of mock JobPosting objects
        """
        # Sample job data similar to Indeed listings
        job_titles = [
            f"{goals.job_title}",
            f"{goals.job_title} (Full-time)",
            f"Lead {goals.job_title}",
        ]

        companies = [
            "TechStart Inc",
            "Digital Innovations LLC",
            "CloudFirst Systems",
            "DataWorks Corp",
            "NextGen Tech",
            "Velocity Solutions",
            "Quantum Labs",
            "Pioneer Digital",
        ]

        locations = [
            goals.location,
            f"{goals.location}, Remote",
            "Hybrid",
            "Full-time Remote",
        ]

        descriptions = [
            f"Seeking a talented {goals.job_title} to grow with our company. "
            f"Competitive salary and benefits package. Apply today!",
            f"Join our team as a {goals.job_title}. "
            f"We offer health insurance, 401k, and flexible work hours.",
            f"Urgent: {goals.job_title} position available. "
            f"Full-time role with relocation assistance available.",
        ]

        jobs = []
        for i in range(3):
            salary_min = goals.min_salary if goals.min_salary else 75000
            salary_max = goals.max_salary if goals.max_salary else 140000

            job = JobPosting(
                source=JobSource.INDEED,
                source_id=f"indeed_{i+1}",
                company=companies[i % len(companies)],
                title=job_titles[i % len(job_titles)],
                location=locations[i % len(locations)],
                description=descriptions[i % len(descriptions)],
                salary_min=salary_min + (i * 5000),
                salary_max=salary_max + (i * 5000),
                posted_date=datetime.now() - timedelta(days=i*2),
                url=f"https://www.indeed.com/jobs?q={goals.job_title.replace(' ', '+')}&l={goals.location.replace(' ', '+')}&vjk={i+1}",
                experience_required="2-3 years" if i > 0 else "Entry level",
                sponsorship_available=False,
                work_mode="Remote" if "Remote" in locations[i % len(locations)] else "On-site",
                ats_platform="Indeed",
            )
            jobs.append(job)

        return jobs
