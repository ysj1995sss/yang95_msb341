from resume_tailorer.ui.onboarding import (
    WIZARD_STEPS,
    apply_goals_to_search_form,
    goals_summary,
    save_goals,
    step_valid,
    suggested_titles,
)


def test_only_the_job_title_is_required():
    assert [s.key for s in WIZARD_STEPS if s.required] == ["job_title"]
    assert not step_valid(WIZARD_STEPS[0], {"job_title": "  "})
    assert step_valid(WIZARD_STEPS[0], {"job_title": "Analyst"})


def test_suggested_titles_come_only_from_the_users_own_history():
    profile = {"work_experience": [{"title": "Analyst"}, {"title": "analyst"}, {"title": "Intern"}, {"title": ""}]}
    assert suggested_titles(profile) == ["Analyst", "Intern"]
    assert suggested_titles(None) == []


def test_authorization_answers_are_stored_apart_from_search_goals():
    record = {}
    save_goals(record, {"job_title": "Analyst", "min_salary": 0, "remote_preference": "remote",
                        "authorized_to_work": True, "sponsorship_required": None})
    assert record["preferences"] == {"job_title": "Analyst", "remote_preference": "remote"}
    assert record["authorization"] == {"authorized_to_work": True, "sponsorship_required": None}


def test_saved_goals_seed_the_search_form_until_they_change():
    record = {"preferences": {"job_title": "Analyst"}, "authorization": {"sponsorship_required": True}}
    session = {}
    assert apply_goals_to_search_form(session, record) is True
    assert session["job_title"] == "Analyst" and session["sponsorship_required"] is True
    session["job_title"] = "Edited on the page"
    assert apply_goals_to_search_form(session, record) is False
    assert session["job_title"] == "Edited on the page"
    record["preferences"]["job_title"] = "Data Analyst"
    assert apply_goals_to_search_form(session, record) is True
    assert session["job_title"] == "Data Analyst"


def test_no_goals_means_nothing_is_seeded():
    session = {}
    assert apply_goals_to_search_form(session, {}) is False
    assert session == {}


def test_summary_states_unknowns_plainly():
    rows = dict(goals_summary({"preferences": {"job_title": "Analyst"}}))
    assert rows["Minimum salary"] == "No minimum"
    assert rows["Industries"] == "Open to anything"
    assert rows["Needs sponsorship"] == "I'll answer later"
