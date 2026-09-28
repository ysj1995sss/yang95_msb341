"""Thin status-focused interface over ApplicationDatabase.

Exists so callers that only need status operations (the UI, JobService)
don't need to know about ApplicationDatabase's full submission CRUD surface.
"""

from typing import List, Optional

from resume_tailorer.applications.database import ApplicationDatabase
from resume_tailorer.applications.models import ApplicationStatus, ApplicationTracker, StatusSource


class StatusTracker:
    """Read/update application status through the hiring funnel."""

    def __init__(self, db: ApplicationDatabase):
        self.db = db

    def update_status(
        self,
        application_id: str,
        new_status: ApplicationStatus,
        notes: str = "",
        source: StatusSource = StatusSource.USER,
        confidence: Optional[str] = None,
        evidence: str = "",
    ) -> bool:
        """Add a status-history entry. Always allowed -- a user correction
        must never be blocked by a prior automated (or user) entry, however
        confident (spec 003 Step 23)."""
        return self.db.update_status(application_id, new_status, notes, source, confidence, evidence)

    def record_low_confidence_signal(
        self, application_id: str, new_status: ApplicationStatus, evidence: str, confidence: str = "low",
    ) -> bool:
        """Record an automated status SIGNAL without presenting it as
        certain (spec 003's "optional status automation" -- no email/ATS
        integration exists yet to call this, but the entry point exists so
        one can be added without a schema change). Never called with
        source=USER; that's what update_status is for."""
        return self.db.update_status(
            application_id, new_status, notes="",
            source=StatusSource.SYSTEM, confidence=confidence, evidence=evidence,
        )

    def get_current_status(self, application_id: str) -> Optional[ApplicationStatus]:
        return self.db.get_current_status(application_id)

    def get_status_history(self, application_id: str) -> List[ApplicationTracker]:
        return self.db.get_status_history(application_id)

    def get_applications_by_status(self, status: ApplicationStatus) -> List[ApplicationTracker]:
        return self.db.get_applications_by_status(status)

    def get_all_applications(self) -> List[ApplicationTracker]:
        return self.db.get_all_applications()
