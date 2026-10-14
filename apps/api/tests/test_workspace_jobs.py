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


def test_location_suggestions_start_common_and_learn_from_postings(jobs_client):
    # Location dropdown (2026-10-13): common places before any search, then the places real postings name.
    before = jobs_client.get("/v2/jobs/setup").json()["options"]["locations"]
    assert "United States" in before and "Remote" in before
    _search(jobs_client)
    after = jobs_client.get("/v2/jobs/setup").json()["options"]["locations"]
    assert after[0] == "Remote" and "US" not in after  # from "Remote, US"; two letters would match too much


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
    # Decision 047: the share of the posting's requirements your facts show, explained honestly.
    assert detail["fit_measured"] is True and detail["row"]["fit"].startswith("Match ")
    assert "not an employer's ATS score" in detail["match_note"]
    assert [name for name, _value in detail["fit_parts"]] == ["Required qualifications", "Preferred qualifications",
                                                              "Requirements counted"]
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
    # Round 6 bug hunt: a role with no words matched every job (10,870) and took 30 seconds.
    for empty in ("!!!", "the and of"):
        assert jobs_client.post("/v2/jobs/search", json={"job_title": empty}).status_code == 400
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


def test_a_failed_search_says_so_without_internal_details(jobs_client, monkeypatch, caplog):
    # Dogfood, 2026-10-13: any error inside the search was pasted into the message people see.
    from resume_tailorer.job_search.job_service import JobService

    def broken(self, *args, **kwargs):
        raise RuntimeError("database is locked at D:/data/owner/jobs.db")

    monkeypatch.setattr(JobService, "search_and_store", broken)
    response = jobs_client.post("/v2/jobs/search", json={"job_title": "Data Analyst"})
    assert response.status_code == 502
    assert "didn't finish" in response.json()["detail"] and "jobs.db" not in response.json()["detail"]
    assert any(r.exc_info and "jobs.db" in str(r.exc_info[1]) for r in caplog.records)  # kept for diagnosis


def test_saving_a_job_counts_as_saved_on_home_and_tracker(jobs_client):
    # Dogfood, 2026-10-13: Home said "0 saved" right above a "Saved jobs" list with a job in it:
    # the count was tracker entries in a "saved" status, which the website never creates.
    _search(jobs_client)
    assert jobs_client.post("/v2/jobs/greenhouse_101/action", json={"action": "save"}).status_code == 200
    assert jobs_client.get("/v2/home").json()["weekly"]["saved"] == 1
    assert jobs_client.get("/v2/tracker").json()["weekly"]["saved"] == 1


def test_a_remote_search_starts_with_only_jobs_that_say_they_are_remote(jobs_client):
    # Dogfood round 4: with Remote chosen, 20 of 27 results were city-only listings (Gurugram,
    # Toronto) until the person found the checkbox. Remote now starts with it ticked.
    jobs_client.put("/v2/profile/goals", json={"job_title": "Data Analyst", "remote_preference": "remote"})
    assert jobs_client.get("/v2/jobs/setup").json()["form"]["work_mode_stated_only"] is True
    jobs_client.post("/v2/jobs/search", json={"job_title": "Data Analyst", "remote_preference": "remote",
                                              "work_mode_stated_only": False})
    assert jobs_client.get("/v2/jobs/setup").json()["form"]["work_mode_stated_only"] is False  # their choice is kept


def test_only_jobs_that_state_the_work_mode_is_a_remembered_search_option(jobs_client):
    # Dogfood round 2, 2026-10-13: "Remote" mostly listed jobs whose work mode isn't stated.
    stated = jobs_client.post("/v2/jobs/search", json={"job_title": "Data Analyst", "remote_preference": "hybrid",
                                                       "work_mode_stated_only": True}).json()
    assert stated["rows"] == []  # the board's only match says "Remote, US", so it is Remote, not hybrid
    assert jobs_client.get("/v2/jobs/setup").json()["form"]["work_mode_stated_only"] is True
    remote = jobs_client.post("/v2/jobs/search", json={"job_title": "Data Analyst", "remote_preference": "remote",
                                                       "work_mode_stated_only": True}).json()
    assert [r["title"] for r in remote["rows"]] == ["Senior Data Analyst"]


MANY = {"jobs": [
    {"id": 200 + n, "title": f"Data Analyst {n}", "absolute_url": f"https://job-boards.greenhouse.io/gitlab/jobs/{200 + n}",
     "location": {"name": "Remote, US"}, "updated_at": "2026-09-20T12:00:00-00:00",
     "content": "Requirements: SQL. Tableau." if n == 2 else "Requirements: Kubernetes. Terraform. Golang. Kafka."}
    for n in range(4)
]}


def test_a_large_search_ranks_by_a_quick_pass_and_still_shows_a_match_on_every_row(jobs_client):
    # Full Match scoring for thousands of jobs is too slow for one request (decision 047): the quick
    # pass picks the top jobs, and every row on the page shown still gets its full Match.
    from app.workspace import jobs_router

    jobs_client.post("/v2/profile/resume", files={"file": ("r.docx", resume_docx(), "application/octet-stream")})
    with patch.object(GreenhouseScraper, "_fetch_board", lambda self, token: MANY if token == "gitlab" else {"jobs": []}), \
         patch.object(jobs_router, "FULL_MATCH_LIMIT", 1):
        clear_board_cache()
        result = _search(jobs_client)
    assert result["rows"][0]["title"] == "Data Analyst 2"  # the posting asking for what you have
    assert len(result["rows"]) == 4 and all(r["fit"].startswith("Match ") for r in result["rows"])


def test_choices_read_in_list_order_whatever_order_they_were_picked(jobs_client):
    """Round 6 bug hunt: levels picked Senior, then Mid in the goals wizard read "senior, mid"."""
    jobs_client.put("/v2/profile/goals", json={"job_title": "Data Analyst", "experience_level": ["senior", "mid"],
                                              "industries": ["Technology", "Finance"]})
    setup = jobs_client.get("/v2/jobs/setup").json()
    assert setup["form"]["experience_level"] == ["mid", "senior"]
    assert setup["form"]["industries"] == ["Finance", "Technology"]
    assert "mid, senior" in setup["summary_line"]
