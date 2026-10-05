"""Workspace API, phase 3: Tailor (spec 009). The model is a stub; synthetic data only."""

import json
import re
import time
from unittest.mock import patch

import pytest

from tests.test_workspace_jobs import jobs_client  # noqa: F401  (stubbed job boards)
from tests.workspace_helpers import resume_docx


class StubModel:
    def __init__(self, settings=None):
        pass

    def complete(self, system, user, max_tokens=2000):
        found = re.search(r'\[\s*\{\s*"paragraph_index"', user)
        if not found:
            return "[]"
        bullets, _ = json.JSONDecoder().raw_decode(user[found.start():])
        edits = [{"paragraph_index": b["paragraph_index"], "change": "keep", "new_text": ""} for b in bullets]
        for edit, bullet in zip(edits, bullets):
            if bullet["text"].startswith("Built SQL dashboards"):
                edit.update(change="rewrite", new_text="Built Tableau SQL dashboards used by 40 managers across regional sales teams")
        return json.dumps(edits)


@pytest.fixture()
def tailor_client(jobs_client, monkeypatch):  # noqa: F811
    from resume_tailorer.docx_export import converter

    monkeypatch.setenv("LLM_MODEL", "stub/model")
    monkeypatch.setenv("LLM_API_KEY", "stub-key")
    monkeypatch.setattr(converter, "_word_platform", lambda: False)
    monkeypatch.setattr(converter, "_soffice", lambda: None)
    with patch("resume_tailorer.llm.client.LLMClient", StubModel):
        yield jobs_client


def _ready(client):
    client.post("/v2/profile/resume", files={"file": ("r.docx", resume_docx(), "application/octet-stream")})
    client.post("/v2/jobs/search", json={"job_title": "Data Analyst"})
    client.post("/v2/jobs/greenhouse_101/action", json={"action": "apply"})


def _run(client):
    started = client.post("/v2/tailor/run", json={})
    assert started.status_code == 200, started.text
    for _ in range(200):
        status = client.get("/v2/tailor/run").json()
        if status["status"] != "running":
            return status
        time.sleep(0.05)
    raise AssertionError("tailoring never finished")


def test_needs_a_job_and_a_resume(tailor_client):
    page = tailor_client.get("/v2/tailor").json()
    assert page["job"] is None and page["resume"] is None and page["model_ready"] is True
    assert tailor_client.post("/v2/tailor/run", json={}).status_code == 409


def test_run_review_decide_rebuild_download(tailor_client):
    _ready(tailor_client)
    page = tailor_client.get("/v2/tailor").json()
    assert page["job"]["title"] == "Senior Data Analyst" and "Career Profile" in page["resume"]["label"]
    status = _run(tailor_client)
    assert status["status"] == "done", status

    review = tailor_client.get("/v2/tailor").json()["review"]
    assert review["version"] >= 1 and review["progress"]["can_continue"] is False
    change = next(c for c in review["changes"] if "Tableau" in c["proposed"])
    assert change["decision"] is None and change["original"].startswith("Built SQL dashboards")

    for c in review["changes"]:
        r = tailor_client.post("/v2/tailor/decisions", json={"change_id": c["id"], "decision": "ACCEPTED"})
        assert r.status_code == 200
    assert r.json()["progress"]["needs_rebuild"] is True
    rebuilt = tailor_client.post("/v2/tailor/rebuild").json()
    assert rebuilt["progress"]["needs_rebuild"] is False
    assert "Tableau SQL dashboards" in rebuilt["tailored_text"]
    # No office suite in tests, so there's no PDF; the Word file is always there.
    assert tailor_client.get("/v2/tailor/download/docx").status_code == 200
    assert tailor_client.get("/v2/tailor/download/pdf").status_code == 404


def test_an_unverifiable_manual_edit_is_refused(tailor_client):
    _ready(tailor_client)
    _run(tailor_client)
    review = tailor_client.get("/v2/tailor").json()["review"]
    change = next(c for c in review["changes"] if "Tableau" in c["proposed"])
    tailor_client.post("/v2/tailor/decisions", json={"change_id": change["id"], "decision": "MANUALLY_EDITED",
                                                     "manual_text": "  "})
    r = tailor_client.post("/v2/tailor/rebuild")
    assert r.status_code == 400 and "empty" in r.json()["detail"]


def test_discard_starts_over(tailor_client):
    _ready(tailor_client)
    _run(tailor_client)
    assert tailor_client.delete("/v2/tailor/review").json() == {"discarded": True}
    assert tailor_client.get("/v2/tailor").json()["review"] is None
    assert tailor_client.post("/v2/tailor/decisions", json={"change_id": "x", "decision": "ACCEPTED"}).status_code == 404
