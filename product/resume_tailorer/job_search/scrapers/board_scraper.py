"""Shared logic for public company job-board APIs (Greenhouse, Lever, Ashby).

Each board API lists only currently published jobs, needs no login, and is
fetched in parallel. Results are real postings only: no match means an empty
result, never placeholder data. Values a board does not state stay unknown.
"""

from __future__ import annotations

import html
import json
import re
import threading
import time
import zlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from resume_tailorer.job_search.job_attributes import title_matches
from resume_tailorer.job_search.models import JobPosting, SearchGoals
from resume_tailorer.job_search.scrapers.base_scraper import BaseScraper

@dataclass(frozen=True)
class BoardIndex:
    """One board, as cached: every posting's title, and all postings compressed together.

    A search reads only the titles, then unpacks a board only when a title matches. Kept
    as parsed JSON, the live boards held about 280 MB of Python objects; packed like this
    they take about 15 MB (decision 027)."""

    titles: tuple[str, ...]
    packed: bytes

    @classmethod
    def build(cls, raw_jobs: list, title_key: str) -> "BoardIndex":
        titles = tuple(str(job.get(title_key) or "") if isinstance(job, dict) else "" for job in raw_jobs)
        return cls(titles, zlib.compress(json.dumps(raw_jobs).encode("utf-8"), 6))

    def jobs(self) -> list:
        return json.loads(zlib.decompress(self.packed))


# One cache for the whole process, so a board fetched for one session (or by the
# background warm-up) serves every other session too (decision 027).
_SHARED_CACHE: Dict[str, Tuple[float, object]] = {}
_IN_FLIGHT: Dict[str, threading.Event] = {}
_SHARED_LOCK = threading.Lock()
# Board URLs whose last fetch was a 404, so a search can say "not found" rather than
# "didn't respond" for a board someone added (spec 013). Never cached as a board.
_NOT_FOUND: set = set()
_last_warm = float("-inf")


def clear_board_cache() -> None:
    global _last_warm
    with _SHARED_LOCK:
        _SHARED_CACHE.clear()
        _IN_FLIGHT.clear()
        _NOT_FOUND.clear()
        _last_warm = float("-inf")


