"""Spec 011 batches through the API: tailor two jobs in the background, open one in Tailor,
finish its review, and prepare it. Nothing is submitted. Stubbed boards and model."""

import time

from tests.test_workspace_jobs import jobs_client  # noqa: F401
from tests.test_workspace_tailor import tailor_client  # noqa: F401
from tests.workspace_helpers import resume_docx


def _wait(client):
    for _ in range(400):
        batch = client.get("/v2/batch").json()["batch"]
        if batch and batch["status"] != "running":
            return batch
        time.sleep(0.05)
    raise AssertionError("the batch never finished")


def _setup(client):
    client.post("/v2/profile/resume", files={"file": ("r.docx", resume_docx(), "application/octet-stream")})
    client.post("/v2/jobs/search", json={"job_title": "Data Analyst"})


def test_a_batch_tailors_each_job_and_prepares_only_reviewed_ones(tailor_client, monkeypatch):  # noqa: F811
    from resume_tailorer.docx_export import pipeline

    from tests.e2e_server import fake_pdf

    monkeypatch.setattr(pipeline, "convert_docx_to_pdf", fake_pdf)  # a real PDF, so there's one to attach
    _setup(tailor_client)
    pasted = tailor_client.post("/v2/tailor/pasted", json={
        "title": "Marketing Analyst", "company": "Bluebird Goods",
        "description": ("Marketing Analyst at Bluebird Goods. Requirements: SQL and dashboard reporting for business "
                        "partners, weekly KPI reporting, partnering with sales leaders, explaining trends to executives, "
                        "and keeping data definitions consistent across teams in a fast-growing company. You will also "
                        "own the quarterly business review deck and work closely with finance on forecasting.")}).json()
    ids = ["greenhouse_101", pasted["job"]["job_id"]]
    started = tailor_client.post("/v2/batch/tailor", json={"job_ids": ids})
    assert started.status_code == 200, started.text
    assert tailor_client.post("/v2/tailor/run", json={}).status_code in (409, 200)  # one run at a time
    batch = _wait(tailor_client)
    assert [i["job_id"] for i in batch["items"]] == ids
    assert all(i["status"] == "done" for i in batch["items"]), batch
    assert batch["summary"].startswith("2 of 2 tailored")

    # Nothing reviewed yet: nothing is tracked.
    prepared = tailor_client.post("/v2/batch/prepare", json={}).json()["results"]
    assert {r["job_id"]: r["status"] for r in prepared}["greenhouse_101"] == "review_first"

    # Open one job in Tailor, review every change, then prepare.
    assert tailor_client.post("/v2/batch/open", json={"job_id": "greenhouse_101"}).status_code == 200
    review = tailor_client.get("/v2/tailor").json()["review"]
    assert review is not None and tailor_client.get("/v2/tailor").json()["job"]["job_id"] == "greenhouse_101"
    for change in review["changes"]:
        tailor_client.post("/v2/tailor/decisions", json={"change_id": change["id"], "decision": "ACCEPTED"})
    if tailor_client.get("/v2/tailor").json()["review"]["progress"]["needs_rebuild"]:
        assert tailor_client.post("/v2/tailor/rebuild").status_code == 200
    results = {r["job_id"]: r for r in tailor_client.post("/v2/batch/prepare", json={}).json()["results"]}
    assert results["greenhouse_101"]["status"] == "tracked", (results, tailor_client.get("/v2/tailor").json()["review"]["progress"])
    assert "Finish on the employer's site" in results["greenhouse_101"]["message"]
    tracker = tailor_client.get("/v2/tracker").json()
    assert any(r["status"] == "ready_to_apply" for r in tracker["rows"])  # tracked, never submitted


def test_batch_limits_and_cancel(tailor_client):  # noqa: F811
    _setup(tailor_client)
    assert tailor_client.post("/v2/batch/tailor", json={"job_ids": [f"x_{i}" for i in range(11)]}).status_code == 400
    assert tailor_client.post("/v2/batch/tailor", json={"job_ids": ["nope_1"]}).status_code == 404
    assert tailor_client.post("/v2/batch/prepare", json={}).status_code == 409  # nothing tailored yet
    assert tailor_client.delete("/v2/batch").json()["batch"] is None


# --- spec 014: continue, tailor again, and out-of-date reviews -------------------------------

def _batch_file(client):
    """The local (single-user) person's folder, where the batch file lives."""
    from resume_tailorer.identity import user_dir

    return user_dir("local")


def test_a_stopped_batch_can_be_continued_with_its_options(tailor_client):  # noqa: F811
    from resume_tailorer import batch_runner

    _setup(tailor_client)
    assert tailor_client.post("/v2/batch/continue", json={}).status_code == 409  # no batch yet
    # A batch the server was running when it restarted: its heartbeat stopped long ago.
    batch_runner.write_batch(_batch_file(tailor_client), {
        "id": "old1", "status": "running", "heartbeat": 1.0, "process": "gone", "created": 1.0, "note": "",
        "options": {"model": None, "length": "preserve", "conservative": True},
        "items": [{"job_id": "greenhouse_101", "title": "Senior Data Analyst", "company": "GitLab",
                   "status": "running", "error": "", "resumable": False}]})
    stopped = tailor_client.get("/v2/batch").json()["batch"]
    assert stopped["status"] == "stopped" and stopped["resumable_count"] == 1
    assert "Continue it to tailor the rest" in stopped["note"]
    assert stopped["items"][0]["status"] == "not_started"

    r = tailor_client.post("/v2/batch/continue", json={})
    assert r.status_code == 200, r.text
    batch = _wait(tailor_client)
    assert batch["status"] == "done" and batch["items"][0]["status"] == "done", batch
    assert batch["options"]["conservative"] is True and batch["resumable_count"] == 0
    assert tailor_client.post("/v2/batch/continue", json={}).status_code == 409  # nothing left


