"""Abstract base class for job scrapers."""

from abc import ABC, abstractmethod
from typing import List, Optional
import time

import requests

from resume_tailorer.job_search.models import SearchGoals, JobPosting


class BaseScraper(ABC):
    """Abstract base class for job scrapers across different platforms."""

    availability: str = "LIMITED"  # AVAILABLE | LIMITED | MANUAL | UNAVAILABLE
    capabilities: tuple = ("SEARCH",)

    def __init__(self, api_key: Optional[str] = None):
        """Initialize scraper with optional API key.

        Args:
            api_key: Optional API key for platforms that require authentication
        """
        self.api_key = api_key
        self.last_request_time = 0

    @abstractmethod
    def get_platform_name(self) -> str:
        """Get the name of the platform this scraper targets.

        Returns:
            Platform name as string (e.g., "linkedin", "indeed")
        """
        pass

    @abstractmethod
    def scrape(self, goals: SearchGoals) -> List[JobPosting]:
        """Scrape job postings matching the given search goals.

        Args:
            goals: SearchGoals object with search criteria

        Returns:
            List of JobPosting objects (empty list on error)
        """
        pass

    def _respect_rate_limit(self, min_delay: float = 1.0) -> None:
        """Implement rate limiting to avoid overwhelming servers.

        Args:
            min_delay: Minimum delay in seconds between requests (default 1.0)
        """
        elapsed = time.time() - self.last_request_time
        if elapsed < min_delay:
            time.sleep(min_delay - elapsed)
        self.last_request_time = time.time()

    def _handle_error(self, error: Exception, context: str = "") -> None:
        """Handle errors gracefully by logging and returning empty results.

        Args:
            error: The exception that occurred
            context: Additional context about where the error occurred
        """
        error_msg = f"Scraper error in {self.get_platform_name()}"
        if context:
            error_msg += f" ({context})"
        error_msg += f": {str(error)}"
        # In production, this would log to a proper logging system
        # For now, we just silently handle errors
        pass

    def _make_get_request(self, url: str, timeout: int = 10) -> Optional[dict]:
        """
        Make an HTTP GET request and return the parsed JSON body.

        Never raises — any network error, timeout, or non-200 status
        results in None so callers can fall back gracefully.

        Args:
            url: Full URL to request.
            timeout: Request timeout in seconds.

        Returns:
            Parsed JSON dict on success, or None on any failure.
        """
        try:
            response = requests.get(url, timeout=timeout)
            self._note_status(url, response.status_code)
            if response.status_code != 200:
                return None
            return response.json()
        except Exception:
            return None

    def _note_status(self, url: str, status: int) -> None:
        """Hook: board scrapers remember which boards answered 404 (spec 013)."""
