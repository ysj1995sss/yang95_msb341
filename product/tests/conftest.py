"""Shared test setup."""

import os

import pytest

# Never download live job boards in the background during tests.
os.environ["JOB_COPILOT_PREFETCH"] = "0"


@pytest.fixture(autouse=True)
def _fresh_job_board_cache():
    """The board cache is process-wide; each test starts with it empty."""
    from resume_tailorer.job_search.scrapers.board_scraper import clear_board_cache

    clear_board_cache()
    yield
    clear_board_cache()
