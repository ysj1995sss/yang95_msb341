"""The full guided journey through the real Streamlit pages (spec 007):
Home -> Career Profile -> goals -> Jobs -> Tailor -> Apply -> Tracker -> Home.

Synthetic data only. Greenhouse is stubbed (no network). Streamlit's test
runner can't upload files or run the model, so the resume import uses the same
import function the upload button calls (with a stub parser), and the
tailoring step is completed through the same validation and handoff functions
Tailor calls after a run.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from resume_tailorer.applications.models import ApplicationStatus
from resume_tailorer.job_search.job_service import PENDING_TAILOR_JOB_KEY
from resume_tailorer.job_search.scrapers import AshbyScraper, GreenhouseScraper, LeverScraper
from resume_tailorer.models import CareerTruthProfile
from resume_tailorer.pdf.generator import PDFGenerator
from resume_tailorer.pdf.validator import PDFValidator
from resume_tailorer.profile_import import import_resume, store_for
from resume_tailorer.session_profile import FACT_VAULT, PROFILE_SOURCE_KEY
from resume_tailorer.tailoring_session import ACTIVE_JOB_KEY, HANDOFF_KEY, publish_artifact_handoff

APP = str(Path(__file__).resolve().parent.parent / "resume_tailorer" / "app.py")

PROFILE = {
    "contact_info": {"name": "Alex Kim", "email": "alex@example.com", "phone": "", "location": ""},
    "education": [{"degree": "BS", "field": "Economics", "institution": "State U", "year": 2017, "gpa": None, "notes": []}],
    "work_experience": [
        {
            "employer": "Acme Analytics",
            "title": "Product Manager",
            "dates": "2019-2024",
            "responsibilities": ["Led the product roadmap for a B2B analytics platform"],
            "accomplishments": ["Launched usage-based pricing adopted by 40 enterprise customers"],
        }
    ],
    "skills": ["Product Management", "SQL", "Roadmapping"],
    "tools": ["Jira"],
    "certifications": [],
    "accomplishments": [],
    "summary": "",
}

BOARD = {
    "jobs": [
        {
            "id": 101,
            "title": "Senior Product Manager, Analytics",
            "absolute_url": "https://job-boards.greenhouse.io/gitlab/jobs/101",
            "location": {"name": "Remote, US"},
            "content": "<p>Own the analytics roadmap. Requirements: product management, SQL, roadmapping, 5+ years.</p>",
            "updated_at": "2026-09-20T12:00:00-00:00",
        }
    ]
}


class StubParser:
    def parse(self, path):
        return CareerTruthProfile.from_dict(PROFILE)


def _fake_board(self, token):
    return BOARD if token == "gitlab" else {"jobs": []}


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("JOB_COPILOT_DATA_DIR", str(tmp_path / "data"))
    with patch.object(GreenhouseScraper, "_fetch_board", _fake_board), \
         patch.object(LeverScraper, "_fetch_board", lambda self, token: []), \
         patch.object(AshbyScraper, "_fetch_board", lambda self, token: {"jobs": []}):
        yield AppTest.from_file(APP, default_timeout=60)


def _go(at, page):
    at.switch_page(page)
    at.run()
    assert not at.exception, at.exception


def _click(at, label):
    matches = [b for b in at.button if b.label == label]
    assert matches, f"No button {label!r}: {[b.label for b in at.button]}"
    matches[0].click()
    at.run()
    assert not at.exception, at.exception


def _markdown(at) -> str:
    return "\n".join(m.value for m in at.markdown)


def test_guided_journey_from_resume_to_tracker(app, tmp_path):
    at = app

    # Home, first visit: one dominant action, the resume import.
    at.run()
    assert not at.exception, at.exception
    assert "Import your resume" in _markdown(at)
    assert any(b.label == "Import resume" for b in at.button)

    # The upload button's import (stub parser): the profile is stored once, in this user's folder.
    import_resume(store_for("local"), "alex_resume.docx", b"synthetic", parser=StubParser())
    assert (tmp_path / "data" / "users" / "local" / "profile" / "career_profile.json").exists()
    at.run()
    assert "Confirm your important facts" in _markdown(at)
    assert at.session_state[PROFILE_SOURCE_KEY] == FACT_VAULT

    # Career Profile: review by exception, then confirm the rest.
    _go(at, "pages/1_Profile_Review.py")
    _click(at, "Confirm the rest")
    assert at.session_state["profile_record"]["facts_confirmed_at"]

    # Home: the goals wizard, one question at a time.
    _go(at, "app.py")
    assert "Set your job goals" in _markdown(at)
    at.text_input(key="wiz_job_title").input("Product Manager")
    at.run()
    for _ in range(6):
        _click(at, "Continue")
    _click(at, "Save goals and continue")
    assert at.session_state["profile_record"]["preferences"]["job_title"] == "Product Manager"
    assert "Choose a real role" in _markdown(at)

    # Jobs: the saved search is summarised (no form, no stepper); one click searches.
    _go(at, "pages/2_Job_Search.py")
    page = _markdown(at)
    assert "Product Manager roles" in page
    assert "Set goals" not in page and "Review a role" not in page
    assert not [t for t in at.text_input if t.key == "job_title"]
    _click(at, "Find matching jobs")
    page = _markdown(at)
    assert "Senior Product Manager, Analytics" in page
    assert "Why this role may fit you" in page
    assert at.radio(key="w_jobs_selected").value == "greenhouse_101"
    _click(at, "Prepare this application")
    pending = at.session_state[PENDING_TAILOR_JOB_KEY]
    assert pending["job_id"] == "greenhouse_101"
    assert "analytics roadmap" in pending["description"]
    assert at.session_state["profile_record"]["active_job_id"] == "greenhouse_101"

    # Tailor: switches to this job and uses the stored resume.
    _go(at, "pages/5_Tailor.py")
    assert at.session_state[ACTIVE_JOB_KEY] == "greenhouse_101"
    assert "analytics roadmap" in at.session_state["job_description_text"]
    assert "alex_resume.docx" in _markdown(at)

    profile = CareerTruthProfile.from_dict(PROFILE)
    pdf_path = PDFGenerator().generate(
        "Alex Kim\nalex@example.com\n\nEXPERIENCE\nProduct Manager\nAcme Analytics | 2019-2024\n"
        "- Led the product roadmap for a B2B analytics platform\n"
        "- Launched usage-based pricing adopted by 40 enterprise customers\n\n"
        "EDUCATION\nBS Economics\nState U | 2017\n",
        profile.name,
    )
    validation = PDFValidator().validate_artifact(pdf_path, profile=profile, expected_page_count=None, accepted_changes=[])
    assert validation.status.value != "FAIL", validation.findings
    with open(pdf_path, "rb") as f:
        publish_artifact_handoff(at.session_state, pdf_bytes=f.read(), validation_status=validation.status.value,
                                 tailored_alignment=0.81, version=1)
    os.remove(pdf_path)

    # Apply: the handoff arrives with no typing; track, then mark as applied.
    _go(at, "pages/3_Applications.py")
    assert at.session_state[HANDOFF_KEY]["job_id"] == "greenhouse_101"
    assert "Not available yet" in _markdown(at)  # Assist and Auto are visibly unavailable
    assert not [b for b in at.button if b.label == "Mark as applied" and not b.disabled]
    _click(at, "Track this application")
    service = at.session_state["job_service"]
    (submission,) = service.applications_db.get_submissions_by_job("greenhouse_101")
    assert service.applications_db.get_current_status(submission.application_id) == ApplicationStatus.READY_TO_APPLY
    assert submission.resume_match_score == pytest.approx(81.0)
    _click(at, "Mark as applied")
    assert service.applications_db.get_current_status(submission.application_id) == ApplicationStatus.APPLIED

    # Tracker: one application, stored in this user's own folder.
    _go(at, "pages/4_Application_Tracker.py")
    table = at.dataframe[0].value.to_string()
    assert "Senior Product Manager, Analytics" in table and "Applied" in table
    assert (tmp_path / "data" / "users" / "local" / "applications.db").exists()
    assert not (tmp_path / "applications.db").exists()

    # Home is now a command center.
    _go(at, "app.py")
    assert "Your next best action" in _markdown(at)
    assert "Welcome back" in _markdown(at)


def test_a_failed_resume_never_reaches_apply(app):
    at = app
    import_resume(store_for("local"), "alex_resume.docx", b"synthetic", parser=StubParser())
    at.session_state[PENDING_TAILOR_JOB_KEY] = {"job_id": "greenhouse_101", "title": "PM", "company": "GitLab",
                                                "url": "https://job-boards.greenhouse.io/gitlab/jobs/101"}
    at.run()
    # Even if a failed resume's handoff were present, Apply must not use it.
    at.session_state[HANDOFF_KEY] = {"job_id": "greenhouse_101", "pdf_path": "missing.pdf", "sha256": "x",
                                     "version": 1, "validation_status": "FAIL", "resume_match_score": 0.5}
    _go(at, "pages/3_Applications.py")
    assert "No usable tailored resume for this job yet" in _markdown(at)
    assert [b for b in at.button if b.label == "Track this application"][0].disabled
