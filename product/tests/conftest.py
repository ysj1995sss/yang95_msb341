"""Shared test setup."""

import os

import pytest

# Never download live job boards in the background during tests.
os.environ["JOB_COPILOT_PREFETCH"] = "0"


@pytest.fixture(autouse=True)
def _fresh_job_board_cache():
    """The board cache is process-wide; each test starts with it empty."""
    from resume_tailorer.job_search.scrapers.board_scraper import clear_board_cache
    from resume_tailorer.job_search.scrapers.smartrecruiters_scraper import clear_detail_cache

    clear_board_cache()
    clear_detail_cache()
    yield
    clear_board_cache()
    clear_detail_cache()


@pytest.fixture(autouse=True)
def _no_live_smartrecruiters(monkeypatch):
    """Tests never reach api.smartrecruiters.com; a test about it patches its own responses."""
    from resume_tailorer.job_search.scrapers.smartrecruiters_scraper import SmartRecruitersScraper

    monkeypatch.setattr(SmartRecruitersScraper, "_make_get_request",
                        lambda self, url, timeout=10: {"content": [], "totalFound": 0})
