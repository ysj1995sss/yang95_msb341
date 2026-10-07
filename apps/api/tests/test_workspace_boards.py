"""Workspace API, spec 013: adding company career boards and searches that explain themselves.
Boards and platform checks are stubbed; synthetic companies only."""

from unittest.mock import patch

import pytest

from resume_tailorer.job_search import board_links
from resume_tailorer.job_search.scrapers import AshbyScraper, GreenhouseScraper, LeverScraper
from resume_tailorer.job_search.scrapers.board_scraper import clear_board_cache
from resume_tailorer.job_search.scrapers.smartrecruiters_scraper import SmartRecruitersScraper

NORTHWIND = {"jobs": [
    {"id": 701, "title": "Data Analyst", "absolute_url": "https://job-boards.greenhouse.io/northwind/jobs/701",
     "location": {"name": "Austin, TX"}, "updated_at": "2026-10-01T12:00:00-00:00", "content": "SQL and Tableau."},
]}
GITLAB = {"jobs": [
    {"id": 101, "title": "Data Analyst", "absolute_url": "https://job-boards.greenhouse.io/gitlab/jobs/101",
     "location": {"name": "Remote, US"}, "updated_at": "2026-10-01T12:00:00-00:00", "content": "SQL."},
]}


def platform_answers(url):
    """What the platforms' public APIs say about a few synthetic boards."""
    if url == "https://boards-api.greenhouse.io/v1/boards/northwind":
        return 200, {"name": "Northwind Outdoor"}
    if url == "https://boards-api.greenhouse.io/v1/boards/northwind/jobs":
        return 200, NORTHWIND
    if url.startswith("https://api.lever.co/v0/postings/slowco"):
        return None, None
    if url.startswith("https://api.smartrecruiters.com/"):
        return 200, {"totalFound": 0, "content": []}
    return 404, {"error": "not found"}


@pytest.fixture()
def boards_client(workspace_client):
    clear_board_cache()
    boards = {"gitlab": GITLAB, "northwind": NORTHWIND}
    with patch.object(board_links, "http_fetch", platform_answers), \
         patch.object(GreenhouseScraper, "_fetch_board", lambda self, token: boards.get(token, {"jobs": []})), \
         patch.object(LeverScraper, "_fetch_board", lambda self, token: []), \
         patch.object(AshbyScraper, "_fetch_board", lambda self, token: {"jobs": []}), \
         patch.object(SmartRecruitersScraper, "_make_get_request", lambda self, url, timeout=10: {"content": [], "totalFound": 0}):
        yield workspace_client
    clear_board_cache()


def _add(client, url, **extra):
    return client.post("/v2/boards", json={"url": url, **extra})


def test_add_list_and_remove_a_board(boards_client):
    before = boards_client.get("/v2/jobs/setup").json()
    assert before["custom_boards"] == [] and before["max_custom_boards"] == 25
    assert before["options"]["sources"][0]["label"].startswith("Greenhouse: ")
    assert "not every company on that platform" in before["help"]["sources"]

    r = _add(boards_client, "https://job-boards.greenhouse.io/northwind/jobs/701", industry="Retail")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["message"] == "Added Northwind Outdoor (Greenhouse): 1 open posting right now."
    assert body["board"]["platform"] == "Greenhouse" and body["board"]["industry"] == "Retail"
    assert body["board"]["status"].startswith("Verified with 1 open posting")

    setup = boards_client.get("/v2/jobs/setup").json()
    assert [b["id"] for b in setup["custom_boards"]] == ["greenhouse:northwind"]
    assert setup["board_count"] == setup["all_curated_count"] + 1
    assert boards_client.get("/v2/boards").json()["custom_boards"][0]["name"] == "Northwind Outdoor"

    assert boards_client.delete("/v2/boards/greenhouse:northwind").status_code == 200
    assert boards_client.get("/v2/boards").json()["custom_boards"] == []
    assert boards_client.delete("/v2/boards/greenhouse:northwind").status_code == 404


@pytest.mark.parametrize("url, status, words", [
    ("https://careers.northwind.example/jobs", 400, "company's own site"),
    ("https://www.linkedin.com/jobs/view/1", 400, "LinkedIn boards aren't supported"),
    ("https://boards.greenhouse.io/gitlab", 409, "already searched by default"),
    ("https://jobs.lever.co/nosuchco", 422, "no public board called 'nosuchco'"),
    ("https://jobs.smartrecruiters.com/NorthwindGroup", 422, "can't be confirmed"),
    ("https://jobs.lever.co/slowco", 502, "didn't answer"),
])
def test_boards_that_cannot_be_added_say_why_and_save_nothing(boards_client, url, status, words):
    r = _add(boards_client, url)
    assert r.status_code == status and words in r.json()["detail"]
    assert boards_client.get("/v2/boards").json()["custom_boards"] == []


