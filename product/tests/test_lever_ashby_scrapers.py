from unittest.mock import patch

from resume_tailorer.job_search.job_attributes import apply_goal_filters, employment_type_for, industry_for
from resume_tailorer.job_search.models import JobSource, SearchGoals
from resume_tailorer.job_search.scrapers import AshbyScraper, LeverScraper


def _goals(title="Product Manager", job_type=""):
    return SearchGoals(
        job_title=title, industries=[], min_salary=0, max_salary=0, location="",
        remote_preference="any", sponsorship_required=False, experience_level="",
        company_size="", employment_type=job_type,
    )


LEVER_JOB = {
    "id": "abc-1",
    "text": "Senior Product Manager, Payments",
    "hostedUrl": "https://jobs.lever.co/wealthfront/abc-1",
    "createdAt": 1790000000000,
    "workplaceType": "hybrid",
    "categories": {"commitment": "Full-time", "location": "Palo Alto, CA"},
    "descriptionPlain": "Own the payments roadmap.",
    "lists": [{"text": "Requirements", "content": "<li>5+ years of product management</li><li>SQL</li>"}],
    "additionalPlain": "",
    "salaryRange": {"currency": "USD", "interval": "per-year-salary", "min": 180000, "max": 240000},
}

ASHBY_JOB = {
    "id": "xyz-9",
    "title": "Product Manager, Growth",
    "jobUrl": "https://jobs.ashbyhq.com/ramp/xyz-9",
    "location": "New York, NY",
    "publishedAt": "2026-09-20T12:00:00.000+00:00",
    "employmentType": "FullTime",
    "workplaceType": "Hybrid",
    "isListed": True,
    "descriptionPlain": "Drive growth experiments.",
    "compensation": {"compensationTiers": [
        {"components": [{"compensationType": "Salary", "interval": "1 YEAR", "currencyCode": "USD",
                         "minValue": 150000, "maxValue": 190000},
                        {"compensationType": "EquityPercentage", "interval": "NONE"}]},
        {"components": [{"compensationType": "Salary", "interval": "1 YEAR", "currencyCode": "CAD",
                         "minValue": 90000, "maxValue": 300000}]},
    ]},
}


def test_lever_maps_stated_facts_only():
    scraper = LeverScraper()
    with patch.object(scraper, "_fetch_board", lambda token: [LEVER_JOB] if token == "wealthfront" else []):
        (job,) = scraper.scrape(_goals())
    assert job.source is JobSource.LEVER and job.company == "Wealthfront"
    assert job.work_mode == "Hybrid"
    assert job.employment_type == "full-time"
    assert (job.salary_min, job.salary_max) == (180000, 240000)
    assert "5+ years of product management" in job.description
    assert job.posted_date is not None and job.sponsorship_available is None
    assert industry_for(job) == "Finance"
    assert scraper.data_source == "real"


def test_ashby_uses_usd_yearly_salary_and_never_converts_other_currencies():
    scraper = AshbyScraper()
    with patch.object(scraper, "_fetch_board", lambda token: {"jobs": [ASHBY_JOB]} if token == "ramp" else {"jobs": []}):
        (job,) = scraper.scrape(_goals())
    assert (job.salary_min, job.salary_max) == (150000, 190000)
    assert job.work_mode == "Hybrid" and job.employment_type == "full-time"
    assert job.company == "Ramp"


def test_unlisted_ashby_jobs_are_skipped():
    scraper = AshbyScraper()
    hidden = {**ASHBY_JOB, "isListed": False}
    with patch.object(scraper, "_fetch_board", lambda token: {"jobs": [hidden]}):
        assert scraper.scrape(_goals()) == []


def test_vague_commitment_is_not_guessed():
    scraper = LeverScraper()
    permanent = {**LEVER_JOB, "categories": {"commitment": "Permanent", "location": "London"}, "salaryRange": None}
    with patch.object(scraper, "_fetch_board", lambda token: [permanent]):
        job = scraper.scrape(_goals())[0]
    assert job.employment_type is None
    assert (job.salary_min, job.salary_max) == (None, None)


def test_stated_job_type_beats_title_words_in_filters():
    scraper = LeverScraper()
    intern = {**LEVER_JOB, "id": "i-1", "text": "Product Manager", "categories": {"commitment": "Internship"}}
    with patch.object(scraper, "_fetch_board", lambda token: [intern] if token == "spotify" else []):
        (job,) = scraper.scrape(_goals())
    assert employment_type_for(job) == "internship"
    assert apply_goal_filters([job], _goals(job_type="internship")) == [job]
    assert apply_goal_filters([job], _goals(job_type="full-time")) == []


def test_no_board_answering_is_reported_as_unavailable():
    scraper = AshbyScraper()
    with patch.object(scraper, "_fetch_board", lambda token: None):
        assert scraper.scrape(_goals()) == []
    assert scraper.data_source == "unavailable"


def test_employment_type_survives_the_database(tmp_path):
    from resume_tailorer.job_search.database import JobDatabase

    scraper = LeverScraper()
    with patch.object(scraper, "_fetch_board", lambda token: [LEVER_JOB] if token == "wealthfront" else []):
        (job,) = scraper.scrape(_goals())
    db = JobDatabase(str(tmp_path / "jobs.db"))
    db.create_tables()
    db.save_job_posting(job)
    stored = db.get_job_posting("lever_abc-1")
    assert stored.employment_type == "full-time" and stored.salary_max == 240000


def test_board_responses_are_reused_for_fifteen_minutes(monkeypatch):
    scraper = AshbyScraper()
    calls = []
    monkeypatch.setattr(scraper, "_make_get_request", lambda url, timeout=0: calls.append(url) or {"jobs": []})
    clock = [1000.0]
    monkeypatch.setattr("resume_tailorer.job_search.scrapers.board_scraper.time.monotonic", lambda: clock[0])

    scraper._fetch_board("ramp")
    scraper._fetch_board("ramp")
    assert len(calls) == 1
    clock[0] += AshbyScraper.CACHE_SECONDS + 1
    scraper._fetch_board("ramp")
    assert len(calls) == 2


def test_failed_board_responses_are_not_cached(monkeypatch):
    scraper = LeverScraper()
    calls = []
    monkeypatch.setattr(scraper, "_make_get_request", lambda url, timeout=0: calls.append(url))
    scraper._fetch_board("spotify")
    scraper._fetch_board("spotify")
    assert len(calls) == 2
