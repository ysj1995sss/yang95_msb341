"""Greenhouse job scraper."""

import html
import re
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional
from datetime import datetime
from resume_tailorer.job_search.job_attributes import COMPANY_DIRECTORY, title_matches
from resume_tailorer.job_search.models import SearchGoals, JobPosting, JobSource
from resume_tailorer.job_search.scrapers.base_scraper import BaseScraper


class GreenhouseScraper(BaseScraper):
    """Scraper for Greenhouse job postings (ATS provider).

    Uses Greenhouse's public boards-api.greenhouse.io endpoint, which
    requires no authentication and returns only currently-published jobs.
    Returns real postings only: no match means an empty result, never
    placeholder data. `data_source` is "real" when at least one board
    answered and "unavailable" when none did.
    """

    availability = "AVAILABLE"
    capabilities = ("SEARCH", "DETAIL_FETCH", "POSTED_DATE")

    GREENHOUSE_BOARD_TOKENS = list(COMPANY_DIRECTORY)

    GREENHOUSE_API_BASE = "https://boards-api.greenhouse.io/v1/boards"
    MAX_PARALLEL_BOARDS = 6

    def __init__(self, api_key: str = None):
        """Initialize Greenhouse scraper.

        Args:
            api_key: Optional Greenhouse API key (not required for the
                public boards-api endpoint; reserved for future
                authenticated endpoints).
        """
        super().__init__(api_key=api_key)
        self.data_source = None
        self.coverage_note = None

    def get_platform_name(self) -> str:
        """Get platform name.

        Returns:
            "greenhouse"
        """
        return "greenhouse"

    def scrape(self, goals: SearchGoals) -> List[JobPosting]:
        """Return real Greenhouse postings whose titles match the goal title."""
        self.data_source = None
        self.coverage_note = None
        try:
            return self._scrape_real(goals)
        except Exception as error:
            self._handle_error(error, "scrape")
            self.data_source = "unavailable"
            return []

    def _fetch_board(self, board_token: str) -> Optional[dict]:
        return self._make_get_request(
            f"{self.GREENHOUSE_API_BASE}/{board_token}/jobs?content=true", timeout=20
        )

    def _scrape_real(self, goals: SearchGoals) -> List[JobPosting]:
        """Query the real Greenhouse public API across known board tokens."""
        with ThreadPoolExecutor(max_workers=self.MAX_PARALLEL_BOARDS) as pool:
            responses = list(pool.map(self._fetch_board, self.GREENHOUSE_BOARD_TOKENS))

        all_jobs = []
        boards_answered = 0
        for board_token, data in zip(self.GREENHOUSE_BOARD_TOKENS, responses):
            if not data or "jobs" not in data:
                continue
            boards_answered += 1
            for raw_job in data["jobs"]:
                job = self._map_greenhouse_job(raw_job, board_token)
                if job is not None:
                    all_jobs.append(job)

        self.data_source = "real" if boards_answered else "unavailable"
        missed = len(self.GREENHOUSE_BOARD_TOKENS) - boards_answered
        if boards_answered and missed:
            self.coverage_note = (
                f"{missed} of {len(self.GREENHOUSE_BOARD_TOKENS)} company boards did not respond"
            )
        return self._filter_by_goals(all_jobs, goals)

    def _filter_by_goals(self, jobs: List[JobPosting], goals: SearchGoals) -> List[JobPosting]:
        """Keep jobs whose title contains every meaningful word of the goal title.

        Location and the other goal fields are applied downstream by the
        database query and job_attributes.apply_goal_filters().
        """
        if not goals.job_title:
            return jobs
        return [job for job in jobs if title_matches(goals.job_title, job.title)]

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
            company=COMPANY_DIRECTORY.get(board_token, (board_token.replace("-", " ").replace("_", " ").title(),))[0],
            title=title,
            location=location,
            description=description,
            posted_date=posted_date,
            salary_min=None,
            salary_max=None,
            experience_required="Unknown",
            education_required="Unknown",
            sponsorship_available=None,
            work_mode="Unknown",
            url=url,
            ats_platform="Greenhouse",
            raw_json=dict(raw_job) if isinstance(raw_job, dict) else {},
        )

    @staticmethod
    def _strip_html(raw_html: str) -> str:
        """Strip HTML tags from Greenhouse job description content.

        Found live (2026-09-24): some Greenhouse boards return `content`
        double-encoded -- literal "&lt;div class=&quot;...&quot;&gt;" text
        rather than real "<div ...>" tags. The tag-stripping regex only
        matches literal angle brackets, so it silently did nothing and the
        raw markup leaked straight into the JD text a candidate pastes into
        the tailorer. Unescaping first turns any such entities into real
        tags, which the same regex then removes as usual; unescaping a
        board whose content was never entity-encoded in the first place is
        a no-op, so this is safe for both cases.
        """
        text = html.unescape(raw_html)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text
