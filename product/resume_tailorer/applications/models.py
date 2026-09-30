"""Domain models for job application submission and status tracking."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class ApplicationMode(Enum):
    """How an application gets submitted."""
    MANUAL = "manual"
    ASSIST = "assist"
    AUTO = "auto"


class ApplicationStatus(Enum):
    """Where an application sits in the hiring funnel."""
    DISCOVERED = "discovered"
    INTERESTED = "interested"
    PREPARING = "preparing"
    READY_TO_APPLY = "ready_to_apply"
    APPLIED = "applied"
    ASSESSMENT = "assessment"
    RECRUITER_SCREEN = "recruiter_screen"
    INTERVIEW = "interview"
    FINAL_INTERVIEW = "final_interview"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    UNKNOWN = "unknown"


class StatusSource(Enum):
    """Where a status-history entry's value came from -- see StatusEvent."""
    USER = "user"
    EMAIL_INTEGRATION = "email_integration"
    ATS_INTEGRATION = "ats_integration"
    SYSTEM = "system"


class SubmissionResult(Enum):
    """Outcome of one submission attempt (spec 003 Step 22).

    Distinct from ApplicationStatus: this tracks whether ONE attempt to
    submit succeeded, not where the application sits in the hiring funnel.
    A SUBMITTED_CONFIRMED result is what's allowed to advance
    ApplicationStatus to APPLIED -- clicking a submit button alone never
    does (spec 003, decision 016).
    """
    STARTED = "submission_started"
    PENDING = "submission_pending"
    CONFIRMED = "submitted_confirmed"
    FAILED = "submission_failed"
    MANUALLY_CONFIRMED = "manually_confirmed"


@dataclass
class FormField:
    """A single field on an ATS application form."""
    field_name: str
    field_type: str  # "text", "email", "phone", "date", "checkbox", "select", "textarea", "file"
    required: bool = False
    value: str = ""
    prefilled: bool = False
    label: str = ""  # the question as the applicant sees it, when the form provides one


@dataclass(frozen=True)
class ATSCapability:
    """What one ATS platform's integration can actually do (spec 003 Step 21).

    Replaces a bare is_supported() bool -- a platform can support Manual
    hand-off while NOT supporting real Assist/Auto submission, and the two
    must never be conflated. final_submission=False is the hard gate
    SubmissionEngine checks before ever attempting a real POST; see
    decision 016 for why every platform currently has it False (decision
    012's live finding that real ATS forms are JS-rendered SPAs with no
    server-side form fields a static HTTP fetch can see).
    """
    platform: str
    manual_supported: bool = True
    assist_supported: bool = False
    auto_supported: bool = False
    resume_upload: bool = False
    profile_prefill: bool = False
    custom_questions: bool = False
    final_submission: bool = False
    status_fetch: bool = False
    notes: str = ""


@dataclass
class ApplicationSubmission:
    """A full audit-trail record of one application submission attempt.

    job_snapshot/candidate_fit_snapshot/career_profile_version/
    answers_version are immutable snapshots captured AT SUBMISSION TIME --
    the dashboard must show what was true when the user applied, not
    whatever the live job/profile look like now (same principle as
    TailoringRun.profile_snapshot_json from Steps 16-20). All snapshot
    fields default empty so existing callers/tests that don't pass them
    keep working unchanged.
    """
    job_posting_id: str
    mode: ApplicationMode
    resume_used: str
    candidate_fit_score: Optional[float]
    resume_match_score: float
    form_fields_submitted: Dict[str, str]
    custom_answers: Dict[str, str]
    ats_platform: str
    form_url: str
    submission_timestamp: datetime = field(default_factory=datetime.now)
    confirmation_number: str = ""
    application_id: str = ""  # assigned by ApplicationDatabase.save_submission()
    job_snapshot: Dict = field(default_factory=dict)
    candidate_fit_snapshot: Dict = field(default_factory=dict)
    career_profile_version: str = ""
    answers_version: str = ""
    # Questions the answer bank could not answer; shown in previews, never persisted.
    unanswered_questions: List[str] = field(default_factory=list)
    next_action: str = ""
    next_action_due: Optional[str] = None  # ISO date string; only ever user-confirmed, never invented
    next_action_notes: str = ""


@dataclass
class SubmissionAttempt:
    """One attempt to submit an application -- separate from the canonical
    ApplicationSubmission record (spec 003 Step 22 / "Submission Attempts").
    Tracked even when the attempt fails before a real network call (e.g.
    the form fetch itself raising), so a failed attempt always leaves an
    audit trail -- the previous single-table design left NO record at all
    for a failure that happened before save_submission() was reached.
    """
    application_id: str
    mode: ApplicationMode
    provider: str  # ats_platform
    result: SubmissionResult
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error_code: str = ""
    error_message: str = ""
    confirmation_number: str = ""
    confirmation_url: str = ""
    attempt_id: str = ""  # assigned by ApplicationDatabase.record_attempt()


@dataclass
class ApplicationTracker:
    """One status-history entry for an application.

    source/confidence/evidence exist so a future email/ATS integration has
    somewhere to write without a schema change (spec 003's "optional status
    automation") -- with no integration built yet, every entry defaults to
    USER with no confidence/evidence, which is the honest current state,
    not a placeholder for something that already works.
    """
    application_id: str
    job_posting_id: str
    status: ApplicationStatus
    notes: str = ""
    status_updated: datetime = field(default_factory=datetime.now)
    source: StatusSource = StatusSource.USER
    confidence: Optional[str] = None  # e.g. "high"/"medium"/"low"; only meaningful for non-USER sources
    evidence: str = ""  # e.g. an email subject line or ATS event id a future integration observed
