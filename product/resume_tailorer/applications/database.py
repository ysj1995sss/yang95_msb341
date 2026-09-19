"""SQLite database for application submissions and status history."""

import json
import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional

from resume_tailorer.applications.models import (
    ApplicationMode,
    ApplicationStatus,
    ApplicationSubmission,
    ApplicationTracker,
)


class ApplicationDatabase:
    """SQLite-backed audit trail for application submissions and status."""

    def __init__(self, db_path: str = "applications.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def create_tables(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                application_id TEXT PRIMARY KEY,
                job_posting_id TEXT NOT NULL,
                mode TEXT NOT NULL,
                resume_used TEXT,
                candidate_fit_score REAL,
                resume_match_score REAL,
                form_fields_submitted TEXT,
                custom_answers TEXT,
                ats_platform TEXT,
                form_url TEXT,
                submission_timestamp TIMESTAMP,
                confirmation_number TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS application_status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id TEXT NOT NULL,
                job_posting_id TEXT NOT NULL,
                status TEXT NOT NULL,
                notes TEXT,
                status_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(application_id) REFERENCES applications(application_id)
            )
        """)
        self.conn.commit()

    def save_submission(self, submission: ApplicationSubmission) -> str:
        """Record what was (or would be) submitted.

        This records the audit row ONLY. It deliberately does not write a
        status-history row: a submission may be a dry-run preview, or a real
        submission whose POST later fails, and neither is an APPLIED status.
        Callers use update_status() once a real submission has succeeded.
        """
        application_id = f"app_{uuid.uuid4().hex[:12]}"
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO applications (
                application_id, job_posting_id, mode, resume_used,
                candidate_fit_score, resume_match_score,
                form_fields_submitted, custom_answers,
                ats_platform, form_url, submission_timestamp, confirmation_number
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            application_id,
            submission.job_posting_id,
            submission.mode.value,
            submission.resume_used,
            submission.candidate_fit_score,
            submission.resume_match_score,
            json.dumps(submission.form_fields_submitted),
            json.dumps(submission.custom_answers),
            submission.ats_platform,
            submission.form_url,
            submission.submission_timestamp.isoformat(),
            submission.confirmation_number,
        ))

        self.conn.commit()
        return application_id

    def update_confirmation_number(self, application_id: str, confirmation_number: str) -> bool:
        """Write back a confirmation number after a successful real submission.

        Args:
            application_id: The application to update.
            confirmation_number: The confirmation identifier returned by
                the ATS platform.

        Returns:
            True if the application existed and was updated, False otherwise.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT application_id FROM applications WHERE application_id = ?", (application_id,))
        if not cursor.fetchone():
            return False

        cursor.execute(
            "UPDATE applications SET confirmation_number = ? WHERE application_id = ?",
            (confirmation_number, application_id),
        )
        self.conn.commit()
        return True

    def get_submission(self, application_id: str) -> Optional[ApplicationSubmission]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM applications WHERE application_id = ?", (application_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_submission(row)

    def get_submissions_by_job(self, job_posting_id: str) -> List[ApplicationSubmission]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM applications WHERE job_posting_id = ?", (job_posting_id,))
        return [self._row_to_submission(row) for row in cursor.fetchall()]

    def update_status(self, application_id: str, status: ApplicationStatus, notes: str = "") -> bool:
        cursor = self.conn.cursor()
        cursor.execute("SELECT job_posting_id FROM applications WHERE application_id = ?", (application_id,))
        row = cursor.fetchone()
        if not row:
            return False

        cursor.execute("""
            INSERT INTO application_status_history (application_id, job_posting_id, status, notes)
            VALUES (?, ?, ?, ?)
        """, (application_id, row["job_posting_id"], status.value, notes))
        self.conn.commit()
        return True

    def get_status_history(self, application_id: str) -> List[ApplicationTracker]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM application_status_history
            WHERE application_id = ?
            ORDER BY status_updated ASC, id ASC
        """, (application_id,))
        return [self._row_to_tracker(row) for row in cursor.fetchall()]

    def get_current_status(self, application_id: str) -> Optional[ApplicationStatus]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT status FROM application_status_history
            WHERE application_id = ?
            ORDER BY status_updated DESC, id DESC
            LIMIT 1
        """, (application_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return ApplicationStatus(row["status"])

    def get_applications_by_status(self, status: ApplicationStatus) -> List[ApplicationTracker]:
        all_current = self._get_all_current_trackers()
        return [t for t in all_current if t.status == status]

    def get_all_applications(self) -> List[ApplicationTracker]:
        return self._get_all_current_trackers()

    def _get_all_current_trackers(self) -> List[ApplicationTracker]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT h.*
            FROM application_status_history h
            INNER JOIN (
                SELECT application_id, MAX(id) AS max_id
                FROM application_status_history
                GROUP BY application_id
            ) latest ON h.application_id = latest.application_id AND h.id = latest.max_id
        """)
        return [self._row_to_tracker(row) for row in cursor.fetchall()]

    def _row_to_submission(self, row) -> ApplicationSubmission:
        return ApplicationSubmission(
            job_posting_id=row["job_posting_id"],
            mode=ApplicationMode(row["mode"]),
            resume_used=row["resume_used"],
            candidate_fit_score=row["candidate_fit_score"],
            resume_match_score=row["resume_match_score"],
            form_fields_submitted=json.loads(row["form_fields_submitted"]) if row["form_fields_submitted"] else {},
            custom_answers=json.loads(row["custom_answers"]) if row["custom_answers"] else {},
            ats_platform=row["ats_platform"],
            form_url=row["form_url"],
            submission_timestamp=datetime.fromisoformat(row["submission_timestamp"]),
            confirmation_number=row["confirmation_number"] or "",
            application_id=row["application_id"],
        )

    def _row_to_tracker(self, row) -> ApplicationTracker:
        return ApplicationTracker(
            application_id=row["application_id"],
            job_posting_id=row["job_posting_id"],
            status=ApplicationStatus(row["status"]),
            notes=row["notes"] or "",
            status_updated=datetime.fromisoformat(row["status_updated"])
            if isinstance(row["status_updated"], str) else row["status_updated"],
        )

    def close(self) -> None:
        self.conn.close()
