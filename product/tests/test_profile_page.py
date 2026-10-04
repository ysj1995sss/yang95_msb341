"""Career Profile page: a summary list with one editor at a time (spec 008). Synthetic data."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from resume_tailorer.models import CareerTruthProfile
from resume_tailorer.profile_import import import_resume, store_for

APP = str(Path(__file__).resolve().parent.parent / "resume_tailorer" / "app.py")

PROFILE = {
    "contact_info": {"name": "Riley Park", "email": "riley@example.com", "phone": "", "location": ""},
    "education": [{"degree": "BS", "field": "Economics", "institution": "State U", "year": 2017, "gpa": None, "notes": []}],
    "work_experience": [{"employer": "Acme", "title": "Analyst", "dates": "2019-2024",
                         "responsibilities": ["Built SQL reports"], "accomplishments": []}],
    "skills": ["SQL"], "tools": ["Excel"], "certifications": [], "accomplishments": [], "summary": "",
}


class StubParser:
    def __init__(self, profile):
        self.profile = profile

    def parse(self, path):
        return CareerTruthProfile.from_dict(self.profile)


def _open(tmp_path, monkeypatch, profile):
    monkeypatch.setenv("JOB_COPILOT_DATA_DIR", str(tmp_path / "data"))
    import_resume(store_for("local"), "riley.docx", b"x", parser=StubParser(profile))
    at = AppTest.from_file(APP, default_timeout=60)
    at.switch_page("pages/1_Profile_Review.py")
    at.run()
    assert not at.exception, at.exception
    return at


def test_default_view_is_a_summary_not_an_open_form(tmp_path, monkeypatch):
    at = _open(tmp_path, monkeypatch, PROFILE)
    assert not [t for t in at.text_input if t.label.startswith("Email")]
    labels = [b.label for b in at.button]
    assert labels.count("Edit") >= 2 and "Manage" in labels and "Confirm the rest" in labels


def test_editing_a_section_saves_and_marks_it_as_yours(tmp_path, monkeypatch):
    at = _open(tmp_path, monkeypatch, PROFILE)
    [b for b in at.button if b.key == "cp_open_contact"][0].click()
    at.run()
    location = [t for t in at.text_input if t.label.startswith("Location")][0]
    location.set_value("Denver, CO")
    [b for b in at.button if b.label == "Save contact"][0].click()
    at.run()
    assert not at.exception, at.exception
    record = store_for("local").load()
    assert record["profile"]["contact_info"]["location"] == "Denver, CO"
    assert record["provenance"]["contact_info.location"] == "edited"


def test_a_likely_parse_problem_opens_its_section_first(tmp_path, monkeypatch):
    profile = dict(PROFILE, skills=["SQL", "sql"])
    at = _open(tmp_path, monkeypatch, profile)
    assert at.session_state["cp_open_section"] == "skills"
    assert any("listed twice" in m.value for m in at.markdown)
