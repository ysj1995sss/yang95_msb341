import pytest
import tempfile
import threading
from pathlib import Path
from datetime import datetime
from resume_tailorer.job_search.models import JobSource, SearchGoals, JobPosting, UserSelection
from resume_tailorer.job_search.database import JobDatabase


@pytest.fixture
def temp_db():
    """Create a temporary database file for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_job_search.db"
        db = JobDatabase(str(db_path))
        yield db
        db.close()


def test_database_initialization(temp_db):
    """JobDatabase can be initialized, db file created."""
    # Database should be initialized
    assert temp_db is not None
    # Tables should exist (test by trying to query)
    # If tables don't exist, the next operations would fail


def test_save_and_retrieve_job_posting(temp_db):
    """Save job, retrieve by ID, verify fields."""
    # Create tables first
    temp_db.create_tables()

    # Create a sample job posting
    job = JobPosting(
        source=JobSource.LINKEDIN,
        source_id="12345",
        company="Tech Corp",
        title="Senior Software Engineer",
        location="San Francisco, CA",
        description="We are looking for a talented software engineer.",
        posted_date=datetime(2024, 9, 1),
        application_deadline=datetime(2024, 10, 1),
        salary_min=100000,
        salary_max=150000,
        experience_required="5+ years",
        education_required="Bachelor's in CS",
        sponsorship_available=True,
        work_mode="hybrid",
        url="https://linkedin.com/jobs/12345",
        ats_platform="Greenhouse",
        raw_json={"job_id": "12345", "company_id": "corp123"}
    )

    # Save the job
    job_id = temp_db.save_job_posting(job)

    # Verify job_id format
    assert job_id == "linkedin_12345"

    # Retrieve the job
    retrieved_job = temp_db.get_job_posting(job_id)

    # Verify fields
    assert retrieved_job is not None
    assert retrieved_job.source == JobSource.LINKEDIN
    assert retrieved_job.source_id == "12345"
    assert retrieved_job.company == "Tech Corp"
    assert retrieved_job.title == "Senior Software Engineer"
    assert retrieved_job.location == "San Francisco, CA"
    assert retrieved_job.salary_min == 100000
    assert retrieved_job.salary_max == 150000
    assert retrieved_job.sponsorship_available is True
    assert retrieved_job.work_mode == "hybrid"
    assert retrieved_job.url == "https://linkedin.com/jobs/12345"
    assert retrieved_job.ats_platform == "Greenhouse"
    assert retrieved_job.raw_json == {"job_id": "12345", "company_id": "corp123"}


def test_search_jobs_by_goals(temp_db):
    """Save job, search with matching goals, verify results."""
    temp_db.create_tables()

    # Save multiple jobs
    job1 = JobPosting(
        source=JobSource.LINKEDIN,
        source_id="1",
        company="Tech Corp",
        title="Senior Software Engineer",
        location="San Francisco, CA",
        description="Looking for senior engineer",
        salary_min=100000,
        salary_max=150000,
        sponsorship_available=True,
        work_mode="hybrid"
    )

    job2 = JobPosting(
        source=JobSource.INDEED,
        source_id="2",
        company="Finance Inc",
        title="Junior Software Engineer",
        location="New York, NY",
        description="Looking for junior engineer",
        salary_min=60000,
        salary_max=80000,
        sponsorship_available=False,
        work_mode="remote"
    )

    job3 = JobPosting(
        source=JobSource.GREENHOUSE,
        source_id="3",
        company="Excluded Corp",
        title="Software Engineer",
        location="Chicago, IL",
        description="Should be excluded",
        salary_min=80000,
        salary_max=120000,
        sponsorship_available=False,
        work_mode="in-person"
    )

    temp_db.save_job_posting(job1)
    temp_db.save_job_posting(job2)
    temp_db.save_job_posting(job3)

    # Search with goals
    goals = SearchGoals(
        job_title="Software Engineer",
        industries=["Technology"],
        min_salary=90000,
        max_salary=160000,
        location="San Francisco",
        remote_preference="any",
        sponsorship_required=False,
        experience_level="senior",
        company_size="large",
        exclude_companies=["Excluded Corp"]
    )

    results = temp_db.search_jobs(goals)

    # Should find job1 (matches title, location, salary, sponsorship not required)
    # Should not find job2 (salary too low)
    # Should not find job3 (excluded)
    assert len(results) >= 1
    assert any(job.source_id == "1" for job in results)
    assert not any(job.source_id == "3" for job in results)


def test_record_user_selection(temp_db):
    """Record selection, retrieve it back."""
    temp_db.create_tables()

    # Save a job first
    job = JobPosting(
        source=JobSource.LINKEDIN,
        source_id="12345",
        company="Tech Corp",
        title="Software Engineer",
        location="San Francisco, CA",
        description="Test job"
    )
    job_id = temp_db.save_job_posting(job)

    # Record a user selection
    selection = UserSelection(
        job_posting_id=job_id,
        action="interested",
        user_notes="Great opportunity!"
    )

    result = temp_db.record_user_selection(selection)
    assert result is True

    # Retrieve the selection
    selections = temp_db.get_user_selections(job_id)
    assert len(selections) > 0
    assert selections[0].action == "save"
    assert selections[0].user_notes == "Great opportunity!"


def test_salary_range_filtering(temp_db):
    """Verify salary filtering works correctly."""
    temp_db.create_tables()

    # Create jobs with different salary ranges
    job_low = JobPosting(
        source=JobSource.LINKEDIN,
        source_id="low",
        company="Corp A",
        title="Software Engineer",
        location="San Francisco, CA",
        description="Low salary",
        salary_min=40000,
        salary_max=60000
    )

    job_medium = JobPosting(
        source=JobSource.LINKEDIN,
        source_id="medium",
        company="Corp B",
        title="Software Engineer",
        location="San Francisco, CA",
        description="Medium salary",
        salary_min=80000,
        salary_max=120000
    )

    job_high = JobPosting(
        source=JobSource.LINKEDIN,
        source_id="high",
        company="Corp C",
        title="Software Engineer",
        location="San Francisco, CA",
        description="High salary",
        salary_min=150000,
        salary_max=200000
    )

    temp_db.save_job_posting(job_low)
    temp_db.save_job_posting(job_medium)
    temp_db.save_job_posting(job_high)

    # Search for jobs in 80k-130k range
    goals = SearchGoals(
        job_title="Software Engineer",
        industries=["Technology"],
        min_salary=80000,
        max_salary=130000,
        location="San Francisco",
        remote_preference="any",
        sponsorship_required=False,
        experience_level="mid",
        company_size="large"
    )

    results = temp_db.search_jobs(goals)

    # Should only find job_medium (80k-120k overlaps with 80k-130k)
    source_ids = [job.source_id for job in results]
    assert "medium" in source_ids
    # job_low (40k-60k) is below the range
    # job_high (150k-200k) is above the range


def test_create_tables_migrates_legacy_schema_without_alternative_sources(tmp_path):
    """A pre-existing DB without the alternative_sources column gets migrated safely."""
    import sqlite3
    db_path = str(tmp_path / "legacy.db")

    # Simulate a legacy database missing the alternative_sources column
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE job_postings (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            source_id TEXT NOT NULL,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            location TEXT NOT NULL,
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source, source_id)
        )
    """)
    conn.commit()
    conn.close()

    # Now open with JobDatabase and run create_tables — should migrate, not crash
    db = JobDatabase(db_path)
    db.create_tables()  # should migrate the legacy table

    # Verify we can now save a job with alternative_sources without error
    posting = JobPosting(
        source=JobSource.LINKEDIN,
        source_id="test-migration-1",
        company="TestCo",
        title="Engineer",
        location="Remote",
        description="desc",
        url="https://example.com/job/1",
    )
    job_id = db.save_job_posting(posting)
    assert job_id is not None

    retrieved = db.get_job_posting(job_id)
    assert retrieved is not None
    assert retrieved.alternative_sources == []

    db.close()


