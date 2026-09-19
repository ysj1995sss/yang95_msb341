from resume_tailorer.applications.ui_helpers import format_application_for_display
from resume_tailorer.applications.models import ApplicationTracker, ApplicationStatus
from datetime import datetime


def test_format_application_for_display_basic_fields():
    tracker = ApplicationTracker(
        application_id="app_abc123",
        job_posting_id="greenhouse_1",
        status=ApplicationStatus.INTERVIEW,
        notes="Onsite next week",
        status_updated=datetime(2026, 9, 18, 14, 30),
    )
    result = format_application_for_display(tracker)
    assert result["Status"] == "Interview"
    assert result["Notes"] == "Onsite next week"
    assert "2026-09-18" in result["Last Updated"]


def test_format_application_for_display_no_notes():
    tracker = ApplicationTracker(
        application_id="app_abc123",
        job_posting_id="greenhouse_1",
        status=ApplicationStatus.APPLIED,
    )
    result = format_application_for_display(tracker)
    assert result["Notes"] == "—"


def test_format_application_for_display_status_title_case():
    tracker = ApplicationTracker(
        application_id="app_abc123",
        job_posting_id="greenhouse_1",
        status=ApplicationStatus.RECRUITER_SCREEN,
    )
    result = format_application_for_display(tracker)
    assert result["Status"] == "Recruiter Screen"
