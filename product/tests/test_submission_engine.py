import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock

from resume_tailorer.applications import submission_engine as submission_engine_module
from resume_tailorer.applications.ats_parsers.greenhouse_parser import GreenhouseParser
from resume_tailorer.applications.submission_engine import SubmissionEngine
from resume_tailorer.applications.database import ApplicationDatabase
from resume_tailorer.applications.models import ApplicationMode, ApplicationStatus, ATSCapability, SubmissionResult
from resume_tailorer.models.career_profile import CareerTruthProfile, EducationEntry, WorkExperience


class _CapableGreenhouseParser(GreenhouseParser):
    """Test-only stand-in for a platform that HAS proven real submission
    works -- exercises the real-submit code path without depending on any
    real platform actually having final_submission=True today (none do;
    see decision 016)."""

    def get_capability(self) -> ATSCapability:
        return ATSCapability(platform="greenhouse", final_submission=True, profile_prefill=True)


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
    # A preview is not a submission: nothing is recorded at all.
    assert not result.application_id
    assert temp_db.get_submissions_by_job("greenhouse_1") == []
    assert result.form_fields_submitted.get("email") == "jane@example.com"


def test_dry_run_false_is_blocked_for_a_platform_without_final_submission_capability(temp_db):
    """No real platform currently declares final_submission=True (decision
    016) -- a real-submit attempt against Greenhouse must fail loudly
    instead of silently POSTing to a URL that was never a real
    form-submission endpoint."""
    engine = SubmissionEngine(temp_db)
    with patch.object(engine, "_submit_to_platform") as mock_submit:
        with patch.object(engine, "_fetch_form_html", return_value=SAMPLE_FORM_HTML):
            with pytest.raises(ValueError, match="final_submission"):
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
    mock_submit.assert_not_called()


def test_dry_run_false_calls_submit_when_platform_has_final_submission_capability(temp_db, monkeypatch):
    """Once a platform genuinely proves it can complete a real submission,
    the real-submit code path itself still works end to end."""
    monkeypatch.setitem(submission_engine_module._PARSER_MAP, "greenhouse", _CapableGreenhouseParser)
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
    assert temp_db.get_current_status(result.application_id) == ApplicationStatus.APPLIED
    persisted = temp_db.get_submission(result.application_id)
    assert persisted.confirmation_number == "CONF-123"


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
    # Manual mode: the user applies themselves, so it is READY_TO_APPLY (never
    # APPLIED) and they advance it via the dashboard once they've actually applied.
    assert temp_db.get_current_status(result.application_id) == ApplicationStatus.READY_TO_APPLY


def test_manual_mode_gets_ready_to_apply_status_immediately(temp_db):
    """Manual mode submissions must be immediately trackable in the dashboard,
    unlike Assist/Auto previews which stay invisible until a real submit succeeds."""
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
            mode=ApplicationMode.MANUAL,
            dry_run=False,
        )
    status = temp_db.get_current_status(result.application_id)
    assert status == ApplicationStatus.READY_TO_APPLY


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


def test_submission_recorded_before_real_submit_attempted(temp_db, monkeypatch):
    """The audit record must exist even if the real POST would fail — verify save happens first."""
    monkeypatch.setitem(submission_engine_module._PARSER_MAP, "greenhouse", _CapableGreenhouseParser)
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
    # ...but a failed submission must NOT show up as APPLIED on the dashboard.
    assert temp_db.get_current_status(submissions[0].application_id) is None


def test_auto_mode_refuses_empty_parsed_form(temp_db):
    """Zero parsed fields means the ATS page was not actually parsed — never POST {}."""
    engine = SubmissionEngine(temp_db)
    with patch.object(engine, "_fetch_form_html", return_value="<html><body>Sign in to apply</body></html>"):
        with patch.object(engine, "_submit_to_platform") as mock_submit:
            with pytest.raises(ValueError, match="could not parse"):
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
    mock_submit.assert_not_called()


