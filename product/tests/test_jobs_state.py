from datetime import datetime
from types import SimpleNamespace

from resume_tailorer.ui.jobs_state import (
    BEST,
    NEWEST,
    SAVED_VIEW,
    JobsInputs,
    JobsState,
    goals_summary_line,
    order_jobs,
    resolve,
    resolve_selection,
    searched_at_text,
    source_note,
)

OK3 = (("greenhouse", "ok"), ("lever", "ok"), ("ashby", "ok"))


def inputs(**kw):
    base = dict(has_goals=False, searched=False, search_requested=False, result_ids=(), selected_id=None)
    base.update(kw)
    return JobsInputs(**base)


def test_no_goals_shows_the_setup_card_and_nothing_else():
    view = resolve(inputs())
    assert view.state is JobsState.NO_GOALS and view.show_setup and not view.show_workspace


def test_saved_goals_mean_ready_to_search_with_no_widget_state_at_all():
    view = resolve(inputs(has_goals=True))
    assert view.state is JobsState.READY_TO_SEARCH and not view.show_setup and not view.show_workspace


def test_a_finished_search_never_looks_like_goals_are_missing():
    for has_goals in (True, False):
        view = resolve(inputs(has_goals=has_goals, searched=True, result_ids=("a", "b"), provider_statuses=OK3))
        assert view.state is JobsState.DETAIL_SELECTED
        assert view.selected_id == "a"


def test_prior_results_stay_visible_while_a_new_search_runs():
    view = resolve(inputs(has_goals=True, searched=True, search_requested=True, result_ids=("a",), selected_id="a"))
    assert view.state is JobsState.SEARCHING and view.show_workspace and view.selected_id == "a"


def test_first_search_without_results_keeps_setup_out_of_the_way():
    view = resolve(inputs(has_goals=True, search_requested=True))
    assert view.state is JobsState.SEARCHING and not view.show_workspace and not view.show_setup


def test_selection_survives_reruns_and_view_changes_while_listed():
    assert resolve_selection("b", ("a", "b", "c")) == "b"
    assert resolve_selection("z", ("a", "b")) == "a"
    assert resolve_selection("b", ()) is None
    view = resolve(inputs(searched=True, result_ids=("c", "b"), selected_id="b", view=NEWEST))
    assert view.selected_id == "b"


def test_selecting_another_job_changes_the_detail():
    assert resolve(inputs(searched=True, result_ids=("a", "b"), selected_id="b")).selected_id == "b"


def test_saved_view_works_without_a_search():
    view = resolve(inputs(view=SAVED_VIEW, result_ids=("s1",)))
    assert view.state is JobsState.SAVED and view.show_workspace and view.selected_id == "s1"


def test_partial_failure_keeps_the_successful_results():
    statuses = (("greenhouse", "ok"), ("lever", "ok"), ("ashby", "failed"))
    view = resolve(inputs(searched=True, result_ids=("a",), provider_statuses=statuses))
    assert view.state is JobsState.DETAIL_SELECTED and view.partial_failure
    assert "Ashby didn't respond" in view.source_note and view.source_note.startswith("Greenhouse, Lever")


def test_no_results_state():
    view = resolve(inputs(has_goals=True, searched=True, provider_statuses=OK3))
    assert view.state is JobsState.NO_RESULTS and not view.show_workspace


def test_every_source_failing_says_so():
    partial, note = source_note((("greenhouse", "failed"), ("lever", "failed")))
    assert not partial and note.startswith("No source responded")


def test_summary_line_reads_like_a_search():
    goals = {"job_title": "Product marketing", "location": "Denver", "remote_preference": "remote",
             "experience_level": ["Mid-level"], "min_salary": 90000}
    assert goals_summary_line(goals) == "Product marketing roles · Denver or remote · Mid-level · $90k+"
    assert goals_summary_line({"job_title": "Analyst"}) == "Analyst roles · Anywhere"


def test_best_matches_put_unknown_fit_after_known_and_passed_last():
    jobs = [SimpleNamespace(id=i, posted_date=None) for i in ("unknown", "low", "high", "passed")]
    fits = {"unknown": None, "low": 40.0, "high": 90.0, "passed": 99.0}
    ordered = order_jobs(jobs, BEST, fits, {"passed": "pass"}, lambda j: j.id)
    assert [j.id for j in ordered] == ["high", "low", "unknown", "passed"]


def test_newest_sorts_by_post_date_with_undated_last():
    jobs = [SimpleNamespace(id="old", posted_date=datetime(2026, 9, 1)),
            SimpleNamespace(id="undated", posted_date=None),
            SimpleNamespace(id="new", posted_date=datetime(2026, 10, 3))]
    assert [j.id for j in order_jobs(jobs, NEWEST, {}, {}, lambda j: j.id)] == ["new", "old", "undated"]


def test_searched_at_text():
    assert searched_at_text(datetime(2026, 10, 4, 14, 41)) == "searched 2:41 PM"
    assert searched_at_text(None) == ""
