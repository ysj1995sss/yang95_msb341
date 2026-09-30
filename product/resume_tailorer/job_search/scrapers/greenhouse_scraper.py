"""Greenhouse job scraper (public boards-api.greenhouse.io)."""

from typing import List, Optional

from resume_tailorer.job_search.job_attributes import COMPANY_DIRECTORY
from resume_tailorer.job_search.models import JobPosting, JobSource
from resume_tailorer.job_search.scrapers.board_scraper import BoardApiScraper, parse_iso, strip_html


class GreenhouseScraper(BoardApiScraper):
    """Greenhouse boards list only currently published jobs and state no salary,
    work arrangement or job type, so those stay unknown."""

    BOARDS = COMPANY_DIRECTORY
    GREENHOUSE_BOARD_TOKENS = list(COMPANY_DIRECTORY)
    GREENHOUSE_API_BASE = "https://boards-api.greenhouse.io/v1/boards"

    def get_platform_name(self) -> str:
        return "greenhouse"

    def board_tokens(self) -> List[str]:
        return list(self.GREENHOUSE_BOARD_TOKENS)

    def board_url(self, token: str) -> str:
        return f"{self.GREENHOUSE_API_BASE}/{token}/jobs?content=true"

    def jobs_in(self, data) -> Optional[list]:
        return data.get("jobs") if isinstance(data, dict) and "jobs" in data else None

    def map_job(self, raw_job: dict, token: str) -> Optional[JobPosting]:
        return self._map_greenhouse_job(raw_job, token)

    def _map_greenhouse_job(self, raw_job: dict, board_token: str) -> Optional[JobPosting]:
        """Map one Greenhouse job; None if id, title or URL is missing (never fabricated)."""
        job_id = raw_job.get("id")
        title = raw_job.get("title")
        url = raw_job.get("absolute_url")
        if not job_id or not title or not url:
            return None

        location = (raw_job.get("location") or {}).get("name") or "Unknown"
        return JobPosting(
            source=JobSource.GREENHOUSE,
            source_id=str(job_id),
            company=self.company_name(board_token),
            title=title,
            location=location,
            description=strip_html(raw_job.get("content") or "") or "Unknown",
            posted_date=parse_iso(raw_job.get("updated_at")),
            salary_min=None,
            salary_max=None,
            experience_required="Unknown",
            education_required="Unknown",
            sponsorship_available=None,
            work_mode="Unknown",
            url=url,
            ats_platform="Greenhouse",
            raw_json=dict(raw_job),
        )

    _strip_html = staticmethod(strip_html)