def test_search_jobs_unknown_work_mode_passes_remote_preference(temp_db):
    """Real Greenhouse postings have work_mode='Unknown' (never fabricated).
    Selecting remote must not silently hide 100% of them."""
    temp_db.create_tables()

    unknown_job = JobPosting(
        source=JobSource.GREENHOUSE,
        source_id="unknown-wm",
        company="Airbnb",
        title="Software Engineer",
        location="Remote - US",
        description="Real posting with no work mode exposed by the API",
        work_mode="Unknown",
        url="https://boards.greenhouse.io/airbnb/jobs/1",
    )
    onsite_job = JobPosting(
        source=JobSource.GREENHOUSE,
        source_id="onsite-wm",
        company="Airbnb",
        title="Software Engineer",
        location="Remote - US",
        description="Explicitly on-site",
        work_mode="on-site",
        url="https://boards.greenhouse.io/airbnb/jobs/2",
    )

    temp_db.save_job_posting(unknown_job)
    temp_db.save_job_posting(onsite_job)

    goals = SearchGoals(
        job_title="Software Engineer",
        industries=["Technology"],
        min_salary=0,
        max_salary=0,
        location="Remote",
        remote_preference="remote",
        sponsorship_required=False,
        experience_level="mid",
        company_size="any",
    )

    results = temp_db.search_jobs(goals)
    source_ids = {job.source_id for job in results}

    assert "unknown-wm" in source_ids
    assert "onsite-wm" not in source_ids


def test_connection_usable_from_a_different_thread_than_it_was_created_on(tmp_path):
    """Found live (2026-09-24): Streamlit's Job Search page caches a
    JobService (and its JobDatabase connection) in st.session_state, but
    Streamlit can run a session's script rerun on a different worker thread
    than the one that created that connection. sqlite3's default
    check_same_thread=True raised 'SQLite objects created in a thread can
    only be used in that same thread.' the moment a rerun landed on a new
    thread. This reproduces that shape directly: create the connection on
    this thread, use it from another."""
    db_path = str(tmp_path / "thread_test.db")
    db = JobDatabase(db_path)
    db.create_tables()

    job = JobPosting(
        source=JobSource.GREENHOUSE,
        source_id="thread-1",
        company="Acme",
        title="Engineer",
        location="Remote",
        description="desc",
    )
    db.save_job_posting(job)

    errors: list[Exception] = []

    def query_from_other_thread():
        try:
            db.get_job_posting(f"{job.source.value}_{job.source_id}")
        except Exception as exc:  # noqa: BLE001 - capturing for the assertion below
            errors.append(exc)

    thread = threading.Thread(target=query_from_other_thread)
    thread.start()
    thread.join()

    assert errors == []
    db.close()
