"""Status from a pasted recruiter email (spec 005, first slice). Synthetic emails only."""

from datetime import date

import pytest

from resume_tailorer.applications.email_status import Candidate, read_email, suggest_status
from resume_tailorer.applications.models import ApplicationStatus as S

APPS = [
    Candidate("a1", "Acme Analytics", "Senior Data Analyst", S.APPLIED),
    Candidate("a2", "Globex", "Product Manager", S.INTERVIEW),
    Candidate("a3", "Initech", "Data Analyst", S.APPLIED),
]

REJECTION = """From: Acme Analytics Recruiting <no-reply@greenhouse.io>
Date: Thu, 1 Oct 2026 09:30:00 -0700
Subject: Your application to Acme Analytics

Hi Riley,
Thank you for applying for the Senior Data Analyst role at Acme Analytics. After careful review,
we have decided to move forward with other candidates whose experience more closely matches.
"""

SCREEN = """From: Jamie <jamie@globex.com>
Subject: Product Manager - next steps
Hi Riley, I'd love to set up a 30-minute call to learn more about your background for the Product Manager role.
"""


@pytest.mark.parametrize("text, status", [
    (REJECTION, S.REJECTED),
    (SCREEN, S.RECRUITER_SCREEN),
    ("We are pleased to extend an offer for the role.", S.OFFER),
    ("Please complete the HackerRank assessment within 5 days.", S.ASSESSMENT),
    ("We'd like to schedule an onsite interview, the final round.", S.FINAL_INTERVIEW),
    ("We'd like to schedule an interview with the hiring team.", S.INTERVIEW),
    ("We have received your application and will be in touch.", S.APPLIED),
    ("Unfortunately we need to reschedule our coffee.", None),
])
def test_status_comes_from_explicit_phrases(text, status):
    assert suggest_status(text)[0] == status


def test_a_rejection_is_matched_to_its_application_with_the_date():
    reading = read_email(REJECTION, APPS)
    assert reading.status == S.REJECTED and "move forward with other candidates" in reading.phrase
    assert reading.chosen == "a1"
    assert reading.email_date == date(2026, 10, 1)
    assert reading.subject == "Your application to Acme Analytics"


def test_the_sender_domain_and_role_identify_the_company():
    reading = read_email(SCREEN, APPS)
    assert reading.matches[0].application_id == "a2"
    assert reading.chosen == "a2"


def test_an_ambiguous_email_is_never_chosen_for_the_user():
    text = "Thanks for applying to the Data Analyst role. We received your application."
    reading = read_email(text, APPS)
    assert reading.status == S.APPLIED and reading.chosen is None


def test_an_email_about_no_tracked_application_matches_nothing():
    reading = read_email("Subject: Hello\nWe received your application at Umbrella Corp.", APPS)
    assert reading.matches == () and reading.chosen is None


def test_moving_backwards_is_flagged():
    reading = read_email("We have received your application to Globex.", APPS)
    assert reading.moves_backwards(S.INTERVIEW)
    assert not read_email(SCREEN, APPS).moves_backwards(S.APPLIED)


def test_tracker_applies_a_pasted_email_only_after_confirmation(tmp_path, monkeypatch):
    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    from resume_tailorer.applications.database import ApplicationDatabase
    from resume_tailorer.applications.models import ApplicationMode, ApplicationSubmission, StatusSource
    from resume_tailorer.identity import applications_db_path

    monkeypatch.setenv("JOB_COPILOT_DATA_DIR", str(tmp_path / "data"))
    db = ApplicationDatabase(applications_db_path("local"))
    db.create_tables()
    app_id = db.save_submission(ApplicationSubmission(
        job_posting_id="greenhouse_1", mode=ApplicationMode.MANUAL, resume_used="r.pdf", candidate_fit_score=None,
        resume_match_score=80.0, form_fields_submitted={}, custom_answers={}, ats_platform="Greenhouse",
        form_url="https://example.com", job_snapshot={"company": "Acme Analytics", "title": "Senior Data Analyst"}))
    db.update_status(app_id, S.APPLIED, "", StatusSource.USER)

    at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "resume_tailorer" / "app.py"), default_timeout=60)
    at.switch_page("pages/4_Application_Tracker.py")
    at.run()
    at.text_area(key="tracker_email_text").input(REJECTION)
    at.run()
    assert not at.exception, at.exception
    assert db.get_current_status(app_id) == S.APPLIED  # a suggestion changes nothing
    assert at.selectbox(key="tracker_email_app").value == app_id
    [b for b in at.button if b.key == "tracker_email_confirm"][0].click()
    at.run()
    assert not at.exception, at.exception
    assert db.get_current_status(app_id) == S.REJECTED
    latest = db.get_status_history(app_id)[-1]
    assert latest.source == StatusSource.EMAIL_INTEGRATION and "Oct 01, 2026" in latest.notes
    assert at.text_area(key="tracker_email_text").value == ""
