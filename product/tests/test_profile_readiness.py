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
