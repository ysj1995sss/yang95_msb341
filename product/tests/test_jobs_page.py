"""Jobs page behaviour on the real Streamlit page (spec 008). Synthetic data only;
the job boards are stubbed."""

from pathlib import Path
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from resume_tailorer.job_search.job_service import PENDING_TAILOR_JOB_KEY
from resume_tailorer.job_search.scrapers import AshbyScraper, GreenhouseScraper, LeverScraper
from resume_tailorer.models import CareerTruthProfile
from resume_tailorer.profile_import import import_resume, store_for

APP = str(Path(__file__).resolve().parent.parent / "resume_tailorer" / "app.py")

PROFILE = {
    "contact_info": {"name": "Riley Park", "email": "riley@example.com", "phone": "", "location": ""},
    "education": [{"degree": "BS", "field": "Economics", "institution": "State U", "year": 2017, "gpa": None, "notes": []}],
    "work_experience": [{"employer": "Acme", "title": "Product Manager", "dates": "2019-2024",
                         "responsibilities": ["Led the analytics roadmap"], "accomplishments": []}],
    "skills": ["Product Management", "SQL"], "tools": [], "certifications": [], "accomplishments": [], "summary": "",
}

BOARD = {"jobs": [
    {"id": 1, "title": "Product Manager, Growth", "absolute_url": "https://job-boards.greenhouse.io/gitlab/jobs/1",
     "location": {"name": "Remote"}, "content": "<p>Own growth. Requirements: product management, SQL.</p>",
     "updated_at": "2026-09-20T12:00:00-00:00"},
    {"id": 2, "title": "Senior Product Manager, Data", "absolute_url": "https://job-boards.greenhouse.io/gitlab/jobs/2",
     "location": {"name": "Denver, CO"}, "content": "<p>Own data products. Requirements: product management, Kubernetes.</p>",
     "updated_at": "2026-09-30T12:00:00-00:00"},
]}


class StubParser:
    def parse(self, path):
        return CareerTruthProfile.from_dict(PROFILE)


def _board(self, token):
    return BOARD if token == "gitlab" else {"jobs": []}


def _failing(self, token):
    raise ConnectionError("board unreachable")


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("JOB_COPILOT_DATA_DIR", str(tmp_path / "data"))
    store = store_for("local")
    import_resume(store, "riley.docx", b"synthetic", parser=StubParser())
    record = store.load()
    record["preferences"] = {"job_title": "Product Manager", "remote_preference": "any"}
    store.save(record)
    with patch.object(GreenhouseScraper, "_fetch_board", _board), \
         patch.object(LeverScraper, "_fetch_board", lambda self, token: []), \
         patch.object(AshbyScraper, "_fetch_board", lambda self, token: {"jobs": []}):
        at = AppTest.from_file(APP, default_timeout=60)
        at.switch_page("pages/2_Job_Search.py")
        at.run()
        assert not at.exception, at.exception
        yield at


def _click(at, label, index=0):
    buttons = [b for b in at.button if b.label == label]
    assert buttons, [b.label for b in at.button]
    buttons[index].click()
    at.run()
    assert not at.exception, at.exception


def _text(at):
    return "\n".join(m.value for m in at.markdown)


def _search(at):
    _click(at, "Find matching jobs")
    assert "Product Manager, Growth" in _text(at)


def test_saved_goals_show_a_summary_not_a_form_or_stepper(app):
    text = _text(app)
    assert "Product Manager roles · Anywhere" in text
    assert "Set goals" not in text and "Prepare application" not in text
    assert not [t for t in app.text_input if t.key == "job_title"]


def test_results_keep_the_selection_on_rerun_and_follow_a_new_choice(app):
    _search(app)
    first = app.radio(key="w_jobs_selected").value
    app.run()
    assert app.radio(key="w_jobs_selected").value == first
    other = "greenhouse_2" if first == "greenhouse_1" else "greenhouse_1"
    app.radio(key="w_jobs_selected").set_value(other).run()
    assert app.session_state["selected_job_id"] == other
    assert app.radio(key="w_jobs_selected").value == other


def test_changing_the_view_keeps_the_selection(app):
    _search(app)
    app.radio(key="w_jobs_selected").set_value("greenhouse_2").run()
    app.segmented_control(key="w_jobs_view").set_value("Newest").run()
    assert not app.exception, app.exception
    assert app.radio(key="w_jobs_selected").value == "greenhouse_2"


def test_prior_results_stay_visible_while_editing_the_search(app):
    _search(app)
    _click(app, "Edit search")
    assert any(t.key == "job_title" for t in app.text_input)
    assert "Product Manager, Growth" in app.radio(key="w_jobs_selected").options


def test_saved_view_works_without_a_search(app):
    _search(app)
    _click(app, "Save")
    app.switch_page("pages/2_Job_Search.py")
    del app.session_state["last_search_run"]
    app.session_state["jobs_view_choice"] = "Saved"
    app.run()
    assert not app.exception, app.exception
    assert app.radio(key="w_jobs_selected").options


def test_partial_source_failure_still_shows_the_results(tmp_path, monkeypatch, app):
    with patch.object(LeverScraper, "_fetch_board", _failing):
        _click(app, "Find matching jobs")
    assert "Product Manager, Growth" in app.radio(key="w_jobs_selected").options
    assert "Lever didn" in _text(app)


def test_no_results_offers_to_edit_the_search(app):
    with patch.object(GreenhouseScraper, "_fetch_board", lambda self, token: {"jobs": []}):
        _click(app, "Find matching jobs")
    assert "No open postings matched this search" in _text(app)
    assert any(b.label == "Edit search" for b in app.button)


def test_unknown_salary_and_sponsorship_are_named(app):
    _search(app)
    text = _text(app)
    assert "Salary was not stated" in text and "Sponsorship was not stated" in text


def test_prepare_carries_the_job_and_switching_jobs_clears_old_tailoring(app):
    _search(app)
    app.session_state["artifact_run_state"] = {"stale": True}
    app.session_state["tailoring_active_job_id"] = "greenhouse_999"
    app.radio(key="w_jobs_selected").set_value("greenhouse_2").run()
    _click(app, "Prepare this application")
    pending = app.session_state[PENDING_TAILOR_JOB_KEY]
    assert pending["job_id"] == "greenhouse_2" and "Kubernetes" in pending["description"]
    app.switch_page("pages/5_Tailor.py")
    app.run()
    assert not app.exception, app.exception
    assert "artifact_run_state" not in app.session_state
    assert "Kubernetes" in app.session_state["job_description_text"]


def test_a_new_session_restores_the_chosen_job_in_tailor(app, tmp_path):
    _search(app)
    _click(app, "Prepare this application")
    fresh = AppTest.from_file(APP, default_timeout=60)
    fresh.switch_page("pages/5_Tailor.py")
    fresh.run()
    assert not fresh.exception, fresh.exception
    assert fresh.session_state[PENDING_TAILOR_JOB_KEY]["job_id"] == app.session_state["selected_job_id"]
    assert fresh.session_state["job_description_text"].strip()
    assert "Choose a job first" not in _text(fresh)
