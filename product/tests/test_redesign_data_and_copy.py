"""Small database reads added for Home and Career Profile, and the copy rules
from spec 007 (no hype words, no claims of submitting)."""

import re
from datetime import datetime
from pathlib import Path

from resume_tailorer.applications.database import ApplicationDatabase
from resume_tailorer.job_search.database import JobDatabase
from resume_tailorer.job_search.models import JobPosting, JobSource, UserSelection

ROOT = Path(__file__).resolve().parent.parent / "resume_tailorer"
USER_FACING = [ROOT / "app.py", *sorted((ROOT / "pages").glob("*.py")), *sorted((ROOT / "ui").glob("*.py")),
               ROOT / "applications" / "streamlit_views.py"]


def _job(i):
    return JobPosting(source=JobSource.GREENHOUSE, source_id=str(i), company=f"Co{i}", title="Analyst",
                      location="Remote", description="d")


def test_jobs_by_latest_action_uses_only_the_newest_choice(tmp_path):
    db = JobDatabase(str(tmp_path / "jobs.db"))
    db.create_tables()
    for i in (1, 2):
        db.save_job_posting(_job(i))
    db.record_user_selection(UserSelection("greenhouse_1", "save", timestamp=datetime(2026, 10, 1)))
    db.record_user_selection(UserSelection("greenhouse_2", "save", timestamp=datetime(2026, 10, 1)))
    db.record_user_selection(UserSelection("greenhouse_2", "pass", timestamp=datetime(2026, 10, 2)))
    assert [j.company for j in db.get_jobs_by_latest_action("save")] == ["Co1"]
    assert [j.company for j in db.get_jobs_by_latest_action("pass")] == ["Co2"]


def test_latest_seen_is_none_before_any_search(tmp_path):
    db = JobDatabase(str(tmp_path / "jobs.db"))
    db.create_tables()
    assert db.latest_seen() is None


def test_answer_entries_keep_the_question_text_and_can_be_removed(tmp_path):
    db = ApplicationDatabase(str(tmp_path / "apps.db"))
    db.create_tables()
    db.save_answer("why us", "Why us?", "Your analytics work.")
    (entry,) = db.get_answer_entries()
    assert (entry["question"], entry["answer"]) == ("Why us?", "Your analytics work.")
    db.delete_answer("why us")
    assert db.get_answer_entries() == [] and db.get_answers() == {}


BANNED = [
    r"\bactivate ai\b", r"\bsupercharge", r"\bautopilot\b", r"successfully submitted",
    r"\bartifact pipeline\b", r"\bdisposition\b", r"\bprovider adapter\b", r"\bcapability model\b",
]


def _string_literals(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    # Docstrings and comments may use internal terms; only quoted UI strings are checked.
    text = re.sub(r'"""[\s\S]*?"""', "", text)
    text = re.sub(r"#.*", "", text)
    literals = [a or b for a, b in re.findall(r'"([^"\n]*)"|\'([^\'\n]*)\'', text)]
    # Prose only: identifiers and dictionary keys have no spaces.
    return " | ".join(lit for lit in literals if " " in lit.strip())


def test_user_facing_copy_avoids_hype_and_internal_terms():
    for path in USER_FACING:
        strings = _string_literals(path).lower()
        for pattern in BANNED:
            assert not re.search(pattern, strings), f"{path.name}: {pattern}"
