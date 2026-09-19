import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock

from resume_tailorer.applications.submission_engine import SubmissionEngine
from resume_tailorer.applications.database import ApplicationDatabase
from resume_tailorer.applications.models import ApplicationMode
from resume_tailorer.models.career_profile import CareerTruthProfile, EducationEntry, WorkExperience


SAMPLE_FORM_HTML = """
<form>
    <input type="text" name="first_name" required>
    <input type="text" name="last_name" required>
    <input type="email" name="email" required>
    <textarea name="cover_letter"></textarea>
</form>
"""


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = ApplicationDatabase(path)
    db.create_tables()
    yield db
    db.close()
    os.unlink(path)


def _make_profile():
    return CareerTruthProfile(
        contact_info={"name": "Jane Doe", "email": "jane@example.com", "phone": "555-1234", "location": "SF"},
        education=[EducationEntry(degree="BS", field="CS", institution="MIT", year=2020)],
        work_experience=[WorkExperience(employer="TechCorp", title="Engineer", dates="2020-2023", responsibilities=[], accomplishments=[])],
        skills=["Python"],
        tools=["Docker"],
        certifications=[],
        accomplishments=[],
    )


def test_dry_run_defaults_to_true_and_never_calls_submit(temp_db):
    """The default call NEVER performs a real submission."""
    engine = SubmissionEngine(temp_db)
    with patch.object(engine, "_submit_to_platform") as mock_submit:
        with patch.object(engine, "_fetch_form_html", return_value=SAMPLE_FORM_HTML):
            result = engine.apply_for_job(
                job_posting_id="greenhouse_1",
                form_url="https://boards.greenhouse.io/company/jobs/1",
                ats_platform="greenhouse",
                profile=_make_profile(),
                resume_pdf_path="/tmp/resume.pdf",
                candidate_fit_score=85.0,
                resume_match_score=90.0,
                mode=ApplicationMode.ASSIST,
            )
    mock_submit.assert_not_called()
    assert result.application_id  # still recorded


def test_dry_run_false_calls_submit_for_assist_mode(temp_db):
    engine = SubmissionEngine(temp_db)
    with patch.object(engine, "_submit_to_platform", return_value="CONF-123") as mock_submit:
        with patch.object(engine, "_fetch_form_html", return_value=SAMPLE_FORM_HTML):
            result = engine.apply_for_job(
                job_posting_id="greenhouse_1",
                form_url="https://boards.greenhouse.io/company/jobs/1",
                ats_platform="greenhouse",
                profile=_make_profile(),
                resume_pdf_path="/tmp/resume.pdf",
                candidate_fit_score=85.0,
                resume_match_score=90.0,
                mode=ApplicationMode.ASSIST,
                dry_run=False,
            )
    mock_submit.assert_called_once()
    assert result.confirmation_number == "CONF-123"


def test_manual_mode_never_submits_even_with_dry_run_false(temp_db):
    """Manual mode's entire point is the user applies themselves; this engine never touches the real form for them."""
    engine = SubmissionEngine(temp_db)
    with patch.object(engine, "_submit_to_platform") as mock_submit:
        with patch.object(engine, "_fetch_form_html", return_value=SAMPLE_FORM_HTML):
            result = engine.apply_for_job(
                job_posting_id="greenhouse_1",
                form_url="https://boards.greenhouse.io/company/jobs/1",
                ats_platform="greenhouse",
                profile=_make_profile(),
                resume_pdf_path="/tmp/resume.pdf",
                candidate_fit_score=85.0,
                resume_match_score=90.0,
                mode=ApplicationMode.MANUAL,
                dry_run=False,
            )
    mock_submit.assert_not_called()
    assert result.mode == ApplicationMode.MANUAL


def test_auto_mode_refuses_submission_with_unfilled_required_field(temp_db):
    """Auto mode must never submit a form with an unanswered required question."""
    engine = SubmissionEngine(temp_db)
    # cover_letter is not a field FormFiller can confidently fill, but it's not required here.
    # Use a form where a REQUIRED field can't be filled to trigger the refusal.
    form_with_unfillable_required = """
    <form>
        <input type="text" name="first_name" required>
        <input type="text" name="obscure_custom_question" required>
    </form>
    """
    with patch.object(engine, "_fetch_form_html", return_value=form_with_unfillable_required):
        with pytest.raises(ValueError, match="required"):
            engine.apply_for_job(
                job_posting_id="greenhouse_1",
                form_url="https://boards.greenhouse.io/company/jobs/1",
                ats_platform="greenhouse",
                profile=_make_profile(),
                resume_pdf_path="/tmp/resume.pdf",
                candidate_fit_score=85.0,
                resume_match_score=90.0,
                mode=ApplicationMode.AUTO,
                dry_run=False,
            )


def test_unsupported_platform_refuses_submission(temp_db):
    engine = SubmissionEngine(temp_db)
    with pytest.raises(ValueError, match="[Ww]orkday"):
        engine.apply_for_job(
            job_posting_id="workday_1",
            form_url="https://company.wd1.myworkdayjobs.com/job/1",
            ats_platform="workday",
            profile=_make_profile(),
            resume_pdf_path="/tmp/resume.pdf",
            candidate_fit_score=85.0,
            resume_match_score=90.0,
            mode=ApplicationMode.ASSIST,
        )


def test_submission_recorded_before_real_submit_attempted(temp_db):
    """The audit record must exist even if the real POST would fail — verify save happens first."""
    engine = SubmissionEngine(temp_db)
    with patch.object(engine, "_submit_to_platform", side_effect=Exception("network error")):
        with patch.object(engine, "_fetch_form_html", return_value=SAMPLE_FORM_HTML):
            with pytest.raises(Exception, match="network error"):
                engine.apply_for_job(
                    job_posting_id="greenhouse_1",
                    form_url="https://boards.greenhouse.io/company/jobs/1",
                    ats_platform="greenhouse",
                    profile=_make_profile(),
                    resume_pdf_path="/tmp/resume.pdf",
                    candidate_fit_score=85.0,
                    resume_match_score=90.0,
                    mode=ApplicationMode.ASSIST,
                    dry_run=False,
                )
    submissions = temp_db.get_submissions_by_job("greenhouse_1")
    assert len(submissions) == 1  # recorded despite the failed submit


def test_submission_captures_filled_fields(temp_db):
    engine = SubmissionEngine(temp_db)
    with patch.object(engine, "_fetch_form_html", return_value=SAMPLE_FORM_HTML):
        result = engine.apply_for_job(
            job_posting_id="greenhouse_1",
            form_url="https://boards.greenhouse.io/company/jobs/1",
            ats_platform="greenhouse",
            profile=_make_profile(),
            resume_pdf_path="/tmp/resume.pdf",
            candidate_fit_score=85.0,
            resume_match_score=90.0,
            mode=ApplicationMode.ASSIST,
        )
    assert result.form_fields_submitted.get("first_name") == "Jane"
    assert result.form_fields_submitted.get("email") == "jane@example.com"