def test_assist_mode_refuses_unfilled_required_on_real_submit(temp_db):
    """Assist real-submit must stop when a required field could not be filled."""
    engine = SubmissionEngine(temp_db)
    form_with_unfillable_required = """
    <form>
        <input type="text" name="first_name" required>
        <input type="text" name="obscure_custom_question" required>
    </form>
    """
    with patch.object(engine, "_fetch_form_html", return_value=form_with_unfillable_required):
        with patch.object(engine, "_submit_to_platform") as mock_submit:
            with pytest.raises(ValueError, match="required"):
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
    mock_submit.assert_not_called()


def test_fetch_form_html_raises_on_http_error(temp_db):
    engine = SubmissionEngine(temp_db)
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("404")
    with patch("resume_tailorer.applications.submission_engine.requests.get", return_value=mock_response):
        with pytest.raises(Exception, match="404"):
            engine._fetch_form_html("https://boards.greenhouse.io/company/jobs/1")


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


def test_snapshots_are_persisted_on_the_submission(temp_db):
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
            mode=ApplicationMode.MANUAL,
            dry_run=False,
            job_snapshot={"company": "Acme", "title": "Engineer"},
            candidate_fit_snapshot={"overall_fit": 85.0},
            career_profile_version="hash-abc",
        )
    persisted = temp_db.get_submission(result.application_id)
    assert persisted.job_snapshot == {"company": "Acme", "title": "Engineer"}
    assert persisted.candidate_fit_snapshot == {"overall_fit": 85.0}
    assert persisted.career_profile_version == "hash-abc"


class TestIdempotencyInEngine:
    def test_second_real_submit_for_the_same_job_is_refused(self, temp_db, monkeypatch):
        monkeypatch.setitem(submission_engine_module._PARSER_MAP, "greenhouse", _CapableGreenhouseParser)
        engine = SubmissionEngine(temp_db)
        with patch.object(engine, "_submit_to_platform", return_value="CONF-1"):
            with patch.object(engine, "_fetch_form_html", return_value=SAMPLE_FORM_HTML):
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
                with pytest.raises(ValueError, match="already has a confirmed submission"):
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

    def test_preview_after_a_real_submit_is_still_allowed(self, temp_db, monkeypatch):
        """Idempotency blocks a second REAL submit, not harmless previews."""
        monkeypatch.setitem(submission_engine_module._PARSER_MAP, "greenhouse", _CapableGreenhouseParser)
        engine = SubmissionEngine(temp_db)
        with patch.object(engine, "_submit_to_platform", return_value="CONF-1"):
            with patch.object(engine, "_fetch_form_html", return_value=SAMPLE_FORM_HTML):
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
                # dry_run=True (the default) must not be blocked by idempotency.
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
                assert not result.application_id
                assert result.form_fields_submitted


class TestSubmissionAttemptTracking:
    def test_capability_block_records_a_failed_attempt(self, temp_db):
        """A real-submit request against a platform without
        final_submission is itself worth an audit trail entry."""
        engine = SubmissionEngine(temp_db)
        with patch.object(engine, "_fetch_form_html", return_value=SAMPLE_FORM_HTML):
            with pytest.raises(ValueError, match="final_submission"):
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
        attempts = temp_db.get_attempts_by_application(submissions[0].application_id)
        assert len(attempts) == 1
        assert attempts[0].result == SubmissionResult.FAILED
        assert attempts[0].error_code == "UNSUPPORTED_PLATFORM"

    def test_successful_real_submit_records_a_confirmed_attempt(self, temp_db, monkeypatch):
        monkeypatch.setitem(submission_engine_module._PARSER_MAP, "greenhouse", _CapableGreenhouseParser)
        engine = SubmissionEngine(temp_db)
        with patch.object(engine, "_submit_to_platform", return_value="CONF-99"):
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
        attempts = temp_db.get_attempts_by_application(result.application_id)
        assert len(attempts) == 1
        assert attempts[0].result == SubmissionResult.CONFIRMED
        assert attempts[0].confirmation_number == "CONF-99"

    def test_failed_real_submit_records_a_failed_attempt_with_error(self, temp_db, monkeypatch):
        monkeypatch.setitem(submission_engine_module._PARSER_MAP, "greenhouse", _CapableGreenhouseParser)
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
        attempts = temp_db.get_attempts_by_application(submissions[0].application_id)
        assert len(attempts) == 1
        assert attempts[0].result == SubmissionResult.FAILED
        assert attempts[0].error_code == "SUBMIT_REQUEST_FAILED"
        assert "network error" in attempts[0].error_message



