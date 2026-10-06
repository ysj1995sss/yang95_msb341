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
                edit.update(change="rewrite", new_text="Built SQL reporting dashboards used by 40 managers across regional sales teams")
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
    assert "sync_summary" in review
    # Spec 010: the overlap number is kept (compatibility) but explained, never called an ATS score.
    assert set(review["alignment"]) == {"before", "after"} and "not an employer score" in review["overlap_note"]
    assert tailor_client.get("/v2/tailor").json()["ats_explainer"]["title"] == "About ATS checks"
    rr = review["requirement_review"]
    assert rr["computed_from"] == "run" and rr["summary"].startswith("Required:")
    rows = [row for group in rr["groups"] for row in group["rows"]]
    assert rows and all({"text", "label", "tone", "reason", "evidence", "shown_in_resume"} <= set(r) for r in rows)
    assert any(r["evidence"] and r["evidence"][0]["source"] for r in rows)
    assert "not a check by any employer's ATS" in review["readability"]["note"]
    kw = review["keyword_report"]  # spec 011
    assert set(kw) >= {"added", "already", "left_out", "note"} and all("label" in g for g in kw["left_out"])
    assert review["readability"]["items"][0]["label"] == "Text can be read from the file"
    change = next(c for c in review["changes"] if "reporting dashboards" in c["proposed"])
    assert change["decision"] is None and change["original"].startswith("Built SQL dashboards")
    assert change["section_label"] == "Work experience"

    for c in review["changes"]:
        r = tailor_client.post("/v2/tailor/decisions", json={"change_id": c["id"], "decision": "ACCEPTED"})
        assert r.status_code == 200
    assert r.json()["progress"]["needs_rebuild"] is True
    rebuilt = tailor_client.post("/v2/tailor/rebuild").json()
    assert rebuilt["progress"]["needs_rebuild"] is False
    assert "SQL reporting dashboards" in rebuilt["tailored_text"]
    # No office suite in tests, so there's no PDF; the Word file is always there.
    assert tailor_client.get("/v2/tailor/download/docx").status_code == 200
    assert tailor_client.get("/v2/tailor/download/pdf").status_code == 404


def test_an_unverifiable_manual_edit_is_refused(tailor_client):
    _ready(tailor_client)
    _run(tailor_client)
    review = tailor_client.get("/v2/tailor").json()["review"]
    change = next(c for c in review["changes"] if "reporting dashboards" in c["proposed"])
    tailor_client.post("/v2/tailor/decisions", json={"change_id": change["id"], "decision": "MANUALLY_EDITED",
                                                     "manual_text": "  "})
    r = tailor_client.post("/v2/tailor/rebuild")
    assert r.status_code == 400 and "empty" in r.json()["detail"]


def test_conflicting_word_employer_stops_before_review_or_download(tailor_client):
    _ready(tailor_client)
    role = tailor_client.get("/v2/profile").json()["profile"]["work_experience"][0]
    edited = tailor_client.put("/v2/profile/work", json={
        "index": 0, "title": role["title"], "employer": "Cedar Analytics",
        "dates": role["dates"],
        "bullets": [*role["responsibilities"], *role["accomplishments"]],
    })
    assert edited.status_code == 200
    status = _run(tailor_client)
    assert status["status"] == "failed" and "Word file" in status["error"]
    assert tailor_client.get("/v2/tailor").json()["review"] is None
    assert tailor_client.get("/v2/tailor/download/docx").status_code == 404


def test_discard_starts_over(tailor_client):
    _ready(tailor_client)
    _run(tailor_client)
    assert tailor_client.delete("/v2/tailor/review").json() == {"discarded": True}
    assert tailor_client.get("/v2/tailor").json()["review"] is None
    assert tailor_client.post("/v2/tailor/decisions", json={"change_id": "x", "decision": "ACCEPTED"}).status_code == 404


JD = ("Data Analyst at Northwind. Requirements: SQL, Tableau and dashboard reporting for business partners. "
      "You will own weekly KPI reporting, partner with sales leaders, build self-serve dashboards, explain "
      "trends to executives, and keep data definitions consistent across teams. Preferred: Python and "
      "experience with experimentation in a fast-growing company.")


def test_a_pasted_job_description_can_be_tailored(tailor_client):
    tailor_client.post("/v2/profile/resume", files={"file": ("r.docx", resume_docx(), "application/octet-stream")})
    assert tailor_client.post("/v2/tailor/pasted", json={"title": "Analyst", "description": "too short"}).status_code == 400
    page = tailor_client.post("/v2/tailor/pasted", json={"title": "Data Analyst", "company": "Northwind",
                                                         "description": JD, "url": "https://northwind.example/jobs/1"}).json()
    assert page["job"]["title"] == "Data Analyst" and page["job"]["job_id"].startswith("company_pages_pasted-")
    assert _run(tailor_client)["status"] == "done"
    assert tailor_client.get("/v2/jobs/" + page["job"]["job_id"]).json()["row"]["source"] == "Pasted by you"


