import os
import tempfile
from unittest.mock import patch

import pytest

from resume_tailorer.applications import submission_engine as engine_module
from resume_tailorer.applications.answer_bank import apply_answer_bank, question_key
from resume_tailorer.applications.ats_parsers.greenhouse_parser import GreenhouseParser
from resume_tailorer.applications.database import ApplicationDatabase
from resume_tailorer.applications.models import ApplicationMode, ATSCapability, FormField
from resume_tailorer.applications.submission_engine import SubmissionEngine
from resume_tailorer.models.career_profile import CareerTruthProfile, WorkExperience

FORM = """
<form>
  <label for="fn">First name</label><input id="fn" name="first_name" required>
  <label for="q1">Are you legally authorized to work in the United States?</label>
  <select id="q1" name="question_101" required><option>Yes</option><option>No</option></select>
  <label>Why do you want to work here? <textarea name="question_202"></textarea></label>
</form>
"""


class _CapableParser(GreenhouseParser):
    def get_capability(self):
        return ATSCapability(platform="greenhouse", final_submission=True, profile_prefill=True)


@pytest.fixture
def db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database = ApplicationDatabase(path)
    database.create_tables()
    yield database
    database.close()
    os.unlink(path)


def _profile():
    return CareerTruthProfile(
        contact_info={"name": "Alex Kim", "email": "alex@example.com"}, education=[],
        work_experience=[WorkExperience(employer="Acme", title="PM", dates="2020", responsibilities=[], accomplishments=[])],
        skills=[], tools=[], certifications=[], accomplishments=[],
    )


def _apply(engine, dry_run=True):
    return engine.apply_for_job(
        job_posting_id="greenhouse_9", form_url="https://example.com/apply", ats_platform="greenhouse",
        profile=_profile(), resume_pdf_path="/tmp/r.pdf", candidate_fit_score=1.0, resume_match_score=1.0,
        mode=ApplicationMode.ASSIST, dry_run=dry_run,
    )


def test_parser_captures_the_visible_question():
    labels = [f.label for f in GreenhouseParser().parse_form(FORM)]
    assert labels == [
        "First name",
        "Are you legally authorized to work in the United States?",
        "Why do you want to work here?",
    ]


def test_only_approved_answers_are_used():
    fields = [
        FormField("question_101", "select", required=True, label="Are you authorized to work in the US?"),
        FormField("question_202", "textarea", label="Why us?"),
        FormField("resume", "file", required=True),
    ]
    filled, custom, unanswered = apply_answer_bank(fields, {question_key("Why us?"): "Your analytics mission."})
    assert custom == {"Why us?": "Your analytics mission."}
    assert unanswered == ["Are you authorized to work in the US?"]
    assert filled[1].value == "Your analytics mission." and filled[1].prefilled


def test_preview_lists_unanswered_questions_and_saves_nothing(db):
    engine = SubmissionEngine(db)
    with patch.object(engine, "_fetch_form_html", return_value=FORM):
        result = _apply(engine)
    assert "Are you legally authorized to work in the United States?" in result.unanswered_questions
    assert result.custom_answers == {}
    assert db.get_submissions_by_job("greenhouse_9") == []


def test_approved_answers_are_reused_and_recorded(db, monkeypatch):
    monkeypatch.setitem(engine_module._PARSER_MAP, "greenhouse", _CapableParser)
    question = "Are you legally authorized to work in the United States?"
    db.save_answer(question_key(question), question, "Yes")
    engine = SubmissionEngine(db)
    with patch.object(engine, "_fetch_form_html", return_value=FORM), \
         patch.object(engine, "_submit_to_platform", return_value="C-1") as submit:
        result = _apply(engine, dry_run=False)
    assert submit.call_args.args[1]["question_101"] == "Yes"
    saved = db.get_submission(result.application_id)
    assert saved.custom_answers == {question: "Yes"}
    assert saved.answers_version


def test_required_question_without_an_approved_answer_blocks_real_submit(db, monkeypatch):
    monkeypatch.setitem(engine_module._PARSER_MAP, "greenhouse", _CapableParser)
    engine = SubmissionEngine(db)
    with patch.object(engine, "_fetch_form_html", return_value=FORM), \
         patch.object(engine, "_submit_to_platform") as submit:
        with pytest.raises(ValueError, match="question_101"):
            _apply(engine, dry_run=False)
    submit.assert_not_called()


def test_a_question_asked_twice_is_listed_and_answered_once():
    fields = [
        FormField("q_1", "text", label="Reservation number"),
        FormField("q_2", "text", label="Reservation  Number"),
        FormField("q_3", "select", label="Are you authorized to work in the US?"),
    ]
    filled, custom, unanswered = apply_answer_bank(fields, {question_key("Reservation number"): "R-1"})
    assert unanswered == ["Are you authorized to work in the US?"]
    assert custom == {"Reservation number": "R-1", "Reservation  Number": "R-1"}
    assert [f.value for f in filled[:2]] == ["R-1", "R-1"]

    _f, _c, still = apply_answer_bank(fields, {})
    assert still == ["Reservation number", "Are you authorized to work in the US?"]
