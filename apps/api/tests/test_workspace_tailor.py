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


def test_review_payload_explains_each_full_change_and_defaults_to_manual(tailor_client):
    _ready(tailor_client)
    assert _run(tailor_client)["status"] == "done"
    review = tailor_client.get("/v2/tailor").json()["review"]
    assert review["review_mode"] == "manual" and review["review_revision"] > 0
    change = next(c for c in review["changes"] if "reporting dashboards" in c["proposed"])
    assert change["original"][:25] in change["title"]
    assert change["proposed"][:25] in change["title"]
    assert change["category"] == "REPHRASED"
    assert change["decision_origin"] is None
    assert "full_requirement" in change


def test_batch_decisions_are_atomic_and_stale_tabs_cannot_overwrite(tailor_client):
    _ready(tailor_client)
    assert _run(tailor_client)["status"] == "done"
    original = tailor_client.get("/v2/tailor").json()["review"]
    start = original["review_revision"]
    change_id = original["changes"][0]["id"]
    invalid = tailor_client.post("/v2/tailor/decisions/batch", json={
        "expected_revision": start, "decisions": [
            {"change_id": change_id, "decision": "REJECTED"},
            {"change_id": "not-in-review", "decision": "ACCEPTED"},
        ],
    })
    assert invalid.status_code == 400
    assert tailor_client.get("/v2/tailor").json()["review"]["review_revision"] == start
    saved = tailor_client.post("/v2/tailor/decisions/batch", json={
        "expected_revision": start, "decisions": [{"change_id": change_id, "decision": "REJECTED"}],
    })
    assert saved.status_code == 200 and saved.json()["review_revision"] == start + 1
    assert next(c for c in saved.json()["changes"] if c["id"] == change_id)["decision_origin"] == "person"
    stale = tailor_client.post("/v2/tailor/decisions/batch", json={
        "expected_revision": start, "decisions": [{"change_id": change_id, "decision": "ACCEPTED"}],
    })
    assert stale.status_code == 409
    reloaded = tailor_client.get("/v2/tailor").json()["review"]
    assert reloaded["review_revision"] == start + 1
    assert next(c for c in reloaded["changes"] if c["id"] == change_id)["decision"] == "REJECTED"


def test_assisted_mode_makes_conservative_decisions_before_review(tailor_client):
    _ready(tailor_client)
    started = tailor_client.post("/v2/tailor/run", json={"review_mode": "assisted"})
    assert started.status_code == 200
    for _ in range(200):
        status = tailor_client.get("/v2/tailor/run").json()
        if status["status"] != "running":
            break
        time.sleep(0.05)
    assert status["status"] == "done", status
    review = tailor_client.get("/v2/tailor").json()["review"]
    assert review["review_mode"] == "assisted"
    assert any(c["decision_origin"] == "AI-assisted" for c in review["changes"])
    assert all(c["decision"] != "ACCEPTED" for c in review["changes"] if c["check"] != "Verified")


def test_rebuild_advances_review_revision_so_an_old_tab_cannot_save(tailor_client):
    _ready(tailor_client)
    assert _run(tailor_client)["status"] == "done"
    review = tailor_client.get("/v2/tailor").json()["review"]
    change_id = review["changes"][0]["id"]
    selected = tailor_client.post("/v2/tailor/decisions/batch", json={
        "expected_revision": review["review_revision"],
        "decisions": [{"change_id": change_id, "decision": "REJECTED"}],
    }).json()
    rebuilt = tailor_client.post("/v2/tailor/rebuild")
    assert rebuilt.status_code == 200
    assert rebuilt.json()["review_revision"] == selected["review_revision"] + 1
    stale = tailor_client.post("/v2/tailor/decisions/batch", json={
        "expected_revision": selected["review_revision"],
        "decisions": [{"change_id": change_id, "decision": "ACCEPTED"}],
    })
    assert stale.status_code == 409


def test_a_failed_initial_review_save_is_not_reported_as_a_finished_run(tailor_client, monkeypatch):
    _ready(tailor_client)
    monkeypatch.setattr("resume_tailorer.review_decisions.save_review", lambda *args: False)
    result = _run(tailor_client)
    assert result["status"] == "failed"
    assert tailor_client.get("/v2/tailor").json()["review"] is None


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


def test_a_new_run_never_reuses_an_old_tabs_revision(tailor_client):
    # Change ids are positional ("paragraph:3"), so an old tab's selection must not
    # apply to a re-tailored review's different proposal at the same position.
    _ready(tailor_client)
    assert _run(tailor_client)["status"] == "done"
    old = tailor_client.get("/v2/tailor").json()["review"]
    assert _run(tailor_client)["status"] == "done"
    new = tailor_client.get("/v2/tailor").json()["review"]
    assert new["review_revision"] != old["review_revision"]
    stale = tailor_client.post("/v2/tailor/decisions/batch", json={
        "expected_revision": old["review_revision"],
        "decisions": [{"change_id": old["changes"][0]["id"], "decision": "ACCEPTED"}],
    })
    assert stale.status_code == 409
    assert all(c["decision"] is None for c in tailor_client.get("/v2/tailor").json()["review"]["changes"])


