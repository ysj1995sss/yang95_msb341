import pytest
from unittest.mock import patch, MagicMock
from resume_tailorer.job_search.scrapers.greenhouse_scraper import GreenhouseScraper
from resume_tailorer.job_search.models import SearchGoals, JobSource


def _make_goals(job_title="Software Engineer", location="Remote"):
    return SearchGoals(
        job_title=job_title,
        industries=["Technology"],
        min_salary=80000,
        max_salary=150000,
        location=location,
        remote_preference="any",
        sponsorship_required=False,
        experience_level="mid",
        company_size="any",
    )


def _fake_greenhouse_response(job_count=2):
    """Simulate the shape of a real Greenhouse boards-api /jobs response."""
    return {
        "jobs": [
            {
                "id": 1000 + i,
                "title": f"Software Engineer {i}",
                "absolute_url": f"https://boards.greenhouse.io/examplecompany/jobs/{1000 + i}",
                "location": {"name": "Remote - US"},
                "content": "<p>We are hiring a software engineer to join our team.</p>",
                "updated_at": "2026-09-01T12:00:00-00:00",
                "departments": [{"name": "Engineering"}],
            }
            for i in range(job_count)
        ]
    }


def test_scrape_uses_real_api_when_available():
    """When the Greenhouse API responds successfully, scrape() returns real JobPostings, not mock data."""
    scraper = GreenhouseScraper()
    goals = _make_goals()

    with patch.object(scraper, "_make_get_request", return_value=_fake_greenhouse_response(job_count=2)):
        results = scraper.scrape(goals)

    assert len(results) >= 1
    assert scraper.data_source == "real"
    assert all(job.source == JobSource.GREENHOUSE for job in results)
    assert all(job.url.startswith("https://boards.greenhouse.io/") for job in results)


def test_scrape_maps_greenhouse_fields_correctly():
    """Real API job fields map correctly onto JobPosting attributes."""
    scraper = GreenhouseScraper()
    goals = _make_goals()

    with patch.object(scraper, "_make_get_request", return_value=_fake_greenhouse_response(job_count=1)):
        results = scraper.scrape(goals)

    job = results[0]
    assert job.source_id == "1000"
    assert job.title == "Software Engineer 0"
    assert job.location == "Remote - US"
    assert job.url == "https://boards.greenhouse.io/examplecompany/jobs/1000"
    assert job.ats_platform == "Greenhouse"
    # company is derived from the board token, title-cased for display
    assert job.company == GreenhouseScraper.GREENHOUSE_BOARD_TOKENS[0].title()


def test_map_greenhouse_job_title_cases_board_token():
    """The board token is presented title-cased (e.g. 'airbnb' -> 'Airbnb')."""
    scraper = GreenhouseScraper()
    raw = {
        "id": 55,
        "title": "Software Engineer",
        "absolute_url": "https://boards.greenhouse.io/some-co/jobs/55",
        "location": {"name": "Remote"},
        "content": "<p>hi</p>",
    }

    job = scraper._map_greenhouse_job(raw, "some-co")

    assert job.company == "Some Co"


def test_map_greenhouse_job_unescapes_double_encoded_html_content():
    """Found live (2026-09-24): a real Greenhouse board returned `content`
    double-encoded -- literal '&lt;div class=&quot;...&quot;&gt;' text, not
    real '<div ...>' tags. The tag-stripping regex only matches literal
    angle brackets, so this markup previously leaked straight into the JD
    text a candidate pastes into the tailorer."""
    scraper = GreenhouseScraper()
    raw = {
        "id": 56,
        "title": "Software Engineer",
        "absolute_url": "https://boards.greenhouse.io/some-co/jobs/56",
        "location": {"name": "Remote"},
        "content": (
            "&lt;div class=&quot;content-intro&quot;&gt;&lt;p&gt;"
            "&lt;span style=&quot;font-family: helvetica&quot;&gt;"
            "Airbnb was born in 2007.&lt;/span&gt;&lt;/p&gt;&lt;/div&gt;"
        ),
    }

    job = scraper._map_greenhouse_job(raw, "some-co")

    assert "<" not in job.description
    assert "&lt;" not in job.description
    assert "&quot;" not in job.description
    assert job.description == "Airbnb was born in 2007."


def test_scrape_real_filters_postings_by_goal_job_title():
    """Real postings whose titles don't match the goal title are dropped BEFORE
    URL validation, so we don't liveness-check every open req on every board."""
    scraper = GreenhouseScraper()
    goals = _make_goals(job_title="Software Engineer")

    mixed_response = {
        "jobs": [
            {
                "id": 1,
                "title": "Senior Software Engineer",
                "absolute_url": "https://boards.greenhouse.io/x/jobs/1",
                "location": {"name": "Remote"},
                "content": "<p>eng</p>",
            },
            {
                "id": 2,
                "title": "Marketing Manager",
                "absolute_url": "https://boards.greenhouse.io/x/jobs/2",
                "location": {"name": "Remote"},
                "content": "<p>mkt</p>",
            },
        ]
    }

    with patch.object(scraper, "_make_get_request", return_value=mixed_response):
        results = scraper._scrape_real(goals)

    titles = {job.title for job in results}
    assert "Senior Software Engineer" in titles
    assert "Marketing Manager" not in titles


