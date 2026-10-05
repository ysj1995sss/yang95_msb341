"""Search speed: title check before mapping, shared board cache, warm-up, batching (decision 027)."""

import threading
import time
from datetime import datetime
from unittest.mock import patch

from resume_tailorer.job_search.deduplicator import JobDeduplicator
from resume_tailorer.job_search.models import JobPosting, JobSource, SearchGoals
from resume_tailorer.job_search.scrapers import board_scraper
from resume_tailorer.job_search.scrapers.greenhouse_scraper import GreenhouseScraper


def _goals(title="Data Analyst"):
    return SearchGoals(job_title=title, industries=[], min_salary=0, max_salary=0, location="",
                       remote_preference="any", sponsorship_required=False, experience_level="any",
                       company_size="any")


def _board(titles):
    return {"jobs": [{"id": i, "title": t, "absolute_url": f"https://boards.example/{i}",
                      "content": "&lt;p&gt;Role&lt;/p&gt;", "location": {"name": "Remote"},
                      "updated_at": "2026-10-01T00:00:00Z"} for i, t in enumerate(titles)]}


def test_postings_with_other_titles_are_never_mapped():
    scraper = GreenhouseScraper()
    scraper.board_tokens = lambda: ["acme"]
    data = _board(["Data Analyst", "Account Executive", "Software Engineer"])
    mapped = []
    original = scraper.map_job
    with patch.object(scraper, "_make_get_request", return_value=data), \
         patch.object(scraper, "map_job", side_effect=lambda raw, token: mapped.append(raw["title"]) or original(raw, token)):
        scraper.scrape(_goals())
    assert mapped == ["Data Analyst"]


def test_a_board_fetched_by_one_scraper_serves_another():
    first, second = GreenhouseScraper(), GreenhouseScraper()
    with patch.object(first, "_make_get_request", return_value=_board(["Data Analyst"])) as one, \
         patch.object(second, "_make_get_request", return_value=None) as two:
        first._fetch_board("acme")
        assert second._fetch_board("acme") == _board(["Data Analyst"])
    assert one.call_count == 1 and two.call_count == 0


def test_concurrent_fetches_of_one_board_share_a_single_request():
    scraper = GreenhouseScraper()
    calls = []

    def slow(url, timeout):
        calls.append(url)
        time.sleep(0.2)
        return _board(["Data Analyst"])

    with patch.object(scraper, "_make_get_request", side_effect=slow):
        results = []
        threads = [threading.Thread(target=lambda: results.append(scraper._fetch_board("acme"))) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    assert len(calls) == 1 and len(results) == 4 and all(results)


def test_warm_up_runs_at_most_once_per_cache_window():
    scraper = GreenhouseScraper()
    scraper.board_tokens = lambda: ["acme"]
    with patch.object(scraper, "_make_get_request", return_value=_board(["Data Analyst"])):
        assert board_scraper.warm_board_cache([scraper]) is True
        assert board_scraper.warm_board_cache([scraper]) is False
        for _ in range(50):
            if scraper._board_cache:
                break
            time.sleep(0.02)
    assert scraper._board_cache


def test_warm_up_is_off_in_tests(tmp_path):
    from resume_tailorer.job_search.job_service import JobService

    service = JobService(str(tmp_path / "j.db"), str(tmp_path / "a.db"))
    assert service.warm_up() is False


def test_deduplication_still_merges_across_sources():
    def posting(source, sid, url):
        return JobPosting(source=source, source_id=sid, company="Acme", title="Data Analyst", location="Remote",
                          description="", posted_date=datetime(2026, 10, 1), url=url)
    many = [posting(JobSource.GREENHOUSE, str(i), f"https://a.example/{i}") for i in range(300)]
    many[0] = posting(JobSource.GREENHOUSE, "x", "")
    many.append(posting(JobSource.LEVER, "y", ""))
    merged = JobDeduplicator().deduplicate(many)
    # Same result as before the index: the Lever posting joins the first compatible cluster.
    assert len(merged) == 300
    assert any(p.source == JobSource.GREENHOUSE and p.source_id == "1" for p in merged)
