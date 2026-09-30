"""Lever job scraper (public api.lever.co postings API)."""

from typing import Optional

from resume_tailorer.job_search.job_attributes import LEVER_BOARDS
from resume_tailorer.job_search.models import JobPosting, JobSource
from resume_tailorer.job_search.scrapers.board_scraper import (
    BoardApiScraper,
    from_epoch_ms,
    normalize_job_type,
    normalize_work_mode,
    strip_html,
    usd_yearly_range,
)


class LeverScraper(BoardApiScraper):
    """Lever states work arrangement and commitment, and sometimes a salary range."""

    BOARDS = LEVER_BOARDS
    API_BASE = "https://api.lever.co/v0/postings"

    def get_platform_name(self) -> str:
        return "lever"

    def board_url(self, token: str) -> str:
        return f"{self.API_BASE}/{token}?mode=json"

    def jobs_in(self, data) -> Optional[list]:
        return data if isinstance(data, list) else None

    def map_job(self, raw_job: dict, token: str) -> Optional[JobPosting]:
        job_id, title, url = raw_job.get("id"), raw_job.get("text"), raw_job.get("hostedUrl")
        if not job_id or not title or not url:
            return None
        categories = raw_job.get("categories") or {}
        salary = raw_job.get("salaryRange") or {}
        salary_min, salary_max = usd_yearly_range(
            [(salary.get("currency"), salary.get("interval"), salary.get("min"), salary.get("max"))]
        )
        sections = [raw_job.get("descriptionPlain") or ""]
        for item in raw_job.get("lists") or []:
            sections.append(f"{item.get('text', '')}:\n{strip_html(item.get('content', ''))}")
        sections.append(raw_job.get("additionalPlain") or "")
        description = "\n\n".join(part.strip() for part in sections if part and part.strip())

        return JobPosting(
            source=JobSource.LEVER,
            source_id=str(job_id),
            company=self.company_name(token),
            title=title,
            location=categories.get("location") or "Unknown",
            description=description or "Unknown",
            posted_date=from_epoch_ms(raw_job.get("createdAt")),
            salary_min=salary_min,
            salary_max=salary_max,
            experience_required="Unknown",
            education_required="Unknown",
            sponsorship_available=None,
            work_mode=normalize_work_mode(raw_job.get("workplaceType")),
            url=url,
            ats_platform="Lever",
            raw_json=dict(raw_job),
            employment_type=normalize_job_type(categories.get("commitment")),
        )
