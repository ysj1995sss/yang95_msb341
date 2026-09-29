"""SQLite database layer for job postings, user selections, and search goals."""

import sqlite3
import json
from datetime import datetime
from typing import Optional, List
from resume_tailorer.job_search.models import JobSource, SearchGoals, JobPosting, UserSelection


class JobDatabase:
    """Manages SQLite persistence for job postings and user selections."""

    def __init__(self, db_path: str = "job_search.db"):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        # check_same_thread=False: found live (2026-09-24) that Streamlit can
        # run script reruns for the same session on a different worker
        # thread than the one that created this connection (cached in
        # st.session_state across reruns) -- the sqlite3 default raised
        # "SQLite objects created in a thread can only be used in that same
        # thread." Safe here because Streamlit executes one rerun at a time
        # per session; there's no genuine concurrent access to guard against.
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row

    def create_tables(self) -> None:
        """Initialize SQLite schema with job_postings, user_selections, and search_goals tables."""
        cursor = self.connection.cursor()

        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")

        # Create job_postings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_postings (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                source_id TEXT NOT NULL,
                company TEXT,
                title TEXT,
                location TEXT,
                description TEXT,
                posted_date TIMESTAMP,
                application_deadline TIMESTAMP,
                salary_min INTEGER,
                salary_max INTEGER,
                experience_required TEXT,
                education_required TEXT,
                sponsorship_available BOOLEAN,
                work_mode TEXT,
                url TEXT,
                ats_platform TEXT,
                raw_json TEXT,
                alternative_sources TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source, source_id)
            )
        """)

        # Migration guard: legacy databases created before alternative_sources
        # existed won't get the column from CREATE TABLE IF NOT EXISTS.
        cursor.execute("PRAGMA table_info(job_postings)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        if "alternative_sources" not in existing_columns:
            cursor.execute("ALTER TABLE job_postings ADD COLUMN alternative_sources TEXT")

        # Create user_selections table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_selections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_posting_id TEXT NOT NULL,
                action TEXT NOT NULL,
                user_notes TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_posting_id) REFERENCES job_postings(id)
            )
        """)

        # Create search_goals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_title TEXT,
                industries TEXT,
                location TEXT,
                min_salary INTEGER,
                max_salary INTEGER,
                remote_preference TEXT,
                sponsorship_required BOOLEAN,
                experience_level TEXT,
                company_size TEXT,
                target_companies TEXT,
                exclude_companies TEXT,
                employment_type TEXT,
                relocation_willing BOOLEAN,
                goal_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Migration guard: add goal_name column if it doesn't exist
        cursor.execute("PRAGMA table_info(search_goals)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        if "goal_name" not in existing_columns:
            cursor.execute("ALTER TABLE search_goals ADD COLUMN goal_name TEXT")

        self.connection.commit()

    def save_job_posting(self, job: JobPosting) -> str:
        """Save a job posting to the database.

        Args:
            job: JobPosting object to save

        Returns:
            job_id in format "{source}_{source_id}"
        """
        job_id = f"{job.source.value}_{job.source_id}"

        # Serialize raw_json to JSON string
        raw_json_str = json.dumps(job.raw_json) if job.raw_json else None

        # Serialize alternative_sources to JSON string
        alternative_sources_str = (
            json.dumps(job.alternative_sources) if job.alternative_sources else None
        )

        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO job_postings
            (id, source, source_id, company, title, location, description,
             posted_date, application_deadline, salary_min, salary_max,
             experience_required, education_required, sponsorship_available,
             work_mode, url, ats_platform, raw_json, alternative_sources)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_id,
            job.source.value,
            job.source_id,
            job.company,
            job.title,
            job.location,
            job.description,
            job.posted_date.isoformat() if job.posted_date else None,
            job.application_deadline.isoformat() if job.application_deadline else None,
            job.salary_min,
            job.salary_max,
            job.experience_required,
            job.education_required,
            job.sponsorship_available,
            job.work_mode,
            job.url,
            job.ats_platform,
            raw_json_str,
            alternative_sources_str
        ))

        self.connection.commit()
        return job_id

    def get_job_posting(self, job_id: str) -> Optional[JobPosting]:
        """Retrieve a job posting by ID.

        Args:
            job_id: Job ID in format "{source}_{source_id}"

        Returns:
            JobPosting object or None if not found
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM job_postings WHERE id = ?", (job_id,))
        row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_job_posting(row)

    def search_jobs(self, goals: SearchGoals) -> List[JobPosting]:
        """Search for jobs matching the given goals.

        Args:
            goals: SearchGoals object with search criteria

        Returns:
            List of JobPosting objects matching the criteria
        """
        cursor = self.connection.cursor()

        # Build WHERE clause dynamically
        where_clauses = []
        params = []

        # Filter by job title (LIKE)
        if goals.job_title:
            where_clauses.append("title LIKE ?")
            params.append(f"%{goals.job_title}%")

        # Filter by salary range
        # salary_max >= min_salary (job's max is at least as much as our minimum)
        if goals.min_salary:
            where_clauses.append("(salary_max IS NULL OR salary_max >= ?)")
            params.append(goals.min_salary)

        # salary_min <= max_salary (job's min is at most as much as our maximum)
        if goals.max_salary:
            where_clauses.append("(salary_min IS NULL OR salary_min <= ?)")
            params.append(goals.max_salary)

        # Filter by location (LIKE)
        if goals.location:
            where_clauses.append("location LIKE ?")
            params.append(f"%{goals.location}%")

        # Filter by work mode if not "any"
        if goals.remote_preference and goals.remote_preference != "any":
            # Real postings from sources that don't expose work mode store
            # "Unknown" (never fabricated) — treat that as a pass rather than
            # silently hiding every real job whenever a preference is set.
            where_clauses.append(
                "(work_mode LIKE ? OR work_mode IS NULL OR work_mode = 'Unknown')"
            )
            params.append(f"%{goals.remote_preference}%")

        # Filter by sponsorship if required
        if goals.sponsorship_required:
            where_clauses.append("sponsorship_available = ?")
            params.append(True)

        # Filter by target companies (if specified, include only these)
        if goals.target_companies:
            placeholders = ",".join("?" * len(goals.target_companies))
            where_clauses.append(f"company IN ({placeholders})")
            params.extend(goals.target_companies)

        # Filter by excluded companies
        if goals.exclude_companies:
            placeholders = ",".join("?" * len(goals.exclude_companies))
            where_clauses.append(f"company NOT IN ({placeholders})")
            params.extend(goals.exclude_companies)

        # Build the query
        query = "SELECT * FROM job_postings"
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        return [self._row_to_job_posting(row) for row in rows]

    def record_user_selection(self, selection: UserSelection) -> bool:
        """Record a user's action on a job posting.

        Args:
            selection: UserSelection object with user action

        Returns:
            True on success, False on error
        """
        from resume_tailorer.job_search.models import (
            canonicalize_triage_action,
            triage_storage_value,
        )

        try:
            action = triage_storage_value(canonicalize_triage_action(selection.action))
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO user_selections
                (job_posting_id, action, user_notes, timestamp)
                VALUES (?, ?, ?, ?)
            """, (
                selection.job_posting_id,
                action,
                selection.user_notes,
                selection.timestamp.isoformat() if isinstance(selection.timestamp, datetime) else selection.timestamp
            ))
            self.connection.commit()
            return True
        except Exception:
            return False

    def get_user_selections(self, job_id: str) -> List[UserSelection]:
        """Retrieve all user selections for a job.

        Args:
            job_id: Job ID in format "{source}_{source_id}"

        Returns:
            List of UserSelection objects, ordered by timestamp DESC
        """
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT * FROM user_selections
            WHERE job_posting_id = ?
            ORDER BY timestamp DESC
        """, (job_id,))
        rows = cursor.fetchall()

        selections = []
        for row in rows:
            timestamp_str = row["timestamp"]
            # Parse timestamp if it's a string
            if isinstance(timestamp_str, str):
                timestamp = datetime.fromisoformat(timestamp_str)
            else:
                timestamp = timestamp_str

            selection = UserSelection(
                job_posting_id=row["job_posting_id"],
                action=row["action"],
                timestamp=timestamp,
                user_notes=row["user_notes"] or ""
            )
            selections.append(selection)

        return selections

    def _row_to_job_posting(self, row: sqlite3.Row) -> JobPosting:
        """Convert a SQLite row to a JobPosting object.

        Args:
            row: SQLite row from job_postings table

        Returns:
            JobPosting object
        """
        # Parse datetime strings to datetime objects
        posted_date = None
        if row["posted_date"]:
            posted_date = datetime.fromisoformat(row["posted_date"])

        application_deadline = None
        if row["application_deadline"]:
            application_deadline = datetime.fromisoformat(row["application_deadline"])

        # Deserialize raw_json from string to dict
        raw_json = {}
        if row["raw_json"]:
            try:
                raw_json = json.loads(row["raw_json"])
            except (json.JSONDecodeError, TypeError):
                raw_json = {}

        # Deserialize alternative_sources from string to list
        alternative_sources = []
        row_keys = row.keys() if hasattr(row, "keys") else []
        if "alternative_sources" in row_keys and row["alternative_sources"]:
            try:
                alternative_sources = json.loads(row["alternative_sources"])
            except (json.JSONDecodeError, TypeError):
                alternative_sources = []

        # Get JobSource enum from string value
        source = JobSource(row["source"])

        return JobPosting(
            source=source,
            source_id=row["source_id"],
            company=row["company"],
            title=row["title"],
            location=row["location"],
            description=row["description"],
            posted_date=posted_date,
            application_deadline=application_deadline,
            salary_min=row["salary_min"],
            salary_max=row["salary_max"],
            experience_required=row["experience_required"],
            education_required=row["education_required"],
            sponsorship_available=(
                None
                if row["sponsorship_available"] is None
                else bool(row["sponsorship_available"])
            ),
            work_mode=row["work_mode"],
            url=row["url"],
            ats_platform=row["ats_platform"],
            raw_json=raw_json,
            alternative_sources=alternative_sources
        )

    def save_search_goal(self, goal: SearchGoals, goal_name: str = None) -> int:
        """Save a search goal to the database.

        Args:
            goal: SearchGoals object to save
            goal_name: Optional name/label for the goal

        Returns:
            ID of the saved goal
        """
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO search_goals
            (job_title, industries, location, min_salary, max_salary,
             remote_preference, sponsorship_required, experience_level,
             company_size, target_companies, exclude_companies,
             employment_type, relocation_willing, goal_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            goal.job_title,
            goal.industries,
            goal.location,
            goal.min_salary,
            goal.max_salary,
            goal.remote_preference,
            goal.sponsorship_required,
            goal.experience_level,
            goal.company_size,
            goal.target_companies,
            goal.exclude_companies,
            goal.employment_type,
            goal.relocation_willing,
            goal_name or goal.job_title
        ))
        self.connection.commit()
        return cursor.lastrowid

    def get_search_goal(self, goal_id: int) -> Optional[dict]:
        """Retrieve a search goal by ID.

        Args:
            goal_id: ID of the search goal

        Returns:
            Dict with goal data or None if not found
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM search_goals WHERE id = ?", (goal_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_search_goals(self) -> List[dict]:
        """Retrieve all saved search goals.

        Returns:
            List of dicts with goal data, ordered by created_at DESC
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM search_goals ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def update_search_goal(self, goal_id: int, goal: SearchGoals, goal_name: str = None) -> bool:
        """Update an existing search goal.

        Args:
            goal_id: ID of the goal to update
            goal: Updated SearchGoals object
            goal_name: Optional updated name/label

        Returns:
            True on success, False on error
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                UPDATE search_goals
                SET job_title = ?, industries = ?, location = ?, min_salary = ?,
                    max_salary = ?, remote_preference = ?, sponsorship_required = ?,
                    experience_level = ?, company_size = ?, target_companies = ?,
                    exclude_companies = ?, employment_type = ?, relocation_willing = ?,
                    goal_name = ?
                WHERE id = ?
            """, (
                goal.job_title,
                goal.industries,
                goal.location,
                goal.min_salary,
                goal.max_salary,
                goal.remote_preference,
                goal.sponsorship_required,
                goal.experience_level,
                goal.company_size,
                goal.target_companies,
                goal.exclude_companies,
                goal.employment_type,
                goal.relocation_willing,
                goal_name or goal.job_title,
                goal_id
            ))
            self.connection.commit()
            return True
        except Exception:
            return False

    def delete_search_goal(self, goal_id: int) -> bool:
        """Delete a search goal.

        Args:
            goal_id: ID of the goal to delete

        Returns:
            True on success, False on error
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM search_goals WHERE id = ?", (goal_id,))
            self.connection.commit()
            return True
        except Exception:
            return False

    def close(self) -> None:
        """Close the database connection."""
        if self.connection:
            self.connection.close()
