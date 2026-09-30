"""Orchestrates: fetch ATS form -> parse -> fill -> (optionally) submit -> record.

Safety model (see plan Task 4 for full rationale):
- dry_run defaults to True everywhere; a real network submission requires
  the caller to pass dry_run=False explicitly.
- Manual mode never performs a real submission regardless of dry_run,
  since the user applies on the platform's own site themselves.
- Auto mode refuses to submit (raises ValueError) if any required field
  couldn't be confidently filled from the CareerTruthProfile.
- Unsupported platforms (Workday) refuse to submit entirely.
- The audit record is saved BEFORE any real network call, so a failed
  submission still leaves a record of what was attempted.
- An APPLIED status (and the confirmation number) is recorded ONLY after a
  real submission actually succeeds. A dry-run preview or a real submission
  whose POST raises leaves no status at all, so the dashboard never shows a
  false "Applied".
- Manual mode is the one exception to "no automatic status": it records
  READY_TO_APPLY (never APPLIED) immediately, so the user can actually
  track and advance it from the dashboard.
"""

import time
from typing import Optional
from urllib.parse import urlparse

import requests

from resume_tailorer.applications.capabilities import _PARSER_MAP
from resume_tailorer.applications.database import ApplicationDatabase
from resume_tailorer.applications.answer_bank import answers_version as compute_answers_version
from resume_tailorer.applications.answer_bank import apply_answer_bank
from resume_tailorer.applications.form_filler import FormFiller
from resume_tailorer.applications.models import (
    ApplicationMode,
    ApplicationStatus,
    ApplicationSubmission,
    SubmissionAttempt,
    SubmissionResult,
)
from resume_tailorer.models.career_profile import CareerTruthProfile

_MIN_SUBMISSION_INTERVAL_SECONDS = 5.0