def test_single_decision_from_an_old_tab_is_refused(tailor_client):
    _ready(tailor_client)
    assert _run(tailor_client)["status"] == "done"
    review = tailor_client.get("/v2/tailor").json()["review"]
    change_id = review["changes"][0]["id"]
    first = tailor_client.post("/v2/tailor/decisions", json={
        "change_id": change_id, "decision": "REJECTED", "expected_revision": review["review_revision"]})
    assert first.status_code == 200
    stale = tailor_client.post("/v2/tailor/decisions", json={
        "change_id": change_id, "decision": "ACCEPTED", "expected_revision": review["review_revision"]})
    assert stale.status_code == 409
    # Older clients that send no revision keep working.
    legacy = tailor_client.post("/v2/tailor/decisions", json={"change_id": change_id, "decision": "ACCEPTED"})
    assert legacy.status_code == 200


def test_manual_choice_without_text_keeps_the_saved_wording(tailor_client):
    _ready(tailor_client)
    assert _run(tailor_client)["status"] == "done"
    change = next(c for c in tailor_client.get("/v2/tailor").json()["review"]["changes"]
                  if "reporting dashboards" in c["proposed"])
    wording = "Built SQL dashboards used by 40 managers"
    tailor_client.post("/v2/tailor/decisions", json={"change_id": change["id"], "decision": "MANUALLY_EDITED",
                                                      "manual_text": wording})
    again = tailor_client.post("/v2/tailor/decisions", json={"change_id": change["id"], "decision": "MANUALLY_EDITED"})
    assert again.status_code == 200
    assert next(c for c in again.json()["changes"] if c["id"] == change["id"])["manual_text"] == wording


def _pause_a_decision_mid_save(tailor_client, monkeypatch):
    """Start a batch decision and hold it right after it has read the saved review, inside
    the per-user lock. Returns (folder, job_id, release, finish)."""
    import threading
    from resume_tailorer import review_decisions

    review = tailor_client.get("/v2/tailor").json()["review"]
    real_load = review_decisions.load_review
    paused, release, seen = threading.Event(), threading.Event(), {}

    def slow_load(folder, job_id):
        state = real_load(folder, job_id)
        seen.update(folder=folder, job_id=job_id)
        paused.set()
        release.wait(5)
        return state

    monkeypatch.setattr(review_decisions, "load_review", slow_load)
    result = {}
    decider = threading.Thread(target=lambda: result.update(response=tailor_client.post(
        "/v2/tailor/decisions/batch", json={"expected_revision": review["review_revision"],
                                            "decisions": [{"change_id": review["changes"][0]["id"], "decision": "REJECTED"}]})))
    decider.start()
    assert paused.wait(5)

    def finish():
        release.set()
        decider.join(10)
        monkeypatch.setattr(review_decisions, "load_review", real_load)
        return result["response"]

    return seen["folder"], seen["job_id"], release, finish


def test_a_new_run_saved_during_another_tabs_decision_is_not_overwritten(tailor_client, monkeypatch):
    import threading
    from types import SimpleNamespace
    from app.workspace import tailor_router
    from resume_tailorer.review_store import load_review

    _ready(tailor_client)
    assert _run(tailor_client)["status"] == "done"
    folder, job_id, _release, finish = _pause_a_decision_mid_save(tailor_client, monkeypatch)
    newer = load_review(folder, job_id)
    newer["version"], newer["review_revision"] = 999, newer["review_revision"] + 1000
    saved = threading.Event()
    writer = threading.Thread(target=lambda: (tailor_router._save_review(
        SimpleNamespace(session={"artifacts_dir": folder}), job_id, newer), saved.set()))
    writer.start()
    saved.wait(1.0)  # unlocked, the new run's save lands while the decision is still in flight
    finish()
    writer.join(10)
    assert load_review(folder, job_id)["version"] == 999  # the new run survives


def test_start_over_during_another_tabs_decision_stays_discarded(tailor_client, monkeypatch):
    import threading
    from resume_tailorer.review_store import load_review

    _ready(tailor_client)
    assert _run(tailor_client)["status"] == "done"
    folder, job_id, _release, finish = _pause_a_decision_mid_save(tailor_client, monkeypatch)
    done = threading.Event()
    discarder = threading.Thread(target=lambda: (tailor_client.delete("/v2/tailor/review"), done.set()))
    discarder.start()
    done.wait(1.0)
    finish()
    discarder.join(10)
    assert load_review(folder, job_id) is None  # not resurrected by the in-flight decision


def test_assisted_rebuild_failure_keeps_the_review_for_the_person(tailor_client, monkeypatch):
    # Review finding 1: a rebuild error after AI assistance's choices (e.g. a free-form page
    # limit) used to fail the whole run and throw the model's proposals away.
    from resume_tailorer import tailoring_service

    real = tailoring_service.regenerate

    def regenerate(session, state):
        if state.get("assisted_review_applied"):
            raise tailoring_service.TailoringError("synthetic rebuild failure")
        return real(session, state)

    monkeypatch.setattr(tailoring_service, "regenerate", regenerate)
    _ready(tailor_client)
    assert tailor_client.post("/v2/tailor/run", json={"review_mode": "assisted"}).status_code == 200
    for _ in range(200):
        status = tailor_client.get("/v2/tailor/run").json()
        if status["status"] != "running":
            break
        time.sleep(0.05)
    assert status["status"] == "done", status
    review = tailor_client.get("/v2/tailor").json()["review"]
    assert review["changes"] and all(c["decision_origin"] != "AI-assisted" for c in review["changes"])
    assert "synthetic rebuild failure" in review["assisted_note"]
