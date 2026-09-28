import sqlite3
import pytest
import tempfile
import os
from resume_tailorer.applications.database import ApplicationDatabase
from resume_tailorer.applications.models import (
    ApplicationMode,
    ApplicationStatus,
    ApplicationSubmission,
    StatusSource,
    SubmissionAttempt,
    SubmissionResult,
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


def test_snapshot_and_next_action_fields_round_trip(temp_db):
    sub = _make_submission()
    sub.job_snapshot = {"company": "Acme", "title": "Engineer"}
    sub.candidate_fit_snapshot = {"overall_fit": 82.0}
    sub.career_profile_version = "hash-abc"
    sub.answers_version = "v1"
    app_id = temp_db.save_submission(sub)

    persisted = temp_db.get_submission(app_id)
    assert persisted.job_snapshot == {"company": "Acme", "title": "Engineer"}
    assert persisted.candidate_fit_snapshot == {"overall_fit": 82.0}
    assert persisted.career_profile_version == "hash-abc"
    assert persisted.answers_version == "v1"
    assert persisted.next_action == ""
    assert persisted.next_action_due is None


def test_update_next_action(temp_db):
    app_id = temp_db.save_submission(_make_submission())
    assert temp_db.update_next_action(app_id, "Prepare for interview", "2026-10-01", "Bring portfolio") is True

    persisted = temp_db.get_submission(app_id)
    assert persisted.next_action == "Prepare for interview"
    assert persisted.next_action_due == "2026-10-01"
    assert persisted.next_action_notes == "Bring portfolio"


def test_update_next_action_unknown_application_returns_false(temp_db):
    assert temp_db.update_next_action("not-a-real-id", "Follow up") is False


def test_additive_migration_backfills_columns_on_a_pre_existing_database(tmp_path):
    """A local applications.db created before these columns existed must
    keep working -- never break on first query after an upgrade."""
    path = str(tmp_path / "legacy.db")
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE applications (
            application_id TEXT PRIMARY KEY, job_posting_id TEXT NOT NULL, mode TEXT NOT NULL,
            resume_used TEXT, candidate_fit_score REAL, resume_match_score REAL,
            form_fields_submitted TEXT, custom_answers TEXT, ats_platform TEXT, form_url TEXT,
            submission_timestamp TIMESTAMP, confirmation_number TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE application_status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, application_id TEXT NOT NULL,
            job_posting_id TEXT NOT NULL, status TEXT NOT NULL, notes TEXT,
            status_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

    db = ApplicationDatabase(path)
    db.create_tables()  # must not raise, and must backfill the new columns
    app_id = db.save_submission(_make_submission())
    assert db.get_submission(app_id).job_snapshot == {}
    db.update_status(app_id, ApplicationStatus.APPLIED)
    history = db.get_status_history(app_id)
    assert history[0].source is StatusSource.USER
    db.close()


class TestSubmissionAttempts:
    def test_record_and_retrieve_an_attempt(self, temp_db):
        app_id = temp_db.save_submission(_make_submission())
        attempt = SubmissionAttempt(
            application_id=app_id, mode=ApplicationMode.ASSIST, provider="greenhouse",
            result=SubmissionResult.STARTED,
        )
        attempt_id = temp_db.record_attempt(attempt)
        assert attempt_id

        attempts = temp_db.get_attempts_by_application(app_id)
        assert len(attempts) == 1
        assert attempts[0].result is SubmissionResult.STARTED
        assert attempts[0].completed_at is None

    def test_complete_attempt_updates_result_and_completion_time(self, temp_db):
        app_id = temp_db.save_submission(_make_submission())
        attempt_id = temp_db.record_attempt(SubmissionAttempt(
            application_id=app_id, mode=ApplicationMode.ASSIST, provider="greenhouse",
            result=SubmissionResult.STARTED,
        ))
        assert temp_db.complete_attempt(
            attempt_id, SubmissionResult.FAILED, error_code="NETWORK_ERROR", error_message="timed out",
        ) is True

        attempts = temp_db.get_attempts_by_application(app_id)
        assert attempts[0].result is SubmissionResult.FAILED
        assert attempts[0].error_code == "NETWORK_ERROR"
        assert attempts[0].completed_at is not None

    def test_complete_unknown_attempt_returns_false(self, temp_db):
        assert temp_db.complete_attempt("not-a-real-attempt", SubmissionResult.FAILED) is False

    def test_multiple_attempts_recorded_in_order(self, temp_db):
        app_id = temp_db.save_submission(_make_submission())
        first = temp_db.record_attempt(SubmissionAttempt(
            application_id=app_id, mode=ApplicationMode.ASSIST, provider="greenhouse",
            result=SubmissionResult.FAILED,
        ))
        second = temp_db.record_attempt(SubmissionAttempt(
            application_id=app_id, mode=ApplicationMode.ASSIST, provider="greenhouse",
            result=SubmissionResult.CONFIRMED,
        ))
        attempts = temp_db.get_attempts_by_application(app_id)
        assert [a.attempt_id for a in attempts] == [first, second]


class TestIdempotency:
    def test_no_confirmed_submission_by_default(self, temp_db):
        temp_db.save_submission(_make_submission(job_posting_id="greenhouse_1"))
        assert temp_db.has_confirmed_submission("greenhouse_1") is False

    def test_confirmed_attempt_trips_the_idempotency_check(self, temp_db):
        app_id = temp_db.save_submission(_make_submission(job_posting_id="greenhouse_1"))
        temp_db.record_attempt(SubmissionAttempt(
            application_id=app_id, mode=ApplicationMode.ASSIST, provider="greenhouse",
            result=SubmissionResult.CONFIRMED,
        ))
        assert temp_db.has_confirmed_submission("greenhouse_1") is True

    def test_manually_confirmed_attempt_also_trips_the_check(self, temp_db):
        app_id = temp_db.save_submission(_make_submission(job_posting_id="greenhouse_1"))
        temp_db.record_attempt(SubmissionAttempt(
            application_id=app_id, mode=ApplicationMode.MANUAL, provider="greenhouse",
            result=SubmissionResult.MANUALLY_CONFIRMED,
        ))
        assert temp_db.has_confirmed_submission("greenhouse_1") is True

    def test_failed_attempt_does_not_trip_the_check(self, temp_db):
        app_id = temp_db.save_submission(_make_submission(job_posting_id="greenhouse_1"))
        temp_db.record_attempt(SubmissionAttempt(
            application_id=app_id, mode=ApplicationMode.ASSIST, provider="greenhouse",
            result=SubmissionResult.FAILED,
        ))
        assert temp_db.has_confirmed_submission("greenhouse_1") is False

    def test_a_different_job_is_unaffected(self, temp_db):
        app_id = temp_db.save_submission(_make_submission(job_posting_id="greenhouse_1"))
        temp_db.record_attempt(SubmissionAttempt(
            application_id=app_id, mode=ApplicationMode.ASSIST, provider="greenhouse",
            result=SubmissionResult.CONFIRMED,
        ))
        assert temp_db.has_confirmed_submission("greenhouse_2") is False


class TestStatusProvenance:
    def test_status_defaults_to_user_source_with_no_confidence(self, temp_db):
        app_id = temp_db.save_submission(_make_submission())
        temp_db.update_status(app_id, ApplicationStatus.APPLIED)
        history = temp_db.get_status_history(app_id)
        assert history[0].source is StatusSource.USER
        assert history[0].confidence is None
        assert history[0].evidence == ""

    def test_status_with_automated_source_and_confidence(self, temp_db):
        app_id = temp_db.save_submission(_make_submission())
        temp_db.update_status(
            app_id, ApplicationStatus.INTERVIEW,
            source=StatusSource.EMAIL_INTEGRATION, confidence="high",
            evidence="Subject: Interview invitation from Acme",
        )
        history = temp_db.get_status_history(app_id)
        assert history[0].source is StatusSource.EMAIL_INTEGRATION
        assert history[0].confidence == "high"
        assert "Interview invitation" in history[0].evidence

    def test_user_correction_always_allowed_after_automated_entry(self, temp_db):
        """A user must be able to override a low-confidence automated
        status -- no automation entry can block a user's own correction."""
        app_id = temp_db.save_submission(_make_submission())
        temp_db.update_status(
            app_id, ApplicationStatus.REJECTED,
            source=StatusSource.EMAIL_INTEGRATION, confidence="low",
        )
        assert temp_db.update_status(app_id, ApplicationStatus.INTERVIEW, source=StatusSource.USER) is True
        assert temp_db.get_current_status(app_id) == ApplicationStatus.INTERVIEW
