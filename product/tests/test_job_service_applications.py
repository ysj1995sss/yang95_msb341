import pytest
import tempfile
import os
from unittest.mock import patch

from resume_tailorer.job_search.job_service import JobService
from resume_tailorer.job_search.models import JobPosting, JobSource
from resume_tailorer.applications.models import ApplicationMode
from resume_tailorer.models.career_profile import CareerTruthProfile, EducationEntry, WorkExperience


SAMPLE_FORM_HTML = """
<form>
    <input type="text" name="first_name" required>
    <input type="email" name="email" required>
</form>
"""


@pytest.fixture
def job_service(tmp_path):
    job_db_path = str(tmp_path / "jobs.db")
    app_db_path = str(tmp_path / "applications.db")
    service = JobService(db_path=job_db_path, applications_db_path=app_db_path)
    yield service
    service.close()


def _make_profile():
    return CareerTruthProfile(
        contact_info={"name": "Jane Doe", "email": "jane@example.com", "phone": "555-1234", "location": "SF"},
        education=[EducationEntry(degree="BS", field="CS", institution="MIT", year=2020)],
        work_experience=[WorkExperience(employer="TechCorp", title="Engineer", dates="2020-2023", responsibilities=[], accomplishments=[])],
        skills=["Python"],
        tools=[],
        certifications=[],
        accomplishments=[],
    )


def test_apply_for_job_records_submission(job_service):
    posting = JobPosting(
        source=JobSource.GREENHOUSE,
        source_id="1",
        company="TestCo",
        title="Engineer",
        location="Remote",
        description="desc",
        url="https://boards.greenhouse.io/testco/jobs/1",
        ats_platform="greenhouse",
    )
    job_id = job_service.db.save_job_posting(posting)

    with patch("resume_tailorer.applications.submission_engine.SubmissionEngine._fetch_form_html", return_value=SAMPLE_FORM_HTML):
        result = job_service.apply_for_job(
            job_id=job_id,
            profile=_make_profile(),
            resume_pdf_path="/tmp/resume.pdf",
            mode=ApplicationMode.MANUAL,
            dry_run=False,
            resume_match_score=88.0,
        )

    assert result.application_id
    assert result.job_posting_id == job_id
    assert result.ats_platform == "greenhouse"


def test_apply_for_job_dry_run_default_never_submits(job_service):
    posting = JobPosting(
        source=JobSource.GREENHOUSE,
        source_id="2",
        company="TestCo",
        title="Engineer",
        location="Remote",
        description="desc",
        url="https://boards.greenhouse.io/testco/jobs/2",
        ats_platform="greenhouse",
    )
    job_id = job_service.db.save_job_posting(posting)

    with patch("resume_tailorer.applications.submission_engine.SubmissionEngine._fetch_form_html", return_value=SAMPLE_FORM_HTML), \
         patch("resume_tailorer.applications.submission_engine.SubmissionEngine._submit_to_platform") as mock_submit:
        job_service.apply_for_job(
            job_id=job_id,
            profile=_make_profile(),
            resume_pdf_path="/tmp/resume.pdf",
            mode=ApplicationMode.ASSIST,
            resume_match_score=88.0,
        )

    mock_submit.assert_not_called()


def test_apply_for_job_raises_for_unknown_job_id(job_service):
    with pytest.raises(ValueError, match="not found"):
        job_service.apply_for_job(
            job_id="greenhouse_does_not_exist",
            profile=_make_profile(),
            resume_pdf_path="/tmp/resume.pdf",
            mode=ApplicationMode.ASSIST,
            resume_match_score=88.0,
        )


def test_job_service_exposes_applications_db(job_service):
    assert job_service.applications_db is not None


def test_apply_for_job_persists_job_and_fit_snapshots(job_service):
    posting = JobPosting(
        source=JobSource.GREENHOUSE,
        source_id="3",
        company="TestCo",
        title="Engineer",
        location="Remote",
        description="desc",
        url="https://boards.greenhouse.io/testco/jobs/3",
        ats_platform="greenhouse",
    )
    job_id = job_service.db.save_job_posting(posting)

    with patch("resume_tailorer.applications.submission_engine.SubmissionEngine._fetch_form_html", return_value=SAMPLE_FORM_HTML):
        result = job_service.apply_for_job(
            job_id=job_id,
            profile=_make_profile(),
            resume_pdf_path="/tmp/resume.pdf",
            mode=ApplicationMode.MANUAL,
            dry_run=False,
            resume_match_score=88.0,
        )

    persisted = job_service.applications_db.get_submission(result.application_id)
    assert persisted.job_snapshot["company"] == "TestCo"
    assert persisted.job_snapshot["title"] == "Engineer"
    assert "overall_fit" in persisted.candidate_fit_snapshot
    assert persisted.career_profile_version  # non-empty hash