def test_a_model_for_one_run_works_without_server_settings(tailor_client, monkeypatch):
    monkeypatch.delenv("LLM_MODEL")
    monkeypatch.delenv("LLM_API_KEY")
    monkeypatch.setattr("app.workspace.tailor_router._load_local_env", lambda: None)
    _ready(tailor_client)
    assert tailor_client.get("/v2/tailor").json()["model_ready"] is False
    assert tailor_client.post("/v2/tailor/run", json={}).status_code == 503
    r = tailor_client.post("/v2/tailor/run", json={"model": "openai/gpt-4o-mini", "api_key": "user-key"})
    assert r.status_code == 200
    assert "user-key" not in str(tailor_client.get("/v2/tailor/run").json())


def test_a_custom_api_address_is_refused_on_a_shared_server(tailor_client, monkeypatch):
    from tests.workspace_helpers import SECRET, token

    monkeypatch.setenv("WORKSPACE_TOKEN_SECRET", SECRET)
    headers = {"Authorization": f"Bearer {token()}"}
    r = tailor_client.post("/v2/tailor/run", headers=headers,
                           json={"model": "x/y", "api_key": "k", "api_base": "http://169.254.169.254/"})
    assert r.status_code in (400, 409)  # 409 if no job yet; never accepted
    assert "custom API address" in r.json()["detail"] or "Choose a job" in r.json()["detail"]


def test_a_restart_never_leaves_a_run_spinning(tailor_client, monkeypatch):
    from app.workspace import tailor_router

    _ready(tailor_client)
    assert _run(tailor_client)["status"] == "done"
    tailor_router._write_run("local", {"status": "running", "step": "Writing", "job_id": "greenhouse_101",
                                       "boot": "an-earlier-server-start"})
    status = tailor_client.get("/v2/tailor/run").json()
    assert status["status"] == "failed" and "restarted" in status["error"] and "boot" not in status
    assert tailor_client.post("/v2/tailor/run", json={}).status_code == 200  # not stuck


def test_a_one_off_resume_survives_a_restart(tailor_client):
    from app.workspace import tailor_router

    _ready(tailor_client)
    tailor_client.post("/v2/tailor/one-off", files={"file": ("other.docx", resume_docx(), "application/octet-stream")})
    assert tailor_router._one_off("local")[0] == "other.docx"  # on disk, not in memory
    assert tailor_client.get("/v2/tailor").json()["resume"]["one_off"] is True
    tailor_client.delete("/v2/tailor/one-off")
    assert tailor_router._one_off("local") is None


def test_a_reviewed_resume_reaches_apply(tailor_client, monkeypatch):
    """Found by the browser tests: the handoff carried no job id, so Apply said there was no resume."""
    from tests.e2e_server import fake_pdf

    monkeypatch.setattr("resume_tailorer.docx_export.pipeline.convert_docx_to_pdf", fake_pdf)
    _ready(tailor_client)
    tailor_client.post("/v2/profile/confirm")
    assert _run(tailor_client)["status"] == "done"
    review = tailor_client.get("/v2/tailor").json()["review"]
    for c in review["changes"]:
        tailor_client.post("/v2/tailor/decisions", json={"change_id": c["id"], "decision": "ACCEPTED"})
    assert tailor_client.post("/v2/tailor/rebuild").json()["progress"]["can_continue"] is True
    apply = tailor_client.get("/v2/apply").json()
    assert apply["handoff"]["has_file"] is True and apply["view"]["stage"] == "ready"


def test_codex_cli_model_only_on_your_own_computer():
    """Signed in (a shared server), the codex-cli model would spend the owner's ChatGPT plan on
    other people's runs; locally it needs no key (decision 031)."""
    import pytest
    from fastapi import HTTPException

    from app.workspace.identity import Owner
    from app.workspace.tailor_router import RunRequest, _settings_for

    class FakeWorkspace:
        def __init__(self, signed_in):
            self.owner = Owner(owner_id="x", name="x", signed_in=signed_in)

    assert _settings_for(RunRequest(model="codex-cli"), FakeWorkspace(False)).model == "codex-cli"
    with pytest.raises(HTTPException) as refused:
        _settings_for(RunRequest(model="codex-cli"), FakeWorkspace(True))
    assert refused.value.status_code == 400 and "your own computer" in refused.value.detail
