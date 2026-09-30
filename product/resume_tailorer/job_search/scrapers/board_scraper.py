"""Shared logic for public company job-board APIs (Greenhouse, Lever, Ashby).

Each board API lists only currently published jobs, needs no login, and is
fetched in parallel. Results are real postings only: no match means an empty
result, never placeholder data. Values a board does not state stay unknown.
"""

from __future__ import annotations

import html
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from resume_tailorer.job_search.job_attributes import title_matches
from resume_tailorer.job_search.models import JobPosting, SearchGoals
from resume_tailorer.job_search.scrapers.base_scraper import BaseScraper

_WORK_MODES = {"remote": "Remote", "hybrid": "Hybrid", "onsite": "Onsite", "on-site": "Onsite"}
_JOB_TYPES = {
    "fulltime": "full-time", "full-time": "full-time",
    "parttime": "part-time", "part-time": "part-time",
    "intern": "internship", "internship": "internship",
    "contract": "contract", "contractor": "contract", "temporary": "contract", "fixed-term": "contract",
}


def normalize_work_mode(value: Optional[str]) -> str:
    return _WORK_MODES.get((value or "").strip().lower(), "Unknown")


def normalize_job_type(value: Optional[str]) -> Optional[str]:
    """Only explicit values map; e.g. "Permanent" says nothing about hours, so it stays unknown."""
    return _JOB_TYPES.get((value or "").strip().lower().replace(" ", ""))


def usd_yearly_range(salaries: List[Tuple[Optional[str], Optional[str], Optional[float], Optional[float]]]):
    """(min, max) across stated USD yearly salaries; other currencies are never converted."""
    lows, highs = [], []
    for currency, interval, low, high in salaries:
        if (currency or "").upper() != "USD" or "year" not in (interval or "").lower():
            continue
        if low:
            lows.append(int(low))
        if high:
            highs.append(int(high))
    return (min(lows) if lows else None, max(highs) if highs else None)


_BLOCK_TAGS = re.compile(r"</?\s*(?:p|div|ul|ol|h[1-6]|tr|section|article|header|footer)\b[^>]*>", re.I)


def strip_html(raw_html: str) -> str:
    """Plain text that keeps the posting's structure: one line per paragraph,
    heading or list item ("- " prefix). The job analyzer finds requirements by
    their lines, so collapsing everything into one line hides them.

    Unescaped before and after tag removal: some boards double-encode markup
    ("&lt;li&gt;") and entities ("&amp;amp;").
    """
    text = html.unescape(raw_html or "")
    text = re.sub(r"<\s*li\b[^>]*>", "\n- ", text, flags=re.I)
    text = re.sub(r"<\s*br\s*/?\s*>", "\n", text, flags=re.I)
    text = _BLOCK_TAGS.sub("\n", text)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    lines = [re.sub(r"[ \t ]+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line and line != "-"]
    return "\n".join(lines)


def parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def from_epoch_ms(value) -> Optional[datetime]:
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


class BoardApiScraper(BaseScraper):
    """A connector for one public job-board API across a curated list of companies."""

    availability = "AVAILABLE"
    capabilities = ("SEARCH", "DETAIL_FETCH", "POSTED_DATE")
    BOARDS: Dict[str, Tuple[str, str]] = {}  # board token -> (company name, industry)
    MAX_PARALLEL_BOARDS = 6
    REQUEST_TIMEOUT = 20
    # Board listings change slowly; reusing a response for a few minutes makes
    # a second search (e.g. a different title) fast. Never served when older.
    CACHE_SECONDS = 15 * 60

    def __init__(self, api_key: str = None):
        super().__init__(api_key=api_key)
        self.data_source = None  # "real" or "unavailable" after each scrape()
        self.coverage_note = None
        self._board_cache: Dict[str, Tuple[float, object]] = {}
        self._cache_lock = threading.Lock()

    def board_tokens(self) -> List[str]:
        return list(self.BOARDS)

    def board_url(self, token: str) -> str:
        raise NotImplementedError

    def jobs_in(self, data) -> Optional[list]:
        """The job list inside a board response, or None if the response is not usable."""
        raise NotImplementedError

    def map_job(self, raw_job: dict, token: str) -> Optional[JobPosting]:
        raise NotImplementedError

    def company_name(self, token: str) -> str:
        return self.BOARDS.get(token, (token.replace("-", " ").replace("_", " ").title(),))[0]

    def scrape(self, goals: SearchGoals) -> List[JobPosting]:
        """Real postings whose titles match the goal title."""
        self.data_source = None
        self.coverage_note = None
        try:
            return self._scrape_real(goals)
        except Exception as error:
            self._handle_error(error, "scrape")
            self.data_source = "unavailable"
            return []

    def _fetch_board(self, token: str):
        url = self.board_url(token)
        now = time.monotonic()
        with self._cache_lock:
            cached = self._board_cache.get(url)
        if cached and now - cached[0] < self.CACHE_SECONDS:
            return cached[1]
        data = self._make_get_request(url, timeout=self.REQUEST_TIMEOUT)
        if data is not None:
            with self._cache_lock:
                self._board_cache[url] = (now, data)
        return data

    def _scrape_real(self, goals: SearchGoals) -> List[JobPosting]:
        tokens = self.board_tokens()
        with ThreadPoolExecutor(max_workers=self.MAX_PARALLEL_BOARDS) as pool:
            responses = list(pool.map(self._fetch_board, tokens))

        all_jobs: List[JobPosting] = []
        boards_answered = 0
        for token, data in zip(tokens, responses):
            raw_jobs = self.jobs_in(data) if data is not None else None
            if raw_jobs is None:
                continue
            boards_answered += 1
            for raw_job in raw_jobs:
                job = self.map_job(raw_job, token) if isinstance(raw_job, dict) else None
                if job is not None:
                    all_jobs.append(job)

        self.data_source = "real" if boards_answered else "unavailable"
        missed = len(tokens) - boards_answered
        if boards_answered and missed:
            self.coverage_note = f"{missed} of {len(tokens)} company boards did not respond"
        return self._filter_by_goals(all_jobs, goals)

    def _filter_by_goals(self, jobs: List[JobPosting], goals: SearchGoals) -> List[JobPosting]:
        """Title pre-filter; location and the other goals apply downstream."""
        if not goals.job_title:
            return jobs
        return [job for job in jobs if title_matches(goals.job_title, job.title)]