def warm_board_cache(scrapers) -> bool:
    """Fetch every board in the background unless that happened recently. True if started."""
    global _last_warm
    if not scrapers:
        return False
    now = time.monotonic()
    with _SHARED_LOCK:
        if now - _last_warm < max(s.CACHE_SECONDS for s in scrapers) - 60:
            return False
        _last_warm = now

    def run():
        # Every source's boards in one pool, so no source waits for another to finish.
        work = [(scraper, token) for scraper in scrapers for token in scraper.board_tokens()]
        try:
            with ThreadPoolExecutor(max_workers=16) as pool:
                list(pool.map(lambda item: item[0]._board_index(item[1]), work))
        except Exception:  # a warm-up is only a head start; a search fetches anyway
            pass

    threading.Thread(target=run, name="job-board-warmup", daemon=True).start()
    return True


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
    MAX_PARALLEL_BOARDS = 12
    REQUEST_TIMEOUT = 20
    # Board listings change slowly; reusing a response for a few minutes makes
    # a second search (e.g. a different title) fast. Never served when older.
    CACHE_SECONDS = 15 * 60
    # Where a raw board posting keeps its title. Checked before a posting is mapped, because
    # mapping cleans the full HTML description and boards list thousands of other roles.
    RAW_TITLE_KEY = "title"

    def __init__(self, api_key: str = None):
        super().__init__(api_key=api_key)
        self.data_source = None  # "real" or "unavailable" after each scrape()
        self.coverage_note = None
        self._board_cache = _SHARED_CACHE
        self._cache_lock = _SHARED_LOCK
        # Per search (spec 013): the boards a person added, and how each board did.
        self._extra: Dict[str, Tuple[str, str]] = {}
        self.board_results: Dict[str, dict] = {}

    def board_tokens(self) -> List[str]:
        return list(self.BOARDS)

    def search_tokens(self, include_curated: bool = True) -> List[str]:
        """Curated boards (unless switched off) plus added boards that aren't curated."""
        curated = self.board_tokens() if include_curated else []
        known = {t.lower() for t in self.board_tokens()}
        return [*curated, *(t for t in self._extra if t.lower() not in known)]

    def board_url(self, token: str) -> str:
        raise NotImplementedError

    def jobs_in(self, data) -> Optional[list]:
        """The job list inside a board response, or None if the response is not usable."""
        raise NotImplementedError

    def map_job(self, raw_job: dict, token: str) -> Optional[JobPosting]:
        raise NotImplementedError

    def company_name(self, token: str) -> str:
        if token in self._extra:
            return self._extra[token][0]
        return self.BOARDS.get(token, (token.replace("-", " ").replace("_", " ").title(),))[0]

    def scrape(self, goals: SearchGoals, extra_boards: Optional[Dict[str, Tuple[str, str]]] = None,
               include_curated: bool = True) -> List[JobPosting]:
        """Real postings whose titles match the goal title.

        `extra_boards`: {token: (company name, industry)} a person added (spec 013)."""
        self.data_source = None
        self.coverage_note = None
        self._extra = dict(extra_boards or {})
        self.board_results = {}
        try:
            return self._scrape_real(goals, include_curated)
        except Exception as error:
            self._handle_error(error, "scrape")
            self.data_source = "unavailable"
            return []

    def _fetch_board(self, token: str):
        """The board's raw response, straight from the network (no cache)."""
        return self._make_get_request(self.board_url(token), timeout=self.REQUEST_TIMEOUT)

    def _note_status(self, url: str, status: int) -> None:
        with self._cache_lock:
            if status == 404:
                _NOT_FOUND.add(url)
            else:
                _NOT_FOUND.discard(url)

    def _index_for(self, token: str) -> Optional[BoardIndex]:
        data = self._fetch_board(token)
        raw_jobs = self.jobs_in(data) if data is not None else None
        return None if raw_jobs is None else BoardIndex.build(raw_jobs, self.RAW_TITLE_KEY)

    def _board_index(self, token: str) -> Optional[BoardIndex]:
        """The board's cached index; None when the board didn't answer (never cached)."""
        url = self.board_url(token)
        with self._cache_lock:
            cached = self._board_cache.get(url)
            if cached and time.monotonic() - cached[0] < self.CACHE_SECONDS:
                return cached[1]
            pending = _IN_FLIGHT.get(url)
            if pending is None:
                _IN_FLIGHT[url] = threading.Event()
        if pending is not None:
            # Another session or the warm-up is fetching this board right now: share its answer.
            pending.wait(self.REQUEST_TIMEOUT + 5)
            with self._cache_lock:
                cached = self._board_cache.get(url)
            if cached:
                return cached[1]
            return self._index_for(token)
        try:
            index = self._index_for(token)
            if index is not None:
                with self._cache_lock:
                    self._board_cache[url] = (time.monotonic(), index)
            return index
        finally:
            with self._cache_lock:
                event = _IN_FLIGHT.pop(url, None)
            if event is not None:
                event.set()

    def _scrape_real(self, goals: SearchGoals, include_curated: bool = True) -> List[JobPosting]:
        tokens = self.search_tokens(include_curated)
        if not tokens:
            self.data_source = "real"
            return []
        with ThreadPoolExecutor(max_workers=self.MAX_PARALLEL_BOARDS) as pool:
            indexes = list(pool.map(self._board_index, tokens))

        all_jobs: List[JobPosting] = []
        boards_answered = 0
        for token, index in zip(tokens, indexes):
            if index is None:
                with self._cache_lock:
                    missing = self.board_url(token) in _NOT_FOUND
                self.board_results[token] = {"status": "not_found" if missing else "failed", "matched": 0}
                continue
            boards_answered += 1
            self.board_results[token] = {"status": "ok", "matched": 0}
            # Titles first: mapping cleans the full HTML description, and boards list
            # thousands of other roles.
            wanted = [i for i, title in enumerate(index.titles)
                      if not goals.job_title or title_matches(goals.job_title, title)]
            if not wanted:
                continue
            raw_jobs = index.jobs()
            for i in wanted:
                raw_job = raw_jobs[i]
                if not isinstance(raw_job, dict):
                    continue
                job = self.map_job(raw_job, token)
                if job is not None:
                    if isinstance(job.raw_json, dict):
                        job.raw_json["board"] = token  # which board it came from (spec 013)
                    all_jobs.append(job)
                    self.board_results[token]["matched"] += 1

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
