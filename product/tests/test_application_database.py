import pytest
import tempfile
import os
from resume_tailorer.applications.database import ApplicationDatabase
from resume_tailorer.applications.models import (
    ApplicationMode,
    ApplicationStatus,
    ApplicationSubmission,
)


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = ApplicationDatabase(path)
    db.create_tables()
    yield db
    db.close()
    os.unlink(path)


def _make_submission(job_posting_id="greenhouse_1"):
    return ApplicationSubmission(
        job_posting_id=job_posting_id,
        mode=ApplicationMode.MANUAL,
        resume_used="/tmp/resume.pdf",
        candidate_fit_score=85.0,
        resume_match_score=90.0,
        form_fields_submitted={"email": "jane@example.com", "first_name": "Jane"},
        custom_answers={"why_us": "Great mission fit."},
        ats_platform="greenhouse",
        form_url="https://boards.greenhouse.io/company/jobs/1",
    )


def test_database_initialization(temp_db):
    assert temp_db is not None


def test_save_submission_returns_application_id(temp_db):
    sub = _make_submission()
    app_id = temp_db.save_submission(sub)
    assert app_id
    assert app_id.startswith("app_")


def test_save_and_retrieve_submission(temp_db):
    sub = _make_submission()
    app_id = temp_db.save_submission(sub)

    retrieved = temp_db.get_submission(app_id)
    assert retrieved is not None
    assert retrieved.job_posting_id == "greenhouse_1"
    assert retrieved.mode == ApplicationMode.MANUAL
    assert retrieved.form_fields_submitted == {"email": "jane@example.com", "first_name": "Jane"}
    assert retrieved.custom_answers == {"why_us": "Great mission fit."}
    assert retrieved.candidate_fit_score == 85.0


def test_get_submission_returns_none_for_missing_id(temp_db):
    assert temp_db.get_submission("app_does_not_exist") is None


def test_get_submissions_by_job(temp_db):
    sub1 = _make_submission(job_posting_id="greenhouse_1")
    sub2 = _make_submission(job_posting_id="greenhouse_1")
    sub3 = _make_submission(job_posting_id="greenhouse_2")
    temp_db.save_submission(sub1)
    temp_db.save_submission(sub2)
    temp_db.save_submission(sub3)

    results = temp_db.get_submissions_by_job("greenhouse_1")
    assert len(results) == 2


def test_save_submission_does_not_create_status_until_explicitly_set(temp_db):
    """Saving a submission (which may be a dry-run preview) must NOT claim APPLIED
    until something explicitly records that status — a preview is not a submission."""
    sub = _make_submission()
    app_id = temp_db.save_submission(sub)

    status = temp_db.get_current_status(app_id)
    assert status is None


def test_update_confirmation_number(temp_db):
    sub = _make_submission()
    app_id = temp_db.save_submission(sub)

    success = temp_db.update_confirmation_number(app_id, "CONF-12345")
    assert success is True

    retrieved = temp_db.get_submission(app_id)
    assert retrieved.confirmation_number == "CONF-12345"


def test_update_confirmation_number_returns_false_for_unknown_id(temp_db):
    success = temp_db.update_confirmation_number("app_does_not_exist", "CONF-999")
    assert success is False


def test_update_status(temp_db):
    sub = _make_submission()
    app_id = temp_db.save_submission(sub)

    success = temp_db.update_status(app_id, ApplicationStatus.RECRUITER_SCREEN, notes="Phone screen scheduled")
    assert success is True

    status = temp_db.get_current_status(app_id)
    assert status == ApplicationStatus.RECRUITER_SCREEN


def test_get_status_history_ordered(temp_db):
    sub = _make_submission()
    app_id = temp_db.save_submission(sub)
    temp_db.update_status(app_id, ApplicationStatus.APPLIED, notes="Submitted")
    temp_db.update_status(app_id, ApplicationStatus.RECRUITER_SCREEN, notes="Screen done")
    temp_db.update_status(app_id, ApplicationStatus.INTERVIEW, notes="Onsite scheduled")

    history = temp_db.get_status_history(app_id)
    assert len(history) == 3
    assert history[0].status == ApplicationStatus.APPLIED
    assert history[1].status == ApplicationStatus.RECRUITER_SCREEN
    assert history[2].status == ApplicationStatus.INTERVIEW


def test_get_applications_by_status(temp_db):
    sub1 = _make_submission(job_posting_id="greenhouse_1")
    sub2 = _make_submission(job_posting_id="greenhouse_2")
    app_id1 = temp_db.save_submission(sub1)
    app_id2 = temp_db.save_submission(sub2)
    temp_db.update_status(app_id1, ApplicationStatus.APPLIED)
    temp_db.update_status(app_id2, ApplicationStatus.INTERVIEW)

    applied = temp_db.get_applications_by_status(ApplicationStatus.APPLIED)
    interview = temp_db.get_applications_by_status(ApplicationStatus.INTERVIEW)

    assert len(applied) == 1
    assert applied[0].application_id == app_id1
    assert len(interview) == 1
    assert interview[0].application_id == app_id2


def test_get_all_applications_returns_current_status_only(temp_db):
    sub = _make_submission()
    app_id = temp_db.save_submission(sub)
    temp_db.update_status(app_id, ApplicationStatus.RECRUITER_SCREEN)
    temp_db.update_status(app_id, ApplicationStatus.INTERVIEW)

    all_apps = temp_db.get_all_applications()
    assert len(all_apps) == 1
    assert all_apps[0].status == ApplicationStatus.INTERVIEW
