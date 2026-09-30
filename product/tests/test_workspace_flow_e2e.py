"""One user journey through the real Streamlit pages:
Fact Vault -> Job Search -> Tailoring Studio -> Apply Launchpad -> Tracker.

The profile API and the Greenhouse boards are stubbed (no network). Streamlit's
test runner cannot upload files, so the tailoring step is completed through the
same validation and handoff functions Tailoring Studio calls after a run.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from resume_tailorer.job_search.job_service import PENDING_TAILOR_JOB_KEY
from resume_tailorer.job_search.scrapers import AshbyScraper, GreenhouseScraper, LeverScraper
from resume_tailorer.models import CareerTruthProfile
from resume_tailorer.pdf.generator import PDFGenerator
from resume_tailorer.pdf.validator import PDFValidator
from resume_tailorer.session_profile import FACT_VAULT, PROFILE_SOURCE_KEY
from resume_tailorer.tailoring_session import ACTIVE_JOB_KEY, HANDOFF_KEY, publish_artifact_handoff

APP = str(Path(__file__).resolve().parent.parent / "resume_tailorer" / "app.py")

VAULT_PROFILE = {
    "contact_info": {"name": "Alex Kim", "email": "alex@example.com", "phone": "", "location": ""},
    "education": [],
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


def _fake_board(self, token):
    return BOARD if token == "gitlab" else {"jobs": []}


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("JOB_COPILOT_DATA_DIR", str(tmp_path / "data"))
    stubs = {
        "get_profile": lambda session: VAULT_PROFILE,
        "get_verification": lambda session: {},
        "get_resume_meta": lambda session: None,
        "get_resume_versions": lambda session: [],
    }
    with patch.object(GreenhouseScraper, "_fetch_board", _fake_board),          patch.object(LeverScraper, "_fetch_board", lambda self, token: []),          patch.object(AshbyScraper, "_fetch_board", lambda self, token: {"jobs": []}):
        with patch.multiple("resume_tailorer.profile_review.api_client", **stubs):
            at = AppTest.from_file(APP, default_timeout=60)
            at.session_state["profile_review_session"] = {"token": "test"}
            yield at


def _click(at, label):
    [button for button in at.button if button.label == label][0].click()
    at.run()
    assert not at.exception, at.exception


def test_fact_vault_to_tracker(app, tmp_path):
    at = app

    # Fact Vault: verified facts become the one shared profile.
    at.switch_page("pages/1_Profile_Review.py")
    at.run()
    assert not at.exception, at.exception
    assert at.session_state[PROFILE_SOURCE_KEY] == FACT_VAULT
    assert at.session_state["career_profile"].name == "Alex Kim"

    # Job Search: the vault profile drives fit; Tailor hands the job over.
    at.switch_page("pages/2_Job_Search.py")
    at.run()
    at.text_input(key="job_title").input("Product Manager")
    _click(at, "Search roles")
    cards = [e.label for e in at.expander if " · Fit " in e.label]
    assert cards and "Not assessed" not in cards[0], cards
    _click(at, "Tailor resume")
    pending = at.session_state[PENDING_TAILOR_JOB_KEY]
    assert pending["job_id"] == "greenhouse_101"

    # Tailoring Studio: switches to this job and uses the vault facts.
    at.switch_page("app.py")
    at.run()
    assert not at.exception, at.exception
    assert at.session_state[ACTIVE_JOB_KEY] == "greenhouse_101"
    assert "analytics roadmap" in at.session_state["job_description_text"]

    profile = CareerTruthProfile.from_dict(VAULT_PROFILE)
    pdf_path = PDFGenerator().generate(
        "Alex Kim\nalex@example.com\n\nEXPERIENCE\nProduct Manager\nAcme Analytics | 2019-2024\n"
        "- Led the product roadmap for a B2B analytics platform\n"
        "- Launched usage-based pricing adopted by 40 enterprise customers\n",
        profile.name,
    )
    validation = PDFValidator().validate_artifact(
        pdf_path, profile=profile, expected_page_count=None, accepted_changes=[]
    )
    assert validation.status.value != "FAIL", validation.findings
    with open(pdf_path, "rb") as f:
        publish_artifact_handoff(
            at.session_state, pdf_bytes=f.read(), validation_status=validation.status.value,
            tailored_alignment=0.81, version=1,
        )
    os.remove(pdf_path)

    # Apply Launchpad: the validated resume and score arrive; preview then stage once.
    at.switch_page("pages/3_Applications.py")
    at.run()
    assert not at.exception, at.exception
    assert at.text_input(key="apply_job_id").value == "greenhouse_101"
    assert at.text_input(key="apply_resume_pdf_path").value == at.session_state[HANDOFF_KEY]["pdf_path"]
    assert at.number_input(key="apply_resume_match_score").value == pytest.approx(81.0)

    _click(at, "Preview (dry run — never submits)")
    at.checkbox[0].check()
    at.run()
    _click(at, "Stage in tracker")
    assert any("Ready to apply" in s.value for s in at.success), [s.value for s in at.success]

    # Application Tracker: exactly one staged application for this job.
    at.switch_page("pages/4_Application_Tracker.py")
    at.run()
    assert not at.exception, at.exception
    service = at.session_state["job_service"]
    (submission,) = service.applications_db.get_submissions_by_job("greenhouse_101")
    assert submission.resume_match_score == pytest.approx(81.0)
    # Stored in this user's own data folder, not in shared files in the working directory.
    assert (tmp_path / "data" / "users" / "local" / "applications.db").exists()
    assert not (tmp_path / "applications.db").exists()
    table = at.dataframe[0].value.to_string()
    assert "Senior Product Manager, Analytics" in table
    assert "Ready" in table
