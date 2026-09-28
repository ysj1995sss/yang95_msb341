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
    StatusSource,
    SubmissionAttempt,
    SubmissionResult,
)

# (column, SQL definition) added after the original schema -- guarded by an
# existence check in _apply_additive_migrations so a pre-existing local
# applications.db file (created before this column set existed) still
# works, matching apps/api/app/migrations.py's additive-only pattern.
_ADDITIVE_APPLICATION_COLUMNS: list[tuple[str, str]] = [
    ("job_snapshot", "TEXT DEFAULT '{}'"),
    ("candidate_fit_snapshot", "TEXT DEFAULT '{}'"),
    ("career_profile_version", "TEXT DEFAULT ''"),
    ("answers_version", "TEXT DEFAULT ''"),
    ("next_action", "TEXT DEFAULT ''"),
    ("next_action_due", "TEXT DEFAULT NULL"),
    ("next_action_notes", "TEXT DEFAULT ''"),
]
_ADDITIVE_STATUS_HISTORY_COLUMNS: list[tuple[str, str]] = [
    ("source", "TEXT DEFAULT 'user'"),
    ("confidence", "TEXT DEFAULT NULL"),
    ("evidence", "TEXT DEFAULT ''"),
]


class ApplicationDatabase:
    """SQLite-backed audit trail for application submissions and status."""

    def __init__(self, db_path: str = "applications.db"):
        self.db_path = db_path
        # check_same_thread=False: same live thread-affinity bug found in
        # JobDatabase (job_search/database.py) -- Streamlit can rerun a
        # session's script on a different worker thread than the one that
        # created a connection cached in st.session_state. Safe here since
        # Streamlit runs one rerun at a time per session.
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS submission_attempts (
                attempt_id TEXT PRIMARY KEY,
                application_id TEXT NOT NULL,
                mode TEXT NOT NULL,
                provider TEXT NOT NULL,
                result TEXT NOT NULL,
                started_at TIMESTAMP NOT NULL,
                completed_at TIMESTAMP,
                error_code TEXT,
                error_message TEXT,
                confirmation_number TEXT,
                confirmation_url TEXT,
                FOREIGN KEY(application_id) REFERENCES applications(application_id)
            )
        """)
        self.conn.commit()
        self._apply_additive_migrations()

    def _apply_additive_migrations(self) -> None:
        """Add columns to a pre-existing applications.db that predates
        them -- never drops/renames/alters an existing column, matching
        apps/api/app/migrations.py's established pattern for this repo."""
        cursor = self.conn.cursor()
        for table, columns in (
            ("applications", _ADDITIVE_APPLICATION_COLUMNS),
            ("application_status_history", _ADDITIVE_STATUS_HISTORY_COLUMNS),
        ):
            existing = {row["name"] for row in cursor.execute(f"PRAGMA table_info({table})")}
            for column, definition in columns:
                if column not in existing:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
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
                ats_platform, form_url, submission_timestamp, confirmation_number,
                job_snapshot, candidate_fit_snapshot, career_profile_version, answers_version,
                next_action, next_action_due, next_action_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            json.dumps(submission.job_snapshot),
            json.dumps(submission.candidate_fit_snapshot),
            submission.career_profile_version,
            submission.answers_version,
            submission.next_action,
            submission.next_action_due,
            submission.next_action_notes,
        ))

        self.conn.commit()
        return application_id

    def has_confirmed_submission(self, job_posting_id: str) -> bool:
        """Idempotency check (spec 003 Step 22): has this job already been
        REALLY submitted (a confirmed or manually-confirmed attempt)?
        Dry-run previews never create a submission_attempts row, so they
        never trip this check -- only a real, evidenced submission does."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 1 FROM submission_attempts sa
            JOIN applications a ON a.application_id = sa.application_id
            WHERE a.job_posting_id = ? AND sa.result IN (?, ?)
            LIMIT 1
        """, (job_posting_id, SubmissionResult.CONFIRMED.value, SubmissionResult.MANUALLY_CONFIRMED.value))
        return cursor.fetchone() is not None

    def record_attempt(self, attempt: SubmissionAttempt) -> str:
        """Record a submission attempt -- called for EVERY attempt,
        including ones that fail before any real network call, so a failed
        attempt always leaves an audit trail (spec 003 Step 22)."""
        attempt_id = f"att_{uuid.uuid4().hex[:12]}"
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO submission_attempts (
                attempt_id, application_id, mode, provider, result,
                started_at, completed_at, error_code, error_message,
                confirmation_number, confirmation_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            attempt_id,
            attempt.application_id,
            attempt.mode.value,
            attempt.provider,
            attempt.result.value,
            attempt.started_at.isoformat(),
            attempt.completed_at.isoformat() if attempt.completed_at else None,
            attempt.error_code,
            attempt.error_message,
            attempt.confirmation_number,
            attempt.confirmation_url,
        ))
        self.conn.commit()
        return attempt_id

    def complete_attempt(
        self,
        attempt_id: str,
        result: SubmissionResult,
        error_code: str = "",
        error_message: str = "",
        confirmation_number: str = "",
        confirmation_url: str = "",
    ) -> bool:
        """Update an attempt with its final outcome."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT attempt_id FROM submission_attempts WHERE attempt_id = ?", (attempt_id,))
        if not cursor.fetchone():
            return False
        cursor.execute("""
            UPDATE submission_attempts
            SET result = ?, completed_at = ?, error_code = ?, error_message = ?,
                confirmation_number = ?, confirmation_url = ?
            WHERE attempt_id = ?
        """, (
            result.value, datetime.now().isoformat(), error_code, error_message,
            confirmation_number, confirmation_url, attempt_id,
        ))
        self.conn.commit()
        return True

    def get_attempts_by_application(self, application_id: str) -> List[SubmissionAttempt]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM submission_attempts WHERE application_id = ? ORDER BY started_at ASC
        """, (application_id,))
        return [self._row_to_attempt(row) for row in cursor.fetchall()]

    def update_next_action(
        self, application_id: str, next_action: str, next_action_due: Optional[str] = None, notes: str = ""
    ) -> bool:
        """Update an application's next-action fields. next_action_due is
        only ever what the caller (a user-confirmed value) passes in --
        this method never invents or defaults a due date."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT application_id FROM applications WHERE application_id = ?", (application_id,))
        if not cursor.fetchone():
            return False
        cursor.execute("""
            UPDATE applications SET next_action = ?, next_action_due = ?, next_action_notes = ?
            WHERE application_id = ?
        """, (next_action, next_action_due, notes, application_id))
        self.conn.commit()
        return True

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

    def update_status(
        self,
        application_id: str,
        status: ApplicationStatus,
        notes: str = "",
        source: StatusSource = StatusSource.USER,
        confidence: Optional[str] = None,
        evidence: str = "",
    ) -> bool:
        """Add a new status-history entry. Always allowed regardless of the
        current status or its source -- a user correction must never be
        blocked by a prior automated (or even prior user) entry (spec 003
        Step 23's "user can always correct status")."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT job_posting_id FROM applications WHERE application_id = ?", (application_id,))
        row = cursor.fetchone()
        if not row:
            return False

        cursor.execute("""
            INSERT INTO application_status_history
                (application_id, job_posting_id, status, notes, source, confidence, evidence)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (application_id, row["job_posting_id"], status.value, notes, source.value, confidence, evidence))
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

    @staticmethod
    def _get(row, key, default=None):
        """Safe column access for a row that may predate an additive column."""
        return row[key] if key in row.keys() else default

    def _row_to_submission(self, row) -> ApplicationSubmission:
        get = self._get
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
            job_snapshot=json.loads(get(row, "job_snapshot") or "{}"),
            candidate_fit_snapshot=json.loads(get(row, "candidate_fit_snapshot") or "{}"),
            career_profile_version=get(row, "career_profile_version") or "",
            answers_version=get(row, "answers_version") or "",
            next_action=get(row, "next_action") or "",
            next_action_due=get(row, "next_action_due"),
            next_action_notes=get(row, "next_action_notes") or "",
        )

    def _row_to_tracker(self, row) -> ApplicationTracker:
        return ApplicationTracker(
            application_id=row["application_id"],
            job_posting_id=row["job_posting_id"],
            status=ApplicationStatus(row["status"]),
            notes=row["notes"] or "",
            status_updated=datetime.fromisoformat(row["status_updated"])
            if isinstance(row["status_updated"], str) else row["status_updated"],
            source=StatusSource(self._get(row, "source") or "user"),
            confidence=self._get(row, "confidence"),
            evidence=self._get(row, "evidence") or "",
        )

    def _row_to_attempt(self, row) -> SubmissionAttempt:
        return SubmissionAttempt(
            attempt_id=row["attempt_id"],
            application_id=row["application_id"],
            mode=ApplicationMode(row["mode"]),
            provider=row["provider"],
            result=SubmissionResult(row["result"]),
            started_at=datetime.fromisoformat(row["started_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            error_code=row["error_code"] or "",
            error_message=row["error_message"] or "",
            confirmation_number=row["confirmation_number"] or "",
            confirmation_url=row["confirmation_url"] or "",
        )

    def close(self) -> None:
        self.conn.close()
