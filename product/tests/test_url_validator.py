import pytest
from unittest.mock import patch, MagicMock
from resume_tailorer.job_search.url_validator import URLValidator
from resume_tailorer.job_search.models import JobPosting, JobSource


def _make_job(url="https://example.com/job/1"):
    return JobPosting(
        source=JobSource.GREENHOUSE,
        source_id="test-1",
        company="TestCo",
        title="Engineer",
        location="Remote",
        description="desc",
        url=url,
    )


def test_check_url_returns_active_on_200():
    validator = URLValidator()
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("resume_tailorer.job_search.url_validator.requests.head", return_value=mock_response):
        result = validator.check_url("https://example.com/job/1")

    assert result == "active"

def test_check_url_returns_closed_on_404():
    validator = URLValidator()
    mock_response = MagicMock()
    mock_response.status_code = 404

    with patch("resume_tailorer.job_search.url_validator.requests.head", return_value=mock_response):
        result = validator.check_url("https://example.com/job/404")

    assert result == "closed"

def test_check_url_returns_closed_on_410():
    validator = URLValidator()
    mock_response = MagicMock()
    mock_response.status_code = 410

    with patch("resume_tailorer.job_search.url_validator.requests.head", return_value=mock_response):
        result = validator.check_url("https://example.com/job/gone")

    assert result == "closed"

def test_check_url_returns_unknown_on_timeout():
    validator = URLValidator()

    with patch("resume_tailorer.job_search.url_validator.requests.head", side_effect=TimeoutError("timed out")):
        result = validator.check_url("https://example.com/job/slow")

    assert result == "unknown"

def test_check_url_returns_unknown_on_connection_error():
    validator = URLValidator()

    with patch("resume_tailorer.job_search.url_validator.requests.head", side_effect=Exception("connection refused")):
        result = validator.check_url("https://example.com/job/unreachable")

    assert result == "unknown"

def test_check_url_returns_unknown_on_other_status_codes():
    validator = URLValidator()
    mock_response = MagicMock()
    mock_response.status_code = 500

    with patch("resume_tailorer.job_search.url_validator.requests.head", return_value=mock_response):
        result = validator.check_url("https://example.com/job/error")

    assert result == "unknown"

def test_filter_active_jobs_keeps_active_and_unknown_drops_closed():
    validator = URLValidator()
    job_active = _make_job("https://example.com/active")
    job_closed = _make_job("https://example.com/closed")
    job_unknown = _make_job("https://example.com/unknown")

    def fake_check(url, timeout=5):
        return {
            "https://example.com/active": "active",
            "https://example.com/closed": "closed",
            "https://example.com/unknown": "unknown",
        }[url]

    with patch.object(validator, "check_url", side_effect=fake_check):
        result = validator.filter_active_jobs([job_active, job_closed, job_unknown])

    result_urls = {job.url for job in result}
    assert "https://example.com/active" in result_urls
    assert "https://example.com/unknown" in result_urls
    assert "https://example.com/closed" not in result_urls
    assert len(result) == 2

def test_filter_active_jobs_handles_empty_list():
    validator = URLValidator()
    result = validator.filter_active_jobs([])
    assert result == []

def test_filter_active_jobs_skips_jobs_with_no_url():
    """A job with an empty URL is treated as 'unknown' (kept), not checked over the network."""
    validator = URLValidator()
    job_no_url = _make_job(url="")

    with patch.object(validator, "check_url") as mock_check:
        result = validator.filter_active_jobs([job_no_url])

    mock_check.assert_not_called()
    assert len(result) == 1


def test_check_url_respects_rate_limit_between_consecutive_calls():
    """Back-to-back checks sleep to keep at most ~1 request/sec per host."""
    validator = URLValidator()
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("resume_tailorer.job_search.url_validator.requests.head", return_value=mock_response), \
         patch("resume_tailorer.job_search.url_validator.time.sleep") as mock_sleep:
        validator.check_url("https://example.com/job/1")
        validator.check_url("https://example.com/job/2")

    # First call: _last_request_time is 0.0 (epoch), so elapsed >> interval -> no sleep.
    # Second call: immediately after the first -> must sleep for the remainder.
    assert mock_sleep.call_count == 1
    slept = mock_sleep.call_args[0][0]
    assert 0 < slept <= URLValidator.MIN_REQUEST_INTERVAL


def test_first_check_url_call_is_not_delayed():
    """A fresh validator's first check is never delayed (last_request_time is epoch 0)."""
    validator = URLValidator()
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("resume_tailorer.job_search.url_validator.requests.head", return_value=mock_response), \
         patch("resume_tailorer.job_search.url_validator.time.sleep") as mock_sleep:
        validator.check_url("https://example.com/job/1")

    mock_sleep.assert_not_called()
