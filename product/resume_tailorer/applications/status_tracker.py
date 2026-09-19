"""Thin status-focused interface over ApplicationDatabase.

Exists so callers that only need status operations (the UI, JobService)
don't need to know about ApplicationDatabase's full submission CRUD surface.
"""

from typing import List, Optional

from resume_tailorer.applications.database import ApplicationDatabase
from resume_tailorer.applications.models import ApplicationStatus, ApplicationTracker


class StatusTracker:
    """Read/update application status through the hiring funnel."""

    def __init__(self, db: ApplicationDatabase):
        self.db = db

    def update_status(self, application_id: str, new_status: ApplicationStatus, notes: str = "") -> bool:
        return self.db.update_status(application_id, new_status, notes)

    def get_current_status(self, application_id: str) -> Optional[ApplicationStatus]:
        return self.db.get_current_status(application_id)

    def get_status_history(self, application_id: str) -> List[ApplicationTracker]:
        return self.db.get_status_history(application_id)

    def get_applications_by_status(self, status: ApplicationStatus) -> List[ApplicationTracker]:
        return self.db.get_applications_by_status(status)

    def get_all_applications(self) -> List[ApplicationTracker]:
        return self.db.get_all_applications()
