import pytest
from datetime import datetime
from resume_tailorer.applications.models import (
    ApplicationMode,
    ApplicationStatus,
    FormField,
    ApplicationSubmission,
    ApplicationTracker,
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