def test_scrape_real_excludes_partially_matching_titles():
    """A title matching only SOME of the goal's title keywords must be excluded (AND semantics, not OR).

    Regression test: 'Software Engineer' previously matched via OR-semantics
    against any title containing EITHER 'Software' OR 'Engineer' alone,
    letting through unrelated roles like 'Engineering Manager, Guest & Host'.
    """
    scraper = GreenhouseScraper()
    goals = _make_goals(job_title="Software Engineer")

    # This title contains "Engineer" but not "Software" - must NOT match.
    partial_match_response = {
        "jobs": [
            {
                "id": 3000,
                "title": "Engineering Manager, Guest Experience",
                "absolute_url": "https://boards.greenhouse.io/examplecompany/jobs/3000",
                "location": {"name": "Remote"},
                "content": "<p>Manager role.</p>",
                "updated_at": "2026-09-01T12:00:00-00:00",
                "departments": [],
            }
        ]
    }

    with patch.object(scraper, "_make_get_request", return_value=partial_match_response):
        results = scraper.scrape(goals)

    # Since the real API path returns zero true matches (the only real job doesn't
    # fully match), scrape() should fall back to mock data (data_source == "mock"),
    # NOT return the partially-matching real job.
    assert scraper.data_source == "mock"
    assert not any(job.title == "Engineering Manager, Guest Experience" for job in results)


def test_filter_by_goals_returns_all_when_no_job_title():
    """With no job title in goals there is nothing to pre-filter on."""
    scraper = GreenhouseScraper()
    goals = _make_goals(job_title="")

    with patch.object(scraper, "_make_get_request", return_value=_fake_greenhouse_response(job_count=2)):
        results = scraper._scrape_real(goals)

    assert len(results) == 2 * len(GreenhouseScraper.GREENHOUSE_BOARD_TOKENS)


def test_scrape_handles_missing_optional_fields_as_unknown():
    """A job JSON missing salary/experience info maps to 'Unknown', never a fabricated value."""
    scraper = GreenhouseScraper()
    goals = _make_goals(job_title="Data Analyst")

    sparse_response = {
        "jobs": [
            {
                "id": 2000,
                "title": "Data Analyst",
                "absolute_url": "https://boards.greenhouse.io/examplecompany/jobs/2000",
                "location": {"name": "New York, NY"},
                "content": "<p>Analyst role.</p>",
                "updated_at": "2026-09-01T12:00:00-00:00",
                "departments": [],
            }
        ]
    }

    with patch.object(scraper, "_make_get_request", return_value=sparse_response):
        results = scraper.scrape(goals)

    job = results[0]
    assert job.salary_min is None
    assert job.salary_max is None
    assert job.experience_required == "Unknown"
    assert job.education_required == "Unknown"


def test_scrape_falls_back_to_mock_when_api_unavailable():
    """When the real API call fails (returns None), scrape() falls back to mock data and flags data_source='mock'."""
    scraper = GreenhouseScraper()
    goals = _make_goals()

    with patch.object(scraper, "_make_get_request", return_value=None):
        results = scraper.scrape(goals)

    assert len(results) >= 1
    assert scraper.data_source == "mock"
    assert all(job.source == JobSource.GREENHOUSE for job in results)


def test_scrape_falls_back_to_mock_on_empty_real_response():
    """When the real API returns zero jobs across all board tokens, scrape() falls back to mock (better demo experience than empty results)."""
    scraper = GreenhouseScraper()
    goals = _make_goals()

    with patch.object(scraper, "_make_get_request", return_value={"jobs": []}):
        results = scraper.scrape(goals)

    assert len(results) >= 1
    assert scraper.data_source == "mock"


def test_scrape_queries_multiple_board_tokens():
    """scrape() attempts multiple company board tokens, not just one, to maximize real results."""
    scraper = GreenhouseScraper()
    goals = _make_goals()
    call_count = {"n": 0}

    def fake_request(url, timeout=10):
        call_count["n"] += 1
        return _fake_greenhouse_response(job_count=1)

    with patch.object(scraper, "_make_get_request", side_effect=fake_request):
        scraper.scrape(goals)

    assert call_count["n"] == len(GreenhouseScraper.GREENHOUSE_BOARD_TOKENS)


def test_make_get_request_returns_none_on_http_error():
    """BaseScraper._make_get_request returns None (never raises) when the request fails."""
    scraper = GreenhouseScraper()

    with patch("resume_tailorer.job_search.scrapers.base_scraper.requests.get") as mock_get:
        mock_get.side_effect = Exception("Connection refused")
        result = scraper._make_get_request("https://boards-api.greenhouse.io/v1/boards/fake/jobs")

    assert result is None


def test_make_get_request_returns_none_on_non_200_status():
    """BaseScraper._make_get_request returns None when the server responds with a non-200 status."""
    scraper = GreenhouseScraper()

    mock_response = MagicMock()
    mock_response.status_code = 404

    with patch("resume_tailorer.job_search.scrapers.base_scraper.requests.get", return_value=mock_response):
        result = scraper._make_get_request("https://boards-api.greenhouse.io/v1/boards/fake/jobs")

    assert result is None

def test_make_get_request_returns_json_on_success():
    """BaseScraper._make_get_request returns the parsed JSON dict on a 200 response."""
    scraper = GreenhouseScraper()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"jobs": []}

    with patch("resume_tailorer.job_search.scrapers.base_scraper.requests.get", return_value=mock_response):
        result = scraper._make_get_request("https://boards-api.greenhouse.io/v1/boards/fake/jobs")

    assert result == {"jobs": []}
