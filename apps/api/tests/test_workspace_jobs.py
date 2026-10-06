"""Workspace API, phase 2: Jobs (spec 009). Boards are stubbed; synthetic data only."""

from unittest.mock import patch

import pytest

from resume_tailorer.job_search.scrapers import AshbyScraper, GreenhouseScraper, LeverScraper
from resume_tailorer.job_search.scrapers.board_scraper import clear_board_cache
from resume_tailorer.job_search.scrapers.smartrecruiters_scraper import SmartRecruitersScraper
from tests.workspace_helpers import resume_docx

BOARD = {"jobs": [
    {"id": 101, "title": "Senior Data Analyst", "absolute_url": "https://job-boards.greenhouse.io/gitlab/jobs/101",
     "location": {"name": "Remote, US"}, "updated_at": "2026-09-20T12:00:00-00:00",
     "content": "&lt;p&gt;Requirements: SQL, Tableau, Python. 3+ years of analytics.&lt;/p&gt;"},
    {"id": 102, "title": "Account Executive", "absolute_url": "https://job-boards.greenhouse.io/gitlab/jobs/102",
     "location": {"name": "Remote, US"}, "updated_at": "2026-09-20T12:00:00-00:00", "content": "Sales."},
]}


@pytest.fixture()
def jobs_client(workspace_client):
    clear_board_cache()
    with patch.object(GreenhouseScraper, "_fetch_board", lambda self, token: BOARD if token == "gitlab" else {"jobs": []}), \
         patch.object(LeverScraper, "_fetch_board", lambda self, token: []), \
         patch.object(AshbyScraper, "_fetch_board", lambda self, token: {"jobs": []}), \
         patch.object(SmartRecruitersScraper, "_make_get_request", lambda self, url, timeout=10: {"content": [], "totalFound": 0}):
        yield workspace_client
    clear_board_cache()


def _search(client, **form):
    r = client.post("/v2/jobs/search", json={"job_title": "Data Analyst", **form})
    assert r.status_code == 200, r.text
    return r.json()


def test_setup_before_any_search(jobs_client):
    setup = jobs_client.get("/v2/jobs/setup").json()
    assert setup["has_goals"] is False and setup["searched"] is False
    assert {s["value"] for s in setup["options"]["sources"]} == {"greenhouse", "lever", "ashby", "smartrecruiters"}
    assert jobs_client.get("/v2/jobs").json()["state"] == "no_goals"


def test_search_lists_matching_roles_and_remembers_the_search(jobs_client):
    result = _search(jobs_client)
    assert [r["title"] for r in result["rows"]] == ["Senior Data Analyst"]
    assert result["state"] in ("results", "detail_selected")
    assert result["summary_line"].startswith("Data Analyst roles")
    # A new request (or another device) sees the same search.
    again = jobs_client.get("/v2/jobs").json()
    assert [r["job_id"] for r in again["rows"]] == ["greenhouse_101"]
    assert jobs_client.get("/v2/jobs/setup").json()["searched"] is True


def test_detail_has_evidence_once_a_profile_exists(jobs_client):
    _search(jobs_client)
    bare = jobs_client.get("/v2/jobs/greenhouse_101").json()
    assert bare["fit_measured"] is False and bare["keywords"] is None
    jobs_client.post("/v2/profile/resume", files={"file": ("r.docx", resume_docx(), "application/octet-stream")})
    detail = jobs_client.get("/v2/jobs/greenhouse_101").json()
    assert detail["fit_measured"] is True and detail["row"]["fit"].startswith("Fit ")
    assert "SQL" in detail["keywords"]["present"]
    # Spec 010: honest wording, and the shared ATS explanation.
    assert "Career Profile" in detail["keywords"]["summary"] and "on your resume" not in detail["keywords"]["summary"]
    assert detail["ats_explainer"]["title"] == "About ATS checks"
    assert detail["requirements"]["summary"].startswith(("Required:", "No requirement list"))
    assert "not an employer's ATS score" in detail["ats_explainer"]["terms_note"]
    assert "Requirements" in detail["description"]
    assert jobs_client.get("/v2/jobs/nope_1").status_code == 404


def test_save_pass_and_prepare(jobs_client):
    _search(jobs_client)
    jobs_client.post("/v2/jobs/greenhouse_101/action", json={"action": "save"})
    saved = jobs_client.get("/v2/jobs", params={"view": "saved"}).json()
    assert saved["state"] == "saved" and saved["rows"][0]["status"] == "Saved"
    prepared = jobs_client.post("/v2/jobs/greenhouse_101/action", json={"action": "apply"}).json()
    assert prepared["next"] == "/tailor"
    assert jobs_client.get("/v2/jobs/greenhouse_101").json()["active"] is True
    assert jobs_client.post("/v2/jobs/greenhouse_101/action", json={"action": "delete"}).status_code == 422


def test_search_needs_a_role_and_a_source(jobs_client):
    assert jobs_client.post("/v2/jobs/search", json={"job_title": " "}).status_code == 400
    assert jobs_client.post("/v2/jobs/search", json={"job_title": "Analyst", "sources": ["linkedin"]}).status_code == 400


def test_results_come_one_page_at_a_time(jobs_client):
    many = {"jobs": [dict(BOARD["jobs"][0], id=1000 + i, title=f"Data Analyst {i}",
                          absolute_url=f"https://job-boards.greenhouse.io/gitlab/jobs/{1000 + i}") for i in range(120)]}
    with patch.object(GreenhouseScraper, "_fetch_board", lambda self, token: many if token == "gitlab" else {"jobs": []}):
        first = _search(jobs_client)
    assert first["total"] == 120 and len(first["rows"]) == 50
    second = jobs_client.get("/v2/jobs", params={"offset": 50}).json()
    assert len(second["rows"]) == 50 and second["rows"][0]["job_id"] not in {r["job_id"] for r in first["rows"]}
    assert len(jobs_client.get("/v2/jobs", params={"offset": 100}).json()["rows"]) == 20


def test_times_reach_the_browser_with_their_utc_offset():
    """Naive server-local times would be read as the browser's own local time (decision 030)."""
    from datetime import date, datetime, timezone

    from app.workspace.context import jsonable, stamp

    naive = datetime(2026, 10, 5, 18, 29)
    sent = datetime.fromisoformat(stamp(naive))
    assert sent.tzinfo is not None and sent == naive.astimezone()
    aware = datetime(2026, 10, 5, 18, 29, tzinfo=timezone.utc)
    assert stamp(aware) == "2026-10-05T18:29:00+00:00"
    assert jsonable({"d": date(2026, 10, 5), "t": aware}) == {"d": "2026-10-05", "t": "2026-10-05T18:29:00+00:00"}