def test_a_profile_edit_flags_tailored_jobs_and_blocks_preparing(tailor_client, monkeypatch):  # noqa: F811
    from resume_tailorer.docx_export import pipeline

    from tests.e2e_server import fake_pdf

    monkeypatch.setattr(pipeline, "convert_docx_to_pdf", fake_pdf)
    _setup(tailor_client)
    tailor_client.post("/v2/batch/tailor", json={"job_ids": ["greenhouse_101"]})
    batch = _wait(tailor_client)
    assert batch["items"][0]["stale"] is False and batch["items"][0]["stale_message"] == ""
    tailor_client.post("/v2/batch/open", json={"job_id": "greenhouse_101"})
    assert tailor_client.get("/v2/tailor").json()["stale_message"] == ""

    assert tailor_client.put("/v2/profile/summary", json={"summary": "Analyst who explains numbers plainly."}).status_code == 200
    item = tailor_client.get("/v2/batch").json()["batch"]["items"][0]
    assert item["stale"] is True and "changed after this was tailored" in item["stale_message"]
    assert "Tailor it again" in tailor_client.get("/v2/tailor").json()["stale_message"]
    (result,) = tailor_client.post("/v2/batch/prepare", json={}).json()["results"]
    assert result["status"] == "tailor_again"

    # Tailor again: a one-job batch, after which the review is current.
    r = tailor_client.post("/v2/batch/again", json={"job_id": "greenhouse_101"})
    assert r.status_code == 200, r.text
    batch = _wait(tailor_client)
    assert [i["job_id"] for i in batch["items"]] == ["greenhouse_101"] and batch["items"][0]["stale"] is False
    assert batch["summary"] == "1 of 1 tailored"  # the same batch, redone in place
    assert tailor_client.post("/v2/batch/again", json={"job_id": "nope_1"}).status_code == 404


def test_home_lists_every_batch_resume_awaiting_decisions(tailor_client, monkeypatch):  # noqa: F811
    # Dogfood, 2026-10-13: "Resumes awaiting your decisions" only showed the open job, so a batch of
    # several tailored resumes appeared on Home as one.
    from resume_tailorer.docx_export import pipeline

    from tests.e2e_server import fake_pdf

    monkeypatch.setattr(pipeline, "convert_docx_to_pdf", fake_pdf)
    _setup(tailor_client)
    pasted = tailor_client.post("/v2/tailor/pasted", json={
        "title": "Marketing Analyst", "company": "Bluebird Goods",
        "description": ("Marketing Analyst at Bluebird Goods. Requirements: SQL and dashboard reporting for business "
                        "partners, weekly KPI reporting, partnering with sales leaders, explaining trends to executives, "
                        "and keeping data definitions consistent across teams in a fast-growing company. You will also "
                        "own the quarterly business review deck and work closely with finance on forecasting.")}).json()
    tailor_client.post("/v2/batch/tailor", json={"job_ids": ["greenhouse_101", pasted["job"]["job_id"]]})
    assert all(i["status"] == "done" for i in _wait(tailor_client)["items"])
    drafts = tailor_client.get("/v2/home").json()["view"]["drafts"]
    titles = [d["title"] for d in drafts]
    assert "Senior Data Analyst" in titles and "Marketing Analyst" in titles and len(titles) == len(set(titles))


def test_home_keeps_two_batch_resumes_with_the_same_title(tailor_client, monkeypatch):  # noqa: F811
    # Code review, 2026-10-13: Home's batch list skipped a resume whose title was already shown, so the
    # same role at two companies appeared once.
    from resume_tailorer.docx_export import pipeline

    from tests.e2e_server import fake_pdf

    monkeypatch.setattr(pipeline, "convert_docx_to_pdf", fake_pdf)
    _setup(tailor_client)
    pasted = tailor_client.post("/v2/tailor/pasted", json={
        "title": "Senior Data Analyst", "company": "Bluebird Goods",
        "description": ("Senior Data Analyst at Bluebird Goods. Requirements: SQL and dashboard reporting for business "
                        "partners, weekly KPI reporting, partnering with sales leaders, explaining trends to executives, "
                        "and keeping data definitions consistent across teams in a fast-growing company. You will also "
                        "own the quarterly business review deck and work closely with finance on forecasting.")}).json()
    tailor_client.post("/v2/batch/tailor", json={"job_ids": ["greenhouse_101", pasted["job"]["job_id"]]})
    assert all(i["status"] == "done" for i in _wait(tailor_client)["items"])
    drafts = tailor_client.get("/v2/home").json()["view"]["drafts"]
    assert [d["title"] for d in drafts].count("Senior Data Analyst") == 2, drafts
