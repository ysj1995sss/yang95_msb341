import pytest
import tempfile
import os

from resume_tailorer.applications.status_tracker import StatusTracker
from resume_tailorer.applications.database import ApplicationDatabase
from resume_tailorer.applications.models import ApplicationMode, ApplicationStatus, ApplicationSubmission


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = ApplicationDatabase(path)
    db.create_tables()
    yield db
    db.close()
    os.unlink(path)


def _seed_application(db, job_posting_id="greenhouse_1"):
    sub = ApplicationSubmission(
        job_posting_id=job_posting_id,
        mode=ApplicationMode.MANUAL,
        resume_used="/tmp/r.pdf",
        candidate_fit_score=80.0,
        resume_match_score=85.0,
        form_fields_submitted={},
        custom_answers={},
        ats_platform="greenhouse",
        form_url="https://boards.greenhouse.io/co/jobs/1",
    )
    return db.save_submission(sub)


def test_status_tracker_update_status(temp_db):
    app_id = _seed_application(temp_db)
    tracker = StatusTracker(temp_db)

    result = tracker.update_status(app_id, ApplicationStatus.INTERVIEW, notes="Onsite scheduled")
    assert result is True

    history = tracker.get_status_history(app_id)
    assert history[-1].status == ApplicationStatus.INTERVIEW
    assert history[-1].notes == "Onsite scheduled"


def test_status_tracker_update_status_unknown_application(temp_db):
    tracker = StatusTracker(temp_db)
    result = tracker.update_status("app_does_not_exist", ApplicationStatus.INTERVIEW)
    assert result is False


def test_status_tracker_get_status_history(temp_db):
    # NOTE: save_submission() no longer auto-creates an initial APPLIED status row
    # (that auto-insert was removed in Task 4's fix — it falsely marked dry-run
    # previews as "Applied"). This test now explicitly records APPLIED before
    # advancing to RECRUITER_SCREEN, mirroring the seed-time state the original
    # test assumed came for free.
    app_id = _seed_application(temp_db)
    tracker = StatusTracker(temp_db)
    tracker.update_status(app_id, ApplicationStatus.APPLIED, notes="Submitted")
    tracker.update_status(app_id, ApplicationStatus.RECRUITER_SCREEN)

    history = tracker.get_status_history(app_id)
    assert len(history) == 2
    assert history[0].status == ApplicationStatus.APPLIED


def test_status_tracker_get_applications_by_status(temp_db):
    # NOTE: app_id1 needs an explicit APPLIED status now — previously
    # save_submission() auto-inserted it, so it "just showed up" as Applied.
    app_id1 = _seed_application(temp_db, "greenhouse_1")
    app_id2 = _seed_application(temp_db, "greenhouse_2")
    tracker = StatusTracker(temp_db)
    tracker.update_status(app_id1, ApplicationStatus.APPLIED)
    tracker.update_status(app_id2, ApplicationStatus.OFFER)

    offers = tracker.get_applications_by_status(ApplicationStatus.OFFER)
    applied = tracker.get_applications_by_status(ApplicationStatus.APPLIED)

    assert len(offers) == 1
    assert offers[0].application_id == app_id2
    assert len(applied) == 1
    assert applied[0].application_id == app_id1


def test_status_tracker_get_all_applications(temp_db):
    # NOTE: with the auto-insert removed, a freshly-saved submission has no
    # status history row at all, so it would not appear in get_all_applications()
    # (which is driven by the status_history table) until a status is recorded.
    app_id1 = _seed_application(temp_db, "greenhouse_1")
    app_id2 = _seed_application(temp_db, "greenhouse_2")
    tracker = StatusTracker(temp_db)
    tracker.update_status(app_id1, ApplicationStatus.APPLIED)
    tracker.update_status(app_id2, ApplicationStatus.APPLIED)

    all_apps = tracker.get_all_applications()
    assert len(all_apps) == 2
