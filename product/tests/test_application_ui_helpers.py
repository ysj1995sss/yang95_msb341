from resume_tailorer.applications.ui_helpers import (
    filter_applications,
    format_application_for_display,
    group_for_status,
    sort_applications,
)
from resume_tailorer.applications.models import (
    ApplicationMode,
    ApplicationStatus,
    ApplicationSubmission,
    ApplicationTracker,
)
from datetime import datetime


def _tracker(status=ApplicationStatus.APPLIED, application_id="app_1", **kwargs):
    return ApplicationTracker(application_id=application_id, job_posting_id="greenhouse_1", status=status, **kwargs)


def _submission(**overrides):
    defaults = dict(
        job_posting_id="greenhouse_1",
        mode=ApplicationMode.ASSIST,
        resume_used="/tmp/acme_resume_v2.pdf",
        candidate_fit_score=85.0,
        resume_match_score=90.0,
        form_fields_submitted={},
        custom_answers={},
        ats_platform="greenhouse",
        form_url="https://boards.greenhouse.io/co/jobs/1",
        job_snapshot={"company": "Acme", "title": "Engineer"},
        candidate_fit_snapshot={"overall_fit": 82.0},
        submission_timestamp=datetime(2026, 9, 20, 10, 0),
        next_action="Prepare for interview",
    )
    defaults.update(overrides)
    return ApplicationSubmission(**defaults)


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


def test_format_application_for_display_with_submission_shows_snapshot_data():
    tracker = _tracker()
    submission = _submission()
    result = format_application_for_display(tracker, submission)
    assert result["Company"] == "Acme"
    assert result["Role"] == "Engineer"
    assert result["Applied Date"] == "2026-09-20"
    assert result["Mode"] == "Assist"
    assert result["Candidate Fit"] == "82%"
    assert result["Resume Version"] == "acme_resume_v2.pdf"
    assert result["Next Action"] == "Prepare for interview"


def test_format_application_for_display_without_submission_shows_placeholders():
    result = format_application_for_display(_tracker())
    assert result["Company"] == "—"
    assert result["Candidate Fit"] == "—"
    assert result["Next Action"] == "—"


class TestGroupForStatus:
    def test_interview_family_groups_together(self):
        assert group_for_status(ApplicationStatus.RECRUITER_SCREEN) == "Interviews"
        assert group_for_status(ApplicationStatus.INTERVIEW) == "Interviews"
        assert group_for_status(ApplicationStatus.FINAL_INTERVIEW) == "Interviews"

    def test_applied_is_submitted(self):
        assert group_for_status(ApplicationStatus.APPLIED) == "Submitted"

    def test_rejected_and_withdrawn_are_distinct(self):
        assert group_for_status(ApplicationStatus.REJECTED) == "Rejected"
        assert group_for_status(ApplicationStatus.WITHDRAWN) == "Withdrawn"


class TestFilterApplications:
    def _rows(self):
        return [
            format_application_for_display(
                _tracker(status=ApplicationStatus.INTERVIEW, application_id="app_1"),
                _submission(job_snapshot={"company": "Acme", "title": "Backend Engineer"}, candidate_fit_snapshot={"overall_fit": 90.0}),
            ),
            format_application_for_display(
                _tracker(status=ApplicationStatus.REJECTED, application_id="app_2"),
                _submission(job_snapshot={"company": "Beacon", "title": "Data Analyst"}, candidate_fit_snapshot={"overall_fit": 60.0}, mode=ApplicationMode.MANUAL),
            ),
        ]

    def test_view_filter(self):
        rows = self._rows()
        assert [r["Company"] for r in filter_applications(rows, view="Interviews")] == ["Acme"]
        assert [r["Company"] for r in filter_applications(rows, view="Rejected")] == ["Beacon"]
        assert len(filter_applications(rows, view="All")) == 2

    def test_company_filter_is_case_insensitive_substring(self):
        rows = self._rows()
        assert len(filter_applications(rows, company="acme")) == 1

    def test_role_filter(self):
        rows = self._rows()
        assert len(filter_applications(rows, role="data")) == 1

    def test_mode_filter(self):
        rows = self._rows()
        assert [r["Company"] for r in filter_applications(rows, mode="Manual")] == ["Beacon"]

    def test_min_fit_filter_excludes_below_threshold(self):
        rows = self._rows()
        assert [r["Company"] for r in filter_applications(rows, min_fit=75.0)] == ["Acme"]

    def test_min_fit_filter_excludes_unknown_fit(self):
        rows = [format_application_for_display(_tracker())]  # no submission -> "—" fit
        assert filter_applications(rows, min_fit=0.0) == []

    def test_filters_combine_with_and(self):
        rows = self._rows()
        assert filter_applications(rows, company="acme", mode="Manual") == []


class TestSortApplications:
    def _rows(self):
        return [
            format_application_for_display(
                _tracker(application_id="app_1"),
                _submission(job_snapshot={"company": "Zeta"}, candidate_fit_snapshot={"overall_fit": 50.0}, submission_timestamp=datetime(2026, 9, 10)),
            ),
            format_application_for_display(
                _tracker(application_id="app_2"),
                _submission(job_snapshot={"company": "Acme"}, candidate_fit_snapshot={"overall_fit": 90.0}, submission_timestamp=datetime(2026, 9, 20)),
            ),
        ]

    def test_sort_by_company_ascending(self):
        rows = sort_applications(self._rows(), "Company")
        assert [r["Company"] for r in rows] == ["Acme", "Zeta"]

    def test_sort_by_candidate_fit_descending(self):
        rows = sort_applications(self._rows(), "Candidate Fit")
        assert [r["Company"] for r in rows] == ["Acme", "Zeta"]

    def test_sort_by_newest_application(self):
        rows = sort_applications(self._rows(), "Newest application")
        assert rows[0]["Company"] == "Acme"

    def test_unknown_sort_key_returns_rows_unchanged(self):
        rows = self._rows()
        assert sort_applications(rows, "Not a real sort key") == rows
