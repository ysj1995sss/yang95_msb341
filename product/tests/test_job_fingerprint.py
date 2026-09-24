"""Tests for stable job fingerprinting."""

from resume_tailorer.job_search.models import JobPosting, JobSource
from resume_tailorer.job_search.fingerprint import job_fingerprint
from resume_tailorer.job_search.deduplicator import JobDeduplicator


def _posting(**kwargs):
    base = dict(
        source=JobSource.GREENHOUSE,
        source_id="1",
        company="Acme",
        title="PM",
        location="Remote",
        description="x",
        url="https://boards.greenhouse.io/acme/jobs/1",
    )
    base.update(kwargs)
    return JobPosting(**base)


def test_same_url_same_fingerprint_strips_tracking_params():
    a = _posting(url="https://example.com/jobs/1?utm=x")
    b = _posting(url="https://example.com/jobs/1")
    assert job_fingerprint(a) == job_fingerprint(b)


def test_distinct_source_ids_not_same_fingerprint():
    a = _posting(source_id="req-1", url="", description="Role A focusing on analytics")
    b = _posting(source_id="req-2", url="", description="Role B focusing on sales ops")
    assert job_fingerprint(a) != job_fingerprint(b)


def test_fingerprint_falls_back_to_company_title_location():
    a = _posting(source_id="", url="", company="Acme Inc", title="PM", location="NYC")
    b = _posting(source_id="", url="", company="acme inc", title="pm", location="nyc")
    assert job_fingerprint(a) == job_fingerprint(b)


def test_dedupe_keeps_distinct_greenhouse_reqs_same_title():
    dedup = JobDeduplicator()
    postings = [
        _posting(source_id="req-1", url="", title="Associate", description="Analytics track"),
        _posting(source_id="req-2", url="", title="Associate", description="Sales track"),
    ]
    result = dedup.deduplicate(postings)
    assert len(result) == 2


def test_dedupe_still_merges_cross_source_same_title_location():
    dedup = JobDeduplicator()
    postings = [
        JobPosting(
            source=JobSource.LINKEDIN,
            source_id="1",
            company="Tech Corp",
            title="Software Engineer",
            location="San Francisco, CA",
            description="from LI",
            url="https://linkedin.com/job/1",
        ),
        JobPosting(
            source=JobSource.INDEED,
            source_id="2",
            company="Tech Corp",
            title="Software Engineer",
            location="San Francisco, CA",
            description="from Indeed",
            url="https://indeed.com/job/2",
        ),
    ]
    result = dedup.deduplicate(postings)
    assert len(result) == 1
    assert result[0].source == JobSource.LINKEDIN
