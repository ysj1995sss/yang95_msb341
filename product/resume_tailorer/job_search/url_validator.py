"""URL liveness validator for job postings.

Per the spec's Step 6 ("Clean and Validate Job Results"), a job posting's
URL should be confirmed still open before showing it to the user. This
validator never guesses: an ambiguous result (timeout, connection error,
unexpected status code) is treated as "unknown" and the job is KEPT
rather than dropped, since hiding a possibly-still-open job is worse
than showing one we're not 100% sure about. Only a confirmed 404/410
("closed") causes a job to be filtered out.
"""

import time
from typing import List

import requests

from resume_tailorer.job_search.models import JobPosting


class URLValidator:
    """Validates that job posting URLs are still live."""

    CLOSED_STATUS_CODES = {404, 410}
    MIN_REQUEST_INTERVAL = 1.0  # seconds, per-domain rate limit

    def __init__(self):
        self._last_request_time = 0.0

    def _respect_rate_limit(self) -> None:
        """Enforce a minimum interval between URL checks, mirroring
        BaseScraper's per-domain rate limiting so URLValidator's live
        HEAD requests don't exceed 1 req/sec against any single host."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.MIN_REQUEST_INTERVAL:
            time.sleep(self.MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.time()

    def check_url(self, url: str, timeout: int = 5) -> str:
        """
        Check whether a job posting URL is still active.

        Args:
            url: The job posting URL to check.
            timeout: Request timeout in seconds.

        Returns:
            "active" if the URL returns a 2xx status code.
            "closed" if the URL returns 404 or 410 (confirmed gone).
            "unknown" for any other status code, timeout, or connection
                error — never guess; ambiguous cases are kept, not dropped.
        """
        self._respect_rate_limit()
        try:
            response = requests.head(url, timeout=timeout, allow_redirects=True)
        except Exception:
            return "unknown"

        status = response.status_code
        if 200 <= status < 300:
            return "active"
        if status in self.CLOSED_STATUS_CODES:
            return "closed"
        return "unknown"

    def filter_active_jobs(self, postings: List[JobPosting]) -> List[JobPosting]:
        """
        Filter a list of job postings, dropping only confirmed-closed ones.

        Jobs with no URL are kept (treated as unknown, never checked).
        Jobs with "active" or "unknown" status are kept. Only "closed"
        (confirmed 404/410) results in a job being dropped.

        Args:
            postings: List of JobPosting objects to check.

        Returns:
            Filtered list excluding only confirmed-closed postings.
        """
        result = []
        for posting in postings:
            if not posting.url:
                result.append(posting)
                continue

            status = self.check_url(posting.url)
            if status != "closed":
                result.append(posting)

        return result
