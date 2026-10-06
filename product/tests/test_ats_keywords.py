from resume_tailorer.analyzers.ats_keywords import check_keywords, profile_text, terms_in

POSTING = """Integrated Marketing Manager, Hardware
Requirements: 5+ years of product marketing and go-to-market experience for hardware launches.
Strong SQL and Tableau skills; stakeholder management across cross-functional teams.
Preferred: MBA, experience with Figma and A/B testing."""


def test_go_never_matches_inside_go_to_market():
    labels = terms_in("We value go-to-market strategy and great messaging")
    assert "Go-to-market" in labels and "Go" not in labels
    assert "Go" in terms_in("Backend services written in Golang")


def test_noise_words_are_not_keywords():
    labels = terms_in("experience with years of the and with")
    assert labels == []


def test_missing_and_present_are_split_against_the_resume():
    resume = "Led go-to-market launches using SQL dashboards; managed stakeholder management for 30+ partners. MBA."
    check = check_keywords(POSTING, resume)
    assert {"Go-to-market", "SQL", "Stakeholder management", "MBA"} <= set(check.present)
    assert {"Tableau", "Figma", "A/B testing", "Product marketing"} <= set(check.missing)
    assert check.summary.endswith("posting terms appear in your Career Profile.")
    assert "resume" not in check.summary  # the check reads the profile, not the resume (spec 010)


def test_single_letter_r_needs_standalone_context():
    assert "R" in terms_in("Python, R, and SQL")
    assert "R" not in terms_in("research and reporting")


def test_profile_text_collects_every_fact():
    text = profile_text({"skills": ["SQL"], "work_experience": [{"responsibilities": ["Built Tableau dashboards"]}]})
    assert "SQL" in text and "Tableau" in text


def test_contact_details_goals_and_preferences_are_not_evidence():
    """Spec 010: only facts a resume is built from count; a goal of "product marketing" or a
    location isn't evidence of a skill."""
    text = profile_text({
        "contact_info": {"name": "Riley Park", "location": "Remote"},
        "preferences": {"target_roles": ["Product marketing"]},
        "goals": ["Salesforce admin"],
        "skills": ["SQL"],
    })
    assert "SQL" in text
    assert "Riley" not in text and "Product marketing" not in text and "Salesforce" not in text


def test_ats_explainer_promises_nothing_it_cannot_do():
    from resume_tailorer.ui import ats_explainer

    text = " ".join([ats_explainer.TITLE, *ats_explainer.PARAGRAPHS, ats_explainer.TERMS_NOTE, ats_explainer.OVERLAP_NOTE]).lower()
    assert "no universal ats score" in text and "not an employer score" in text
    for promise in ("pass the ats", "beat the ats", "guarantee", "ats-proof", "ats score of"):
        assert promise not in text


def test_empty_posting_says_so():
    assert check_keywords("", "anything").summary.startswith("No common screening keywords")
