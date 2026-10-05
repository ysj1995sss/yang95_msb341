"""SmartRecruiters job scraper (public api.smartrecruiters.com postings API, no key).

Unlike Greenhouse, Lever and Ashby, a SmartRecruiters board can't be downloaded whole
(BoschGroup lists about 4,800 postings), and the list has no description. The search
text goes to SmartRecruiters, titles are checked here, and only matching postings are
fetched in full, a bounded number per company (decision 027).
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait
from typing import Dict, List, Optional, Tuple

from resume_tailorer.job_search.job_attributes import SMARTRECRUITERS_BOARDS, title_matches
from resume_tailorer.job_search.models import JobPosting, JobSource, SearchGoals
from resume_tailorer.job_search.scrapers.base_scraper import BaseScraper
from resume_tailorer.job_search.scrapers.board_scraper import normalize_job_type, parse_iso, strip_html

_DETAIL_CACHE: Dict[str, Tuple[float, dict]] = {}
_DETAIL_LOCK = threading.Lock()
_DETAIL_CACHE_LIMIT = 3000


def clear_detail_cache() -> None:
    with _DETAIL_LOCK:
        _DETAIL_CACHE.clear()


class SmartRecruitersScraper(BaseScraper):
    BOARDS = SMARTRECRUITERS_BOARDS
    API_BASE = "https://api.smartrecruiters.com/v1/companies"
    PAGE_SIZE = 100
    MAX_PAGES = 3  # per company and search
    MAX_DETAILS_PER_BOARD = 15
    MAX_PARALLEL = 16
    REQUEST_TIMEOUT = 20
    CACHE_SECONDS = 15 * 60
    # Full postings arriving later than this are left to finish in the background: they land
    # in the cache, so the next search includes them, and this search isn't held up.
    DETAIL_BUDGET_SECONDS = 5.0

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key=api_key)
        self.data_source = None
        self.coverage_note = None

    def get_platform_name(self) -> str:
        return "smartrecruiters"

    def board_tokens(self) -> List[str]:
        return list(self.BOARDS)

    def company_name(self, token: str) -> str:
        return self.BOARDS.get(token, (token,))[0]

    def scrape(self, goals: SearchGoals) -> List[JobPosting]:
        self.data_source = None
        self.coverage_note = None
        try:
            return self._scrape_real(goals)
        except Exception as error:
            self._handle_error(error, "scrape")
            self.data_source = "unavailable"
            return []

    def _list(self, token: str, query: str) -> Optional[list]:
        """Postings whose text matches the search, or None if the company didn't answer."""
        found: list = []
        for page in range(self.MAX_PAGES):
            url = (f"{self.API_BASE}/{token}/postings?limit={self.PAGE_SIZE}&offset={page * self.PAGE_SIZE}"
                   + (f"&q={_quote(query)}" if query else ""))
            data = self._make_get_request(url, timeout=self.REQUEST_TIMEOUT)
            if not isinstance(data, dict) or not isinstance(data.get("content"), list):
                return found if page else None
            found.extend(item for item in data["content"] if isinstance(item, dict))
            if len(found) >= int(data.get("totalFound") or 0) or not data["content"]:
                break
        return found

    def _detail(self, token: str, posting_id: str) -> Optional[dict]:
        url = f"{self.API_BASE}/{token}/postings/{posting_id}"
        now = time.monotonic()
        with _DETAIL_LOCK:
            cached = _DETAIL_CACHE.get(url)
        if cached and now - cached[0] < self.CACHE_SECONDS:
            return cached[1]
        data = self._make_get_request(url, timeout=self.REQUEST_TIMEOUT)
        if isinstance(data, dict):
            with _DETAIL_LOCK:
                if len(_DETAIL_CACHE) >= _DETAIL_CACHE_LIMIT:
                    _DETAIL_CACHE.clear()
                _DETAIL_CACHE[url] = (now, data)
            return data
        return None

    def _scrape_real(self, goals: SearchGoals) -> List[JobPosting]:
        tokens = self.board_tokens()
        query = (goals.job_title or "").strip()
        with ThreadPoolExecutor(max_workers=self.MAX_PARALLEL) as pool:
            listings = list(pool.map(lambda token: self._list(token, query), tokens))

        wanted: list[tuple[str, str]] = []
        answered = 0
        for token, items in zip(tokens, listings):
            if items is None:
                continue
            answered += 1
            matches = [item for item in items
                       if item.get("id") and (not query or title_matches(query, str(item.get("name") or "")))]
            wanted += [(token, str(item["id"])) for item in matches[: self.MAX_DETAILS_PER_BOARD]]

        pool = ThreadPoolExecutor(max_workers=self.MAX_PARALLEL)
        futures = [pool.submit(self._detail, *pair) for pair in wanted]
        done, pending = wait(futures, timeout=self.DETAIL_BUDGET_SECONDS)
        pool.shutdown(wait=False)  # pending fetches keep filling the cache
        jobs = [job for (token, _), future in zip(wanted, futures)
                if future in done and future.result() and (job := self.map_job(future.result(), token)) is not None]

        self.data_source = "real" if answered else "unavailable"
        missed = len(tokens) - answered
        notes = []
        if answered and missed:
            notes.append(f"{missed} of {len(tokens)} SmartRecruiters companies did not respond")
        if pending:
            notes.append(f"{len(pending)} SmartRecruiters postings are still loading; search again to include them")
        self.coverage_note = "; ".join(notes) or None
        return jobs

    def map_job(self, raw_job: dict, token: str) -> Optional[JobPosting]:
        job_id, title = raw_job.get("id"), raw_job.get("name")
        url = raw_job.get("postingUrl") or raw_job.get("applyUrl")
        if not job_id or not title or not url or raw_job.get("active") is False:
            return None
        sections = ((raw_job.get("jobAd") or {}).get("sections") or {})
        parts = []
        for key in ("jobDescription", "qualifications", "additionalInformation", "companyDescription"):
            section = sections.get(key) or {}
            text = strip_html(section.get("text") or "")
            if text.strip():
                parts.append(f"{section.get('title') or ''}\n{text}".strip())
        location = raw_job.get("location") or {}
        work_mode = "Remote" if location.get("remote") else "Hybrid" if location.get("hybrid") else "Onsite"
        return JobPosting(
            source=JobSource.SMARTRECRUITERS,
            source_id=str(job_id),
            company=(raw_job.get("company") or {}).get("name") or self.company_name(token),
            title=str(title),
            location=_clean_location(location.get("fullLocation")) or "Unknown",
            description="\n\n".join(parts) or "Unknown",
            posted_date=parse_iso(raw_job.get("releasedDate")),
            salary_min=None,
            salary_max=None,
            experience_required="Unknown",
            education_required="Unknown",
            sponsorship_available=None,
            work_mode=work_mode,
            url=str(url),
            ats_platform="SmartRecruiters",
            raw_json={"id": job_id, "company": token},
            employment_type=normalize_job_type((raw_job.get("typeOfEmployment") or {}).get("label")),
        )


def _clean_location(text: str | None) -> str:
    """'London, , United Kingdom' -> 'London, United Kingdom' (an empty region leaves a gap)."""
    return ", ".join(part.strip() for part in (text or "").split(",") if part.strip())


def _quote(text: str) -> str:
    from urllib.parse import quote

    return quote(text)