def _manual(engine, job_id="workday_1", url="https://acme.wd5.myworkdayjobs.com/job/1", platform="workday", dry_run=False):
    return engine.apply_for_job(
        job_posting_id=job_id, form_url=url, ats_platform=platform, profile=_make_profile(),
        resume_pdf_path="/tmp/resume.pdf", candidate_fit_score=80.0, resume_match_score=70.0,
        mode=ApplicationMode.MANUAL, dry_run=dry_run,
    )


class TestManualModeNeedsNoAtsParsing:
    def test_workday_and_unknown_platforms_can_be_staged_without_fetching(self, temp_db):
        engine = SubmissionEngine(temp_db)
        with patch.object(engine, "_fetch_form_html", side_effect=AssertionError("must not fetch")):
            workday = _manual(engine)
            unknown = _manual(engine, job_id="site_1", url="https://careers.acme.com/1", platform="")
        assert temp_db.get_current_status(workday.application_id) == ApplicationStatus.READY_TO_APPLY
        assert temp_db.get_current_status(unknown.application_id) == ApplicationStatus.READY_TO_APPLY

    def test_manual_mode_rejects_an_invalid_link(self, temp_db):
        with pytest.raises(ValueError, match="valid http"):
            _manual(SubmissionEngine(temp_db), url="not a link")

    def test_preview_then_stage_creates_exactly_one_application(self, temp_db):
        engine = SubmissionEngine(temp_db)
        preview = _manual(engine, dry_run=True)
        assert not preview.application_id
        staged = _manual(engine)
        again = _manual(engine)
        assert again.application_id == staged.application_id
        assert len(temp_db.get_submissions_by_job("workday_1")) == 1
        assert len(temp_db.get_status_history(staged.application_id)) == 1


class TestEveryRealSubmitFailureIsAudited:
    @pytest.mark.parametrize(
        "platform, fetch, code",
        [
            ("nosuchats", None, "UNKNOWN_PLATFORM"),
            ("workday", None, "UNSUPPORTED_PLATFORM"),
            ("greenhouse", Exception("503"), "FORM_FETCH_FAILED"),
            ("greenhouse", "<p>no form</p>", "FORM_EMPTY"),
        ],
    )
    def test_refusal_before_any_post_records_a_failed_attempt(self, temp_db, platform, fetch, code):
        engine = SubmissionEngine(temp_db)
        kwargs = {"side_effect": fetch} if isinstance(fetch, Exception) else {"return_value": fetch}
        with patch.object(engine, "_fetch_form_html", **kwargs):
            with pytest.raises(ValueError):
                engine.apply_for_job(
                    job_posting_id="job_1", form_url="https://example.com/job/1", ats_platform=platform,
                    profile=_make_profile(), resume_pdf_path="/tmp/r.pdf", candidate_fit_score=1.0,
                    resume_match_score=1.0, mode=ApplicationMode.AUTO, dry_run=False,
                )
        (record,) = temp_db.get_submissions_by_job("job_1")
        (attempt,) = temp_db.get_attempts_by_application(record.application_id)
        assert attempt.result == SubmissionResult.FAILED
        assert attempt.error_code == code
        assert temp_db.get_current_status(record.application_id) is None
