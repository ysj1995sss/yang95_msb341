from datetime import date, datetime

from resume_tailorer.applications.models import (
    ApplicationMode,
    ApplicationStatus as S,
    ApplicationSubmission,
    ApplicationTracker,
)
from resume_tailorer.applications.weekly import build_weekly_summary, week_bounds
from resume_tailorer.ui.tracker_views import applied_date, build_row, in_view, sort_rows, view_counts

TODAY = date(2026, 10, 7)


def sub(**kw):
    base = dict(job_posting_id="greenhouse_1", mode=ApplicationMode.MANUAL, resume_used="/a/tailored_v2.pdf",
                candidate_fit_score=72.0, resume_match_score=81.0, form_fields_submitted={}, custom_answers={},
                ats_platform="greenhouse", form_url="https://example.com/1",
                job_snapshot={"company": "Northwind", "title": "Analyst", "url": "https://example.com/1"},
                candidate_fit_snapshot={"overall_fit": 72.0})
    base.update(kw)
    return ApplicationSubmission(**base)


def row(status, updated=datetime(2026, 10, 6), due=None, history=None):
    tracker = ApplicationTracker("app1", "greenhouse_1", status, status_updated=updated)
    return build_row(tracker, sub(next_action_due=due, next_action="Email" if due else ""), history or [tracker])


def test_row_reads_the_immutable_snapshot():
    r = row(S.APPLIED)
    table = r.as_table()
    assert (table["Company"], table["Role"], table["Candidate fit"]) == ("Northwind", "Analyst", "72%")
    assert table["Resume"] == "tailored_v2.pdf" and table["Source"] == "Greenhouse" and table["Mode"] == "Manual"


def test_applied_date_comes_from_when_the_user_marked_it():
    history = [ApplicationTracker("a", "j", S.READY_TO_APPLY, status_updated=datetime(2026, 10, 1)),
               ApplicationTracker("a", "j", S.APPLIED, status_updated=datetime(2026, 10, 3))]
    assert applied_date(history) == date(2026, 10, 3)
    assert applied_date(history[:1]) is None


def test_saved_views():
    assert in_view(row(S.READY_TO_APPLY), "Ready to apply", TODAY)
    assert in_view(row(S.INTERVIEW), "Interviewing", TODAY)
    assert in_view(row(S.ASSESSMENT), "Interviewing", TODAY)
    assert in_view(row(S.REJECTED), "Closed", TODAY)
    assert in_view(row(S.APPLIED, due="2026-10-07"), "Needs action", TODAY)
    assert not in_view(row(S.REJECTED, due="2026-10-01"), "Needs action", TODAY)
    assert in_view(row(S.PREPARING), "Needs action", TODAY)


def test_waiting_means_applied_with_no_update_for_two_weeks():
    assert in_view(row(S.APPLIED, updated=datetime(2026, 9, 20)), "Waiting", TODAY)
    assert not in_view(row(S.APPLIED, updated=datetime(2026, 10, 1)), "Waiting", TODAY)


def test_counts_and_sorting_put_due_items_first():
    rows = [row(S.APPLIED), row(S.APPLIED, due="2026-10-09"), row(S.APPLIED, due="2026-10-05")]
    assert [r.due for r in sort_rows(rows)][:2] == [date(2026, 10, 5), date(2026, 10, 9)]
    assert view_counts(rows, TODAY)["All"] == 3


def test_weekly_summary_counts_only_this_weeks_applications():
    assert week_bounds(TODAY) == (date(2026, 10, 5), date(2026, 10, 11))
    entries = [(S.APPLIED, date(2026, 10, 6)), (S.INTERVIEW, date(2026, 9, 20)), (S.APPLIED, date(2026, 9, 30)),
               (S.READY_TO_APPLY, None), (S.INTERESTED, None)]
    w = build_weekly_summary(entries, TODAY)
    assert (w.applied, w.interviews, w.saved) == (1, 1, 1)
