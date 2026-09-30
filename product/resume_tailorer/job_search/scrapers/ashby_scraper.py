"""Ashby job scraper (public api.ashbyhq.com posting API)."""

from typing import Optional

from resume_tailorer.job_search.job_attributes import ASHBY_BOARDS
from resume_tailorer.job_search.models import JobPosting, JobSource
from resume_tailorer.job_search.scrapers.board_scraper import (
    BoardApiScraper,
    normalize_job_type,
    normalize_work_mode,
    parse_iso,
    strip_html,
    usd_yearly_range,
)


class AshbyScraper(BoardApiScraper):
    """Ashby states employment type, work arrangement and structured compensation."""

    BOARDS = ASHBY_BOARDS
    API_BASE = "https://api.ashbyhq.com/posting-api/job-board"

    def get_platform_name(self) -> str:
        return "ashby"

    def board_url(self, token: str) -> str:
        return f"{self.API_BASE}/{token}?includeCompensation=true"

    def jobs_in(self, data) -> Optional[list]:
        return data.get("jobs") if isinstance(data, dict) and isinstance(data.get("jobs"), list) else None

    def map_job(self, raw_job: dict, token: str) -> Optional[JobPosting]:
        job_id, title, url = raw_job.get("id"), raw_job.get("title"), raw_job.get("jobUrl")
        if not job_id or not title or not url or raw_job.get("isListed") is False:
            return None
        salaries = [
            (part.get("currencyCode"), part.get("interval"), part.get("minValue"), part.get("maxValue"))
            for tier in ((raw_job.get("compensation") or {}).get("compensationTiers") or [])
            for part in (tier.get("components") or [])
            if part.get("compensationType") == "Salary"
        ]
        salary_min, salary_max = usd_yearly_range(salaries)
        description = raw_job.get("descriptionPlain") or strip_html(raw_job.get("descriptionHtml") or "")

        return JobPosting(
            source=JobSource.ASHBY,
            source_id=str(job_id),
            company=self.company_name(token),
            title=title,
            location=raw_job.get("location") or "Unknown",
            description=description or "Unknown",
            posted_date=parse_iso(raw_job.get("publishedAt")),
            salary_min=salary_min,
            salary_max=salary_max,
            experience_required="Unknown",
            education_required="Unknown",
            sponsorship_available=None,
            work_mode=normalize_work_mode(raw_job.get("workplaceType")),
            url=url,
            ats_platform="Ashby",
            raw_json=dict(raw_job),
            employment_type=normalize_job_type(raw_job.get("employmentType")),
        )
