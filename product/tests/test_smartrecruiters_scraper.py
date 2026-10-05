"""SmartRecruiters, a fourth live source (decision 027). Shapes follow the public API."""

from resume_tailorer.job_search.job_service import JobService
from resume_tailorer.job_search.models import JobSource, SearchGoals
from resume_tailorer.job_search.scrapers.smartrecruiters_scraper import SmartRecruitersScraper


def _goals(title="Data Analyst"):
    return SearchGoals(job_title=title, industries=[], min_salary=0, max_salary=0, location="",
                       remote_preference="any", sponsorship_required=False, experience_level="any",
                       company_size="any")


LIST = {"totalFound": 2, "content": [
    {"id": "111", "name": "Senior Data Analyst", "company": {"name": "Acme"}},
    {"id": "222", "name": "Software Engineer", "company": {"name": "Acme"}},
]}
DETAIL = {
    "id": "111", "name": "Senior Data Analyst", "active": True,
    "company": {"identifier": "Acme", "name": "Acme"},
    "releasedDate": "2026-10-03T16:02:30.623Z",
    "location": {"fullLocation": "Denver, CO, United States", "remote": False, "hybrid": True},
    "typeOfEmployment": {"label": "Full-time"},
    "postingUrl": "https://jobs.smartrecruiters.com/Acme/111-senior-data-analyst",
    "jobAd": {"sections": {
        "jobDescription": {"title": "Job Description", "text": "<p>Own weekly KPI reporting.</p>"},
        "qualifications": {"title": "Qualifications", "text": "<ul><li>SQL</li><li>Tableau</li></ul>"},
    }},
}


def _fake(urls):
    def get(url, timeout=10):
        urls.append(url)
        if url.endswith("/postings/111"):
            return DETAIL
        if "/postings?" in url:
            return LIST
        return None
    return get


def test_only_matching_titles_are_fetched_in_full_and_mapped(monkeypatch):
    scraper = SmartRecruitersScraper()
    scraper.board_tokens = lambda: ["Acme"]
    urls = []
    monkeypatch.setattr(scraper, "_make_get_request", _fake(urls))
    (job,) = scraper.scrape(_goals())
    assert not any(u.endswith("/postings/222") for u in urls)
    assert "q=Data%20Analyst" in urls[0]
    assert job.source == JobSource.SMARTRECRUITERS and job.ats_platform == "SmartRecruiters"
    assert (job.company, job.location, job.work_mode, job.employment_type) == (
        "Acme", "Denver, CO, United States", "Hybrid", "full-time")
    assert "Own weekly KPI reporting." in job.description and "Tableau" in job.description
    assert job.url.startswith("https://jobs.smartrecruiters.com/")


def test_a_company_that_does_not_answer_is_reported_not_fatal(monkeypatch):
    scraper = SmartRecruitersScraper()
    scraper.board_tokens = lambda: ["Acme", "Down"]
    urls = []
    fake = _fake(urls)
    monkeypatch.setattr(scraper, "_make_get_request", lambda url, timeout=10: None if "/Down/" in url else fake(url))
    assert len(scraper.scrape(_goals())) == 1
    assert scraper.data_source == "real" and "1 of 2" in scraper.coverage_note


def test_nothing_answering_means_unavailable(monkeypatch):
    scraper = SmartRecruitersScraper()
    monkeypatch.setattr(scraper, "_make_get_request", lambda url, timeout=10: None)
    assert scraper.scrape(_goals()) == [] and scraper.data_source == "unavailable"


def test_the_product_offers_only_live_sources(tmp_path):
    service = JobService(str(tmp_path / "j.db"), str(tmp_path / "a.db"))
    assert set(service.scraper_map) == {JobSource.GREENHOUSE, JobSource.LEVER, JobSource.ASHBY,
                                        JobSource.SMARTRECRUITERS}


def test_slow_postings_do_not_hold_up_the_search(monkeypatch):
    import time

    scraper = SmartRecruitersScraper()
    scraper.board_tokens = lambda: ["Acme"]
    scraper.DETAIL_BUDGET_SECONDS = 0.2
    fake = _fake([])

    def slow(url, timeout=10):
        if url.endswith("/postings/111"):
            time.sleep(1)
        return fake(url)

    monkeypatch.setattr(scraper, "_make_get_request", slow)
    started = time.monotonic()
    assert scraper.scrape(_goals()) == []
    assert time.monotonic() - started < 0.9
    assert "still loading" in scraper.coverage_note
