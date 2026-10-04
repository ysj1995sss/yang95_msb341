from resume_tailorer.ui.profile_readiness import build_readiness, readiness_line

GOOD = {
    "contact_info": {"name": "Sam", "email": "s@example.com"},
    "work_experience": [{"title": "Analyst", "employer": "Northwind", "dates": "2019-2023",
                         "responsibilities": ["x"], "accomplishments": []}],
    "education": [{"institution": "State U", "degree": "BS", "year": 2018}],
    "skills": ["SQL"],
}


def test_no_resume_means_not_started():
    readiness = build_readiness({})
    assert not readiness.has_resume
    assert readiness.summary == "Not started: import a resume"
    assert readiness.attention == ()


def test_complete_profile_has_all_required_sections_ready():
    readiness = build_readiness({"profile": GOOD, "resume": {"filename": "cv.docx"}})
    assert readiness.required_ready == readiness.required_total == 4
    assert readiness.attention == ()
    assert "%" not in readiness.summary


def test_attention_lists_only_what_needs_the_user():
    profile = dict(GOOD, contact_info={"name": "Sam"},
                   work_experience=[{"title": "Analyst", "employer": "Northwind", "dates": "",
                                     "responsibilities": ["x"], "accomplishments": []}])
    readiness = build_readiness({"profile": profile, "resume": {}})
    assert "Add your email" in readiness.attention
    assert any("dates are missing" in a for a in readiness.attention)
    assert readiness.required_ready == 2


def test_no_degree_can_be_declared():
    profile = dict(GOOD, education=[])
    assert not build_readiness({"profile": profile}).sections[2].ready
    assert build_readiness({"profile": profile, "no_education": True}).sections[2].ready


def test_optional_sections_never_block_readiness():
    readiness = build_readiness({"profile": GOOD})
    optional = [s for s in readiness.sections if not s.required]
    assert {s.name for s in optional} == {
        "Professional summary", "Certifications", "Links", "Job goals", "Work authorization",
    }
    assert readiness.required_ready == 4


def test_rail_line_reads_the_session():
    assert readiness_line({"profile_record": {"profile": GOOD}}) == "4 of 4 required sections ready"
    assert readiness_line({}) == "Not started: import a resume"


def test_section_rows_summarise_instead_of_opening_every_field():
    from resume_tailorer.ui.profile_readiness import section_rows

    rows = {r.key: r for r in section_rows({"profile": GOOD, "resume": {}}, answers=3)}
    assert rows["work"].detail == "1 role" and rows["work"].status == "Ready"
    assert rows["contact"].status == "Ready" and rows["contact"].action == "Edit"
    assert rows["authorization"].status == "Optional" and rows["authorization"].action == "Add"
    assert rows["answers"].detail == "3 answers" and rows["answers"].action == "Manage"


def test_likely_parse_problems_are_flagged_for_review():
    from resume_tailorer.ui.profile_readiness import first_section_needing_review, review_items, section_rows

    profile = dict(GOOD, skills=["SQL", "sql", "Tableau"], tools=["Tableau"],
                   education=[{"institution": "State U", "degree": "MBA", "field": "", "year": 2020}],
                   work_experience=[dict(GOOD["work_experience"][0], title="Developed a growth strategy " * 4)])
    items = review_items(profile)
    assert any("listed twice" in i for i in items["skills"])
    assert any("both skills and tools" in i for i in items["skills"])
    assert any("field of study is empty" in i for i in items["education"])
    assert any("looks like a sentence" in i for i in items["work"])
    rows = section_rows({"profile": profile})
    assert first_section_needing_review(rows) == "work"
    assert {r.key: r.action for r in rows}["skills"] == "Review"


def test_provenance_is_summarised_once_per_section():
    from resume_tailorer.ui.profile_readiness import provenance_summary

    record = {"provenance": {"skills": "resume", "tools": "edited", "contact_info.name": "confirmed"}}
    assert provenance_summary(record, "skills") == "From your resume, 1 edited by you"
    assert provenance_summary(record, "contact") == "Confirmed by you"
    assert provenance_summary(record, "links") == ""
