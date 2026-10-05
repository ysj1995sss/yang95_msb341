"""Usage limits and error handling (decision 030)."""

import pytest
from fastapi import HTTPException

from app.workspace import limits


def test_a_limit_refuses_with_a_plain_message_and_resets(workspace_client, monkeypatch):
    monkeypatch.setenv("SEARCHES_PER_HOUR", "2")
    limits.use("local", "search", now=1000)
    limits.use("local", "search", now=1100)
    with pytest.raises(HTTPException) as refused:
        limits.use("local", "search", now=1200)
    assert refused.value.status_code == 429 and "2 searches this hour" in refused.value.detail
    limits.use("local", "search", now=1000 + 3601)  # the first one has left the window


def test_zero_turns_a_limit_off(workspace_client, monkeypatch):
    monkeypatch.setenv("IMPORTS_PER_DAY", "0")
    for _ in range(50):
        limits.use("local", "import")


def test_the_search_endpoint_is_limited(workspace_client, monkeypatch):
    monkeypatch.setenv("SEARCHES_PER_HOUR", "1")
    limits.use("local", "search")
    r = workspace_client.post("/v2/jobs/search", json={"job_title": "Analyst"})
    assert r.status_code == 429 and "searches this hour" in r.json()["detail"]


def test_an_unexpected_error_shows_a_reference_not_a_stack_trace(workspace_client, monkeypatch):
    from app.main import app

    @app.get("/v2/__boom")
    def boom():
        raise RuntimeError("secret internals")

    r = workspace_client.get("/v2/__boom")
    assert r.status_code == 500 and "reference" in r.json()["detail"] and "secret" not in r.text
    assert workspace_client.get("/health").headers["X-Request-Id"]