def test_duplicates_are_refused(boards_client):
    assert _add(boards_client, "boards.greenhouse.io/northwind").status_code == 200
    r = _add(boards_client, "https://job-boards.greenhouse.io/Northwind/jobs/9")
    assert r.status_code == 409 and "already added" in r.json()["detail"]


def test_searches_include_added_boards_and_label_their_jobs(boards_client):
    _add(boards_client, "boards.greenhouse.io/northwind")
    r = boards_client.post("/v2/jobs/search", json={"job_title": "Data Analyst"})
    assert r.status_code == 200, r.text
    rows = {row["company"]: row for row in r.json()["rows"]}
    assert set(rows) == {"Northwind Outdoor", "GitLab"}
    assert rows["Northwind Outdoor"]["added_board"] is True
    assert rows["Northwind Outdoor"]["source"] == "Greenhouse · board you added"
    assert rows["GitLab"]["added_board"] is False
    result = boards_client.get("/v2/jobs").json()
    assert result["boards_line"].startswith("Searched ") and result["failed_boards"] == []
    detail = boards_client.get(f"/v2/jobs/{rows['Northwind Outdoor']['job_id']}").json()
    assert detail["row"]["source"] == "Greenhouse · board you added"
    assert dict(map(tuple, detail["facts"]))["Industry"] == "Not specified"
    (board,) = boards_client.get("/v2/boards").json()["custom_boards"]
    assert board["status"].startswith("1 matching role at the last search")


def test_added_boards_alone_can_be_searched(boards_client):
    _add(boards_client, "boards.greenhouse.io/northwind")
    r = boards_client.post("/v2/jobs/search", json={"job_title": "Data Analyst", "sources": []})
    assert [row["company"] for row in r.json()["rows"]] == ["Northwind Outdoor"]
    assert boards_client.get("/v2/jobs/setup").json()["form"]["sources"] == []
    r = boards_client.post("/v2/jobs/search", json={"job_title": "Data Analyst", "sources": [], "include_custom": False})
    assert r.status_code == 400


def test_a_failing_added_board_is_named(boards_client):
    _add(boards_client, "boards.greenhouse.io/northwind")
    with patch.object(GreenhouseScraper, "_fetch_board", lambda self, token: None if token == "northwind" else {"jobs": []}):
        boards_client.post("/v2/jobs/search", json={"job_title": "Data Analyst"})
    result = boards_client.get("/v2/jobs").json()
    assert result["failed_boards"] == ["Northwind Outdoor (Greenhouse)"]
    assert "Northwind Outdoor (Greenhouse)" in result["boards_line"]
    (board,) = boards_client.get("/v2/boards").json()["custom_boards"]
    assert board["tone"] == "review" and board["status"].startswith("Didn't answer")


def test_sponsorship_keeps_unstated_jobs_and_says_so(boards_client):
    r = boards_client.post("/v2/jobs/search", json={"job_title": "Data Analyst", "sponsorship_required": True})
    (row,) = r.json()["rows"]
    assert row["sponsorship_note"] == "Sponsorship not stated — check the posting"


def test_few_results_explain_filters_titles_and_companies(boards_client):
    r = boards_client.post("/v2/jobs/search", json={
        "job_title": "Senior Data Analyst", "location": "Austin", "target_companies": "gitlab, Stripe"})
    result = r.json()
    assert result["total"] == 0
    assert result["broader_titles"][0] == "Data Analyst"
    assert any("Stripe" in note for note in result["company_notes"])
    assert all("gitlab" not in note.lower() for note in result["company_notes"])
    r = boards_client.post("/v2/jobs/search", json={"job_title": "Data Analyst", "location": "Austin"})
    result = r.json()
    assert result["total"] == 0  # GitLab's role is remote, not in Austin
    assert [n["key"] for n in result["narrowing"]] == ["location"]
    assert result["narrowing"][0]["extra"] == 1


def test_board_checks_are_limited_per_day(boards_client, monkeypatch):
    monkeypatch.setenv("BOARD_CHECKS_PER_DAY", "1")
    assert _add(boards_client, "jobs.lever.co/nosuchco").status_code == 422  # a real check: counted
    assert _add(boards_client, "https://careers.example/").status_code == 400  # no check: not counted
    r = _add(boards_client, "boards.greenhouse.io/northwind")
    assert r.status_code == 429 and "career-board checks" in r.json()["detail"]
