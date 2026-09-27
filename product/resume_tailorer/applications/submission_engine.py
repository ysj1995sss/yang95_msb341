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

import requests

from resume_tailorer.applications.ats_parsers.greenhouse_parser import GreenhouseParser
from resume_tailorer.applications.ats_parsers.lever_parser import LeverParser
from resume_tailorer.applications.ats_parsers.ashby_parser import AshbyParser
from resume_tailorer.applications.ats_parsers.workday_parser import WorkdayParser
from resume_tailorer.applications.database import ApplicationDatabase
from resume_tailorer.applications.form_filler import FormFiller
from resume_tailorer.applications.models import (
    ApplicationMode,
    ApplicationStatus,
    ApplicationSubmission,
)
from resume_tailorer.models.career_profile import CareerTruthProfile

_PARSER_MAP = {
    "greenhouse": GreenhouseParser,
    "lever": LeverParser,
    "ashby": AshbyParser,
    "workday": WorkdayParser,
}

_MIN_SUBMISSION_INTERVAL_SECONDS = 5.0


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

        Returns:
            The recorded ApplicationSubmission (with application_id set).

        Raises:
            ValueError: If the platform is unsupported, or if Auto mode
                would submit with an unfilled required field.
        """
        parser_class = _PARSER_MAP.get(ats_platform)
        if parser_class is None:
            raise ValueError(f"Unknown ATS platform: {ats_platform}")

        parser = parser_class()
        if not parser.is_supported():
            raise ValueError(
                f"{ats_platform} is not supported for automated form parsing "
                f"(its application forms require a real browser to render)."
            )

        form_html = self._fetch_form_html(form_url)
        fields = parser.parse_form(form_html)
        filled_fields = self.form_filler.fill_form(fields, profile)

        if mode != ApplicationMode.MANUAL and not filled_fields:
            raise ValueError(
                "could not parse any application fields from the ATS page; "
                "refusing to submit an empty form."
            )

        unfilled_required = [f for f in filled_fields if f.required and not f.prefilled]
        real_submit = (not dry_run) and (mode != ApplicationMode.MANUAL)

        if real_submit and unfilled_required:
            names = ", ".join(f.field_name for f in unfilled_required)
            raise ValueError(
                f"Cannot submit: required field(s) [{names}] could not be "
                f"confidently filled from the candidate profile."
            )

        form_fields_submitted = {f.field_name: f.value for f in filled_fields if f.prefilled}

        submission = ApplicationSubmission(
            job_posting_id=job_posting_id,
            mode=mode,
            resume_used=resume_pdf_path,
            candidate_fit_score=candidate_fit_score,
            resume_match_score=resume_match_score,
            form_fields_submitted=form_fields_submitted,
            custom_answers={},  # AI-drafted custom answers are out of scope for this MVP
            ats_platform=ats_platform,
            form_url=form_url,
        )

        # Record the attempt BEFORE any real network call, so a failed
        # submission still leaves an audit trail of what was attempted.
        application_id = self.db.save_submission(submission)
        submission.application_id = application_id

        # Manual mode never goes through the submit branch below, so without an
        # explicit status here it would never appear in the dashboard at all
        # (the dashboard is driven by the status_history table). READY_TO_APPLY
        # is honest: the user has not applied yet, but the application is now
        # trackable and can be advanced to APPLIED from the dashboard.
        if mode == ApplicationMode.MANUAL:
            self.db.update_status(
                application_id,
                ApplicationStatus.READY_TO_APPLY,
                notes="Manual mode: apply via the provided link, then update status here once submitted.",
            )

        should_actually_submit = (not dry_run) and (mode != ApplicationMode.MANUAL)
        if should_actually_submit:
            self._respect_rate_limit()
            confirmation_number = self._submit_to_platform(form_url, form_fields_submitted)
            submission.confirmation_number = confirmation_number
            self.db.update_confirmation_number(application_id, confirmation_number)
            self.db.update_status(
                application_id,
                ApplicationStatus.APPLIED,
                notes=f"Submitted via {mode.value} mode" + (f", confirmation: {confirmation_number}" if confirmation_number else ""),
            )

        return submission

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
