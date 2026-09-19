"""Domain models for job application submission and status tracking."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict


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
    RECRUITER_SCREEN = "recruiter_screen"
    INTERVIEW = "interview"
    FINAL_INTERVIEW = "final_interview"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


@dataclass
class FormField:
    """A single field on an ATS application form."""
    field_name: str
    field_type: str  # "text", "email", "phone", "date", "checkbox", "select", "textarea", "file"
    required: bool = False
    value: str = ""
    prefilled: bool = False


@dataclass
class ApplicationSubmission:
    """A full audit-trail record of one application submission attempt."""
    job_posting_id: str
    mode: ApplicationMode
    resume_used: str
    candidate_fit_score: float
    resume_match_score: float
    form_fields_submitted: Dict[str, str]
    custom_answers: Dict[str, str]
    ats_platform: str
    form_url: str
    submission_timestamp: datetime = field(default_factory=datetime.now)
    confirmation_number: str = ""
    application_id: str = ""  # assigned by ApplicationDatabase.save_submission()


@dataclass
class ApplicationTracker:
    """One status-history entry for an application."""
    application_id: str
    job_posting_id: str
    status: ApplicationStatus
    notes: str = ""
    status_updated: datetime = field(default_factory=datetime.now)
