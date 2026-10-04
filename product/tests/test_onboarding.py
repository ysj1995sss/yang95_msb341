from resume_tailorer.ui.onboarding import (
    GOALS_KEY, WIZARD_STEPS, apply_goals_to_search_form, build_checklist, goals_summary,
    next_item, progress, save_goals, step_valid,
)


def test_empty_session_starts_at_facts():
    items = build_checklist({})
    assert progress(items) == (0, 5)
    assert next_item(items).label == "Add and verify your facts"


def test_progress_follows_session_evidence():
    items = build_checklist({"career_profile": object(), GOALS_KEY: {"job_title": "PM"}})
    assert progress(items)[0] == 2
    assert next_item(items).label == "Pick a role"


def test_only_job_title_is_required():
    required = [s.key for s in WIZARD_STEPS if s.required]
    assert required == ["job_title"]
    assert not step_valid(WIZARD_STEPS[0], {"job_title": "  "})
    assert step_valid(WIZARD_STEPS[0], {"job_title": "PM"})


def test_goals_seed_search_form_once():
    session = {}
    save_goals(session, {"job_title": "PM", "min_salary": 0, "remote_preference": "any", "sponsorship_required": False})
    assert "min_salary" not in session[GOALS_KEY]
    assert apply_goals_to_search_form(session) is True
    assert session["job_title"] == "PM"
    session["job_title"] = "Edited on the page"
    assert apply_goals_to_search_form(session) is False
    assert session["job_title"] == "Edited on the page"


def test_summary_states_unknowns_plainly():
    rows = dict(goals_summary({"job_title": "PM"}))
    assert rows["Minimum salary"] == "No minimum"
    assert rows["Industries"] == "Open to anything"
