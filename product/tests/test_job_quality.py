"""Tests for job quality evaluation (Step 6)."""

from datetime import datetime, timedelta

from resume_tailorer.job_search.job_quality import evaluate_job_quality, quality_label
from resume_tailorer.job_search.models import JobPosting, JobQualityStatus, JobSource


def _job(**overrides):
    defaults = dict(
        source=JobSource.GREENHOUSE,
        source_id="1",
        company="Acme",
        title="Engineer",
        location="Remote",
        description="Build things",
        posted_date=datetime(2026, 9, 1),
        url="https://example.com/job/1",
    )
    defaults.update(overrides)
    return JobPosting(**defaults)


def test_active_when_recent_and_url_active():
    now = datetime(2026, 9, 20)
    job = _job(posted_date=datetime(2026, 9, 10))
    assert evaluate_job_quality(job, now=now, url_status="active") == JobQualityStatus.ACTIVE


def test_stale_when_posted_beyond_threshold():
    now = datetime(2026, 9, 20)
    job = _job(posted_date=datetime(2026, 6, 1))
    assert evaluate_job_quality(job, now=now, stale_days=45) == JobQualityStatus.STALE


def test_expired_when_deadline_passed():
    now = datetime(2026, 9, 20)
    job = _job(
        posted_date=datetime(2026, 9, 1),
        application_deadline=datetime(2026, 9, 10),
    )
    assert evaluate_job_quality(job, now=now) == JobQualityStatus.EXPIRED


def test_broken_when_url_closed():
    job = _job(posted_date=datetime(2026, 9, 15))
    assert (
        evaluate_job_quality(job, now=datetime(2026, 9, 20), url_status="closed")
        == JobQualityStatus.BROKEN
    )


def test_unknown_when_no_dates():
    job = _job(posted_date=None, application_deadline=None)
    assert evaluate_job_quality(job, now=datetime(2026, 9, 20)) == JobQualityStatus.UNKNOWN


def test_broken_takes_priority_over_expired():
    now = datetime(2026, 9, 20)
    job = _job(
        posted_date=datetime(2026, 9, 1),
        application_deadline=datetime(2026, 9, 10),
    )
    assert evaluate_job_quality(job, now=now, url_status="closed") == JobQualityStatus.BROKEN


def test_quality_label():
    assert quality_label(JobQualityStatus.STALE) == "Stale"
    assert quality_label(JobQualityStatus.BROKEN) == "Broken URL"


def test_stale_boundary_just_inside_window():
    now = datetime(2026, 9, 20)
    job = _job(posted_date=now - timedelta(days=44))
    assert evaluate_job_quality(job, now=now, stale_days=45) == JobQualityStatus.ACTIVE
