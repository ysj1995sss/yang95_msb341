"""Greenhouse job scraper."""

import re
import uuid
from typing import List, Optional
from datetime import datetime, timedelta
from resume_tailorer.job_search.models import SearchGoals, JobPosting, JobSource
from resume_tailorer.job_search.scrapers.base_scraper import BaseScraper


class GreenhouseScraper(BaseScraper):
    """Scraper for Greenhouse job postings (ATS provider).

    Uses Greenhouse's public boards-api.greenhouse.io endpoint, which
    requires no authentication and returns JSON job listings for any
    company that has a public Greenhouse job board. Falls back to
    mock data if the real API is unavailable or returns no results,
    so the demo experience always has something to show — but
    `data_source` always reflects which path was actually used.
    """

    # A small curated list of company board tokens known to expose public
    # Greenhouse job boards. Board token is the string in a company's
    # public URL: https://boards.greenhouse.io/{board_token}
    GREENHOUSE_BOARD_TOKENS = [
        "airbnb",
        "stripe",
        "gitlab",
        "coinbase",
        "asana",
    ]

    GREENHOUSE_API_BASE = "https://boards-api.greenhouse.io/v1/boards"

    def __init__(self, api_key: str = None):
        """Initialize Greenhouse scraper.

        Args:
            api_key: Optional Greenhouse API key (not required for the
                public boards-api endpoint; reserved for future
                authenticated endpoints).
        """
        super().__init__(api_key=api_key)
        self.data_source = None  # set to "real" or "mock" after each scrape()

    def get_platform_name(self) -> str:
        """Get platform name.

        Returns:
            "greenhouse"
        """
        return "greenhouse"

    def scrape(self, goals: SearchGoals) -> List[JobPosting]:
        """Scrape Greenhouse job postings matching search goals.

        Tries the real public Greenhouse boards API first across a
        curated list of company board tokens. Falls back to mock data
        if the real API is unavailable or returns no jobs at all, so
        there's always something to show for demo purposes. Sets
        self.data_source to "real" or "mock" depending on which path
        was used.

        Args:
            goals: SearchGoals object with search criteria

        Returns:
            List of JobPosting objects (empty list only if both real
            and mock paths somehow fail, which should not happen in
            practice since mock generation cannot fail).
        """
        self.data_source = None
        real_jobs = self._scrape_real(goals)

        if real_jobs:
            self.data_source = "real"
            return real_jobs

        self.data_source = "mock"
        try:
            self._respect_rate_limit()
            return self._generate_mock_jobs(goals)
        except Exception as error:
            self._handle_error(error, "scrape")
            return []

    def _scrape_real(self, goals: SearchGoals) -> List[JobPosting]:
        """Query the real Greenhouse public API across known board tokens."""
        all_jobs = []

        for board_token in self.GREENHOUSE_BOARD_TOKENS:
            self._respect_rate_limit()
            url = f"{self.GREENHOUSE_API_BASE}/{board_token}/jobs?content=true"
            data = self._make_get_request(url)

            if not data or "jobs" not in data:
                continue

            for raw_job in data["jobs"]:
                job = self._map_greenhouse_job(raw_job, board_token)
                if job is not None:
                    all_jobs.append(job)

        return self._filter_by_goals(all_jobs, goals)

    def _filter_by_goals(self, jobs: List[JobPosting], goals: SearchGoals) -> List[JobPosting]:
        """Filter real job postings by the user's search goals before they proceed
        to deduplication and URL validation, so the number of postings that need
        live liveness-checking stays small (the spec calls for results 'filtered
        by the user's stated goals', not every open req across every board).

        Matching is intentionally loose (substring, case-insensitive) since job
        titles vary in phrasing across companies — this is a coarse pre-filter,
        not the final relevance ranking (that's the database layer's job).

        Location is deliberately NOT filtered here: real Greenhouse locations are
        free-text and the database's search_jobs() LIKE filter already handles
        location matching downstream.
        """
        if not goals.job_title:
            return jobs

        title_keywords = [
            word.lower()
            for word in goals.job_title.split()
            if len(word) > 2  # skip short connector words like "of", "a"
        ]

        if not title_keywords:
            return jobs

        matched = []
        for job in jobs:
            title_lower = job.title.lower()
            if any(keyword in title_lower for keyword in title_keywords):
                matched.append(job)

        return matched

    def _map_greenhouse_job(self, raw_job: dict, board_token: str) -> Optional[JobPosting]:
        """Map a single Greenhouse API job dict to a JobPosting.

        Returns None if the raw job is missing required fields
        (id, title, absolute_url) — never fabricates a required field.
        """
        job_id = raw_job.get("id")
        title = raw_job.get("title")
        url = raw_job.get("absolute_url")

        if not job_id or not title or not url:
            return None

        location_data = raw_job.get("location") or {}
        location = location_data.get("name") or "Unknown"

        content_html = raw_job.get("content") or ""
        description = self._strip_html(content_html) or "Unknown"

        updated_at = raw_job.get("updated_at")
        posted_date = None
        if updated_at:
            try:
                posted_date = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                posted_date = None

        return JobPosting(
            source=JobSource.GREENHOUSE,
            source_id=str(job_id),
            company=board_token.replace("-", " ").replace("_", " ").title(),
            title=title,
            location=location,
            description=description,
            posted_date=posted_date,
            salary_min=None,
            salary_max=None,
            experience_required="Unknown",
            education_required="Unknown",
            sponsorship_available=False,
            work_mode="Unknown",
            url=url,
            ats_platform="Greenhouse",
        )

    @staticmethod
    def _strip_html(html: str) -> str:
        """Strip HTML tags from Greenhouse job description content."""
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _generate_mock_jobs(self, goals: SearchGoals) -> List[JobPosting]:
        """Generate mock Greenhouse job postings for testing/demo fallback.

        Args:
            goals: SearchGoals object with search criteria

        Returns:
            List of mock JobPosting objects
        """
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
                source_id=f"greenhouse_{i+1}_{uuid.uuid4().hex[:8]}",
                company=companies[i % len(companies)],
                title=job_titles[i % len(job_titles)],
                location=locations[i % len(locations)],
                description=descriptions[i % len(descriptions)],
                salary_min=salary_min + (i * 8000),
                salary_max=salary_max + (i * 8000),
                posted_date=datetime.now() - timedelta(days=i * 3),
                url=f"https://boards.greenhouse.io/company/jobs/{i+1}",
                experience_required="5+ years" if i > 1 else "3+ years",
                sponsorship_available=False,
                work_mode="Hybrid" if i % 2 == 0 else "On-site",
                ats_platform="Greenhouse",
            )
            jobs.append(job)

        return jobs
