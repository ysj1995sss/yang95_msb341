import pytest
from datetime import datetime
from resume_tailorer.applications.models import (
    ApplicationMode,
    ApplicationStatus,
    ATSCapability,
    FormField,
    ApplicationSubmission,
    ApplicationTracker,
    StatusSource,
    SubmissionAttempt,
    SubmissionResult,
)


def test_application_mode_enum_values():
    assert ApplicationMode.MANUAL.value == "manual"
    assert ApplicationMode.ASSIST.value == "assist"
    assert ApplicationMode.AUTO.value == "auto"


def test_application_status_enum_values():
    assert ApplicationStatus.DISCOVERED.value == "discovered"
    assert ApplicationStatus.APPLIED.value == "applied"
    assert ApplicationStatus.RECRUITER_SCREEN.value == "recruiter_screen"
    assert ApplicationStatus.FINAL_INTERVIEW.value == "final_interview"
    assert ApplicationStatus.WITHDRAWN.value == "withdrawn"


def test_form_field_defaults():
    field = FormField(field_name="email", field_type="email")
    assert field.required is False
    assert field.value == ""
    assert field.prefilled is False


def test_form_field_with_value():
    field = FormField(field_name="first_name", field_type="text", required=True, value="Jane", prefilled=True)
    assert field.value == "Jane"
    assert field.prefilled is True


def test_application_submission_defaults():
    sub = ApplicationSubmission(
        job_posting_id="greenhouse_123",
        mode=ApplicationMode.MANUAL,
        resume_used="/tmp/resume.pdf",
        candidate_fit_score=85.0,
        resume_match_score=90.0,
        form_fields_submitted={"email": "jane@example.com"},
        custom_answers={},
        ats_platform="greenhouse",
        form_url="https://boards.greenhouse.io/company/jobs/123",
    )
    assert sub.confirmation_number == ""
    assert sub.application_id == ""
    assert isinstance(sub.submission_timestamp, datetime)


def test_application_tracker_defaults():
    tracker = ApplicationTracker(
        application_id="app_abc123",
        job_posting_id="greenhouse_123",
        status=ApplicationStatus.APPLIED,
    )
    assert tracker.notes == ""
    assert isinstance(tracker.status_updated, datetime)
    assert tracker.source is StatusSource.USER
    assert tracker.confidence is None
    assert tracker.evidence == ""


def test_application_status_includes_assessment_and_unknown():
    assert ApplicationStatus.ASSESSMENT.value == "assessment"
    assert ApplicationStatus.UNKNOWN.value == "unknown"


def test_application_submission_snapshot_fields_default_empty():
    sub = ApplicationSubmission(
        job_posting_id="greenhouse_123",
        mode=ApplicationMode.MANUAL,
        resume_used="/tmp/resume.pdf",
        candidate_fit_score=85.0,
        resume_match_score=90.0,
        form_fields_submitted={},
        custom_answers={},
        ats_platform="greenhouse",
        form_url="https://boards.greenhouse.io/company/jobs/123",
    )
    assert sub.job_snapshot == {}
    assert sub.candidate_fit_snapshot == {}
    assert sub.career_profile_version == ""
    assert sub.next_action == ""
    assert sub.next_action_due is None


class TestATSCapability:
    def test_defaults_are_manual_only(self):
        cap = ATSCapability(platform="greenhouse")
        assert cap.manual_supported is True
        assert cap.assist_supported is False
        assert cap.auto_supported is False
        assert cap.final_submission is False
        assert cap.resume_upload is False
        assert cap.status_fetch is False

    def test_is_frozen(self):
        cap = ATSCapability(platform="greenhouse")
        with pytest.raises(Exception):
            cap.final_submission = True


class TestSubmissionAttempt:
    def test_defaults(self):
        attempt = SubmissionAttempt(
            application_id="app_abc123",
            mode=ApplicationMode.ASSIST,
            provider="greenhouse",
            result=SubmissionResult.STARTED,
        )
        assert attempt.completed_at is None
        assert attempt.error_code == ""
        assert attempt.attempt_id == ""
        assert isinstance(attempt.started_at, datetime)
