from datetime import date

from resume_tailorer.ui.home_state import (
    APPLY_PAGE,
    JOBS_PAGE,
    PROFILE_PAGE,
    TAILOR_PAGE,
    TRACKER_PAGE,
    HomeInputs,
    Item,
    build_home_view,
    due_items,
)
from resume_tailorer.ui.profile_readiness import ProfileReadiness


def readiness(has_resume=True, confirmed=True, attention=()):
    return ProfileReadiness(has_resume, (), 4 if has_resume else 0, 4, attention, confirmed)


def inputs(**overrides):
    base = dict(readiness=readiness(), goals_set=True, role_chosen=True, application_prepared=True,
                searched_this_week=True)
    base.update(overrides)
    return HomeInputs(**base)


def test_brand_new_user_imports_a_resume_on_home():
    view = build_home_view(inputs(readiness=readiness(False, False), goals_set=False, role_chosen=False,
                                  application_prepared=False))
    assert view.mode == "first_time" and view.completed == 0
    assert view.next_action.inline == "upload"
    assert [s.state for s in view.milestones][:2] == ["current", "pending"]


def test_after_import_the_user_confirms_facts_and_hears_how_many_need_attention():
    view = build_home_view(inputs(readiness=readiness(True, False, ("Add your email",)), goals_set=False,
                                  role_chosen=False, application_prepared=False))
    assert view.next_action.page == PROFILE_PAGE
    assert "1 thing needs" in view.next_action.why


def test_goals_are_answered_on_home_then_jobs_then_tailor():
    view = build_home_view(inputs(goals_set=False, role_chosen=False, application_prepared=False))
    assert view.next_action.inline == "goals"
    view = build_home_view(inputs(role_chosen=False, application_prepared=False))
    assert view.next_action.page == JOBS_PAGE
    view = build_home_view(inputs(application_prepared=False, active_job=Item("Analyst", "Northwind")))
    assert view.next_action.page == TAILOR_PAGE and "Analyst" in view.next_action.title
    view = build_home_view(inputs(application_prepared=False, active_job=Item("Analyst"), handoff_ready=True))
    assert view.next_action.page == APPLY_PAGE


def test_milestones_are_never_completed_by_navigation_alone():
    view = build_home_view(inputs(readiness=readiness(False, True)))
    assert view.completed == 3  # confirmed facts don't count without a resume
    assert view.mode == "first_time"


def test_returning_priority_failed_resume_first():
    view = build_home_view(inputs(active_job=Item("Analyst"), artifact_status="FAIL",
                                  followups_due=(Item("x"),)))
    assert view.mode == "returning"
    assert view.next_action.title.startswith("Fix the resume")


def test_returning_priority_order():
    due = (Item("Analyst at Northwind", "Email recruiter · due today"),)
    assert build_home_view(inputs(followups_due=due)).next_action.page == TRACKER_PAGE
    draft = inputs(active_job=Item("Analyst"), artifact_status="PASS", artifact_reviewed=False)
    assert build_home_view(draft).next_action.page == TAILOR_PAGE
    assert build_home_view(draft).drafts
    ready = inputs(ready_to_finish=(Item("Analyst at Northwind"),))
    assert build_home_view(ready).next_action.page == APPLY_PAGE
    saved = inputs(saved_jobs=(Item("A"), Item("B")))
    assert build_home_view(saved).next_action.title == "Review 2 saved jobs"
    assert build_home_view(inputs(searched_this_week=False)).next_action.title == "Search for new roles"
    assert build_home_view(inputs()).next_action.title == "You're caught up"


def test_due_items_include_today_and_overdue_but_not_closed_or_future():
    rows = [
        {"title": "A", "company": "X", "next_action": "Email", "due": "2026-10-01", "closed": False},
        {"title": "B", "company": "Y", "next_action": "Call", "due": "2026-10-04", "closed": False},
        {"title": "C", "company": "Z", "next_action": "Wait", "due": "2026-10-09", "closed": False},
        {"title": "D", "company": "W", "next_action": "Old", "due": "2026-09-01", "closed": True},
        {"title": "E", "company": "V", "next_action": "", "due": "", "closed": False},
    ]
    items = due_items(rows, date(2026, 10, 4))
    assert [i.title for i in items] == ["A at X", "B at Y"]
    assert "overdue" in items[0].detail and "due today" in items[1].detail