class _Refusal(ValueError):
    """A refused real submission, carrying the audit error code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class SubmissionEngine:
    """Orchestrates the parse -> fill -> submit -> record pipeline for one application."""

    def __init__(self, db: ApplicationDatabase):
        self.db = db
        self.form_filler = FormFiller()
        self._last_submission_time = 0.0

    def apply_for_job(
        self,
        job_posting_id: str,
        form_url: str,
        ats_platform: str,
        profile: CareerTruthProfile,
        resume_pdf_path: str,
        candidate_fit_score: float,
        resume_match_score: float,
        mode: ApplicationMode,
        dry_run: bool = True,
        job_snapshot: Optional[dict] = None,
        candidate_fit_snapshot: Optional[dict] = None,
        career_profile_version: str = "",
        answers_version: str = "",
    ) -> ApplicationSubmission:
        """
        Parse the job's application form, fill known fields, optionally
        submit, and always record the attempt.

        Args:
            job_posting_id: The job's ID (format "{source}_{source_id}").
            form_url: URL of the application form to fetch and parse.
            ats_platform: Lowercase platform name ("greenhouse", "lever",
                "ashby", "workday").
            profile: The candidate's verified career data.
            resume_pdf_path: Path to the tailored resume PDF used.
            candidate_fit_score: Score at time of submission.
            resume_match_score: Score at time of submission.
            mode: MANUAL, ASSIST, or AUTO.
            dry_run: If True (default), never performs a real network
                submission — only parses, fills, and records what WOULD
                be submitted. Only Assist/Auto modes ever submit for
                real, and only when this is explicitly False.
            job_snapshot: Immutable snapshot of the job posting at
                submission time (spec 003 Step 22), for the dashboard.
            candidate_fit_snapshot: Immutable snapshot of the candidate
                fit result at submission time.
            career_profile_version: Content hash of the profile used, so a
                later profile edit is detectable without storing the whole
                profile twice.
            answers_version: Ignored; replaced by a hash of the approved
                answers actually used (empty when none were used).

        Returns:
            The recorded ApplicationSubmission (with application_id set).

        Raises:
            ValueError: If the platform is unsupported; if a real submit
                would leave an unfilled required field; if the platform
                doesn't declare final_submission capability (decision 016);
                or if this job already has a confirmed submission on record
                (idempotency).
        """
        submission = ApplicationSubmission(
            job_posting_id=job_posting_id,
            mode=mode,
            resume_used=resume_pdf_path,
            candidate_fit_score=candidate_fit_score,
            resume_match_score=resume_match_score,
            form_fields_submitted={},
            custom_answers={},  # filled from the user's approved answer bank, never drafted
            ats_platform=ats_platform,
            form_url=form_url,
            job_snapshot=job_snapshot or {},
            candidate_fit_snapshot=candidate_fit_snapshot or {},
            career_profile_version=career_profile_version,
            answers_version=answers_version,
        )

        if mode == ApplicationMode.MANUAL:
            return self._stage_manual(submission, dry_run)

        if dry_run:
            # A preview never persists anything; only a real submit is recorded.
            submission.form_fields_submitted = self._prepare_fields(
                submission, profile, real_submit=False
            )[0]
            return submission

        try:
            if self.db.has_confirmed_submission(job_posting_id):
                raise _Refusal(
                    "DUPLICATE_SUBMISSION",
                    f"This job ({job_posting_id}) already has a confirmed submission on record. "
                    f"Refusing to submit again -- check the dashboard if you believe this is wrong.",
                )
            submission.form_fields_submitted, capability = self._prepare_fields(
                submission, profile, real_submit=True
            )
        except Exception as exc:
            self._record_failed_attempt(submission, exc)
            raise

        # Record the attempt BEFORE any real network call, so a failed
        # submission still leaves an audit trail of what was attempted.
        application_id = self.db.save_submission(submission)
        submission.application_id = application_id
        attempt_id = self.db.record_attempt(SubmissionAttempt(
            application_id=application_id, mode=mode, provider=ats_platform,
            result=SubmissionResult.STARTED,
        ))

        # Hard safety gate (spec 003, decision 016): a real submission is
        # never attempted against a platform that has not proven it can
        # actually complete one -- checked as the LAST gate before any
        # real network POST.
        if not capability.final_submission:
            self.db.complete_attempt(
                attempt_id, SubmissionResult.FAILED,
                error_code="UNSUPPORTED_PLATFORM",
                error_message=f"{ats_platform} does not declare final_submission capability",
            )
            raise ValueError(
                f"Cannot submit for real: {ats_platform} does not currently support "
                f"final_submission ({capability.notes or 'not yet verified working against a real form'}). "
                f"Use Manual mode, or Preview (dry run) to see what would be attempted."
            )

        self._respect_rate_limit()
        try:
            confirmation_number = self._submit_to_platform(form_url, submission.form_fields_submitted)
        except Exception as exc:
            self.db.complete_attempt(
                attempt_id, SubmissionResult.FAILED,
                error_code="SUBMIT_REQUEST_FAILED", error_message=str(exc),
            )
            raise

        submission.confirmation_number = confirmation_number
        self.db.update_confirmation_number(application_id, confirmation_number)
        self.db.complete_attempt(attempt_id, SubmissionResult.CONFIRMED, confirmation_number=confirmation_number)
        self.db.update_status(
            application_id,
            ApplicationStatus.APPLIED,
            notes=f"Submitted via {mode.value} mode" + (f", confirmation: {confirmation_number}" if confirmation_number else ""),
        )
        return submission

    def _stage_manual(self, submission: ApplicationSubmission, dry_run: bool) -> ApplicationSubmission:
        """Manual mode needs only a real employer link: the user applies on
        the site themselves, so the ATS page is never fetched or parsed."""
        parsed = urlparse(submission.form_url or "")
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("A valid http(s) application link is required for Manual mode.")
        if dry_run:
            return submission

        for existing in self.db.get_submissions_by_job(submission.job_posting_id):
            if (
                existing.mode == ApplicationMode.MANUAL
                and self.db.get_current_status(existing.application_id) == ApplicationStatus.READY_TO_APPLY
            ):
                return existing

        submission.application_id = self.db.save_submission(submission)
        # READY_TO_APPLY is honest: the user has not applied yet, but the
        # application is now trackable and can be advanced to APPLIED later.
        self.db.update_status(
            submission.application_id,
            ApplicationStatus.READY_TO_APPLY,
            notes="Manual mode: apply via the provided link, then update status here once submitted.",
        )
        return submission

    def _prepare_fields(self, submission: ApplicationSubmission, profile: CareerTruthProfile, real_submit: bool):
        """Parse and fill the ATS form. Returns (prefilled fields, capability)."""
        parser_class = _PARSER_MAP.get(submission.ats_platform)
        if parser_class is None:
            raise _Refusal("UNKNOWN_PLATFORM", f"Unknown ATS platform: {submission.ats_platform}")
        parser = parser_class()
        if not parser.is_supported():
            raise _Refusal(
                "UNSUPPORTED_PLATFORM",
                f"{submission.ats_platform} is not supported for automated form parsing "
                f"(its application forms require a real browser to render).",
            )
        try:
            form_html = self._fetch_form_html(submission.form_url)
        except Exception as exc:
            raise _Refusal("FORM_FETCH_FAILED", str(exc) or exc.__class__.__name__) from exc
        filled_fields = self.form_filler.fill_form(parser.parse_form(form_html), profile)
        filled_fields, custom, unanswered = apply_answer_bank(filled_fields, self.db.get_answers())
        submission.custom_answers = custom
        submission.answers_version = compute_answers_version(custom)
        submission.unanswered_questions = unanswered
        if not filled_fields:
            raise _Refusal(
                "FORM_EMPTY",
                "could not parse any application fields from the ATS page; "
                "refusing to submit an empty form.",
            )
        unfilled_required = [f for f in filled_fields if f.required and not f.prefilled]
        if real_submit and unfilled_required:
            names = ", ".join(f.field_name for f in unfilled_required)
            raise _Refusal(
                "REQUIRED_FIELDS_UNFILLED",
                f"Cannot submit: required field(s) [{names}] could not be "
                f"confidently filled from the candidate profile.",
            )
        return {f.field_name: f.value for f in filled_fields if f.prefilled}, parser.get_capability()

    def _record_failed_attempt(self, submission: ApplicationSubmission, exc: Exception) -> None:
        """Audit a real-submit request that was refused or failed before any POST.
        The record has no status, so it never appears as an application."""
        submission.application_id = self.db.save_submission(submission)
        attempt_id = self.db.record_attempt(SubmissionAttempt(
            application_id=submission.application_id, mode=submission.mode,
            provider=submission.ats_platform, result=SubmissionResult.STARTED,
        ))
        self.db.complete_attempt(
            attempt_id, SubmissionResult.FAILED,
            error_code=getattr(exc, "code", "SUBMIT_PREPARATION_FAILED"),
            error_message=str(exc),
        )

    def _fetch_form_html(self, form_url: str) -> str:
        """Fetch the raw HTML of the application form page."""
        response = requests.get(form_url, timeout=10)
        response.raise_for_status()
        return response.text

    def _submit_to_platform(self, form_url: str, form_fields: dict) -> str:
        """Perform the real POST submission to the ATS platform.

        Only ever called when dry_run=False and mode is Assist or Auto.
        Returns a confirmation identifier if the platform provides one,
        otherwise an empty string.
        """
        response = requests.post(form_url, data=form_fields, timeout=15)
        response.raise_for_status()
        return response.headers.get("X-Confirmation-Id", "")

    def _respect_rate_limit(self) -> None:
        """Enforce a minimum interval between real submissions."""
        elapsed = time.time() - self._last_submission_time
        if elapsed < _MIN_SUBMISSION_INTERVAL_SECONDS:
            time.sleep(_MIN_SUBMISSION_INTERVAL_SECONDS - elapsed)
        self._last_submission_time = time.time()
