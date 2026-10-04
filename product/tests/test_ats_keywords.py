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
    assert "key terms already on your resume" in check.summary


def test_single_letter_r_needs_standalone_context():
    assert "R" in terms_in("Python, R, and SQL")
    assert "R" not in terms_in("research and reporting")


def test_profile_text_collects_every_string():
    text = profile_text({"skills": ["SQL"], "work_experience": [{"responsibilities": ["Built Tableau dashboards"]}]})
    assert "SQL" in text and "Tableau" in text


def test_empty_posting_says_so():
    assert check_keywords("", "anything").summary.startswith("No common screening keywords")
