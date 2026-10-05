"""Workspace API, phase 4: Apply and Tracker (spec 009). Synthetic data only."""

import hashlib

from tests.test_workspace_jobs import jobs_client  # noqa: F401  (stubbed job boards)
from tests.workspace_helpers import resume_docx

REJECTION = """From: Gitlab Recruiting <no-reply@greenhouse.io>
Date: Thu, 1 Oct 2026 09:30:00 -0700
Subject: Your application to Gitlab

Thank you for applying for the Senior Data Analyst role at Gitlab. After careful review,
we have decided to move forward with other candidates.
"""


def _with_tailored_resume(client, tmp_path):
    """A job chosen in Jobs and a validated tailored PDF handed to Apply (as Tailor leaves it)."""
    from resume_tailorer.active_job import remember_handoff
    from resume_tailorer.profile_import import store_for

    client.post("/v2/profile/resume", files={"file": ("r.docx", resume_docx(), "application/octet-stream")})
    client.post("/v2/profile/confirm")
    client.post("/v2/jobs/search", json={"job_title": "Data Analyst"})
    client.post("/v2/jobs/greenhouse_101/action", json={"action": "apply"})
    pdf = tmp_path / "tailored.pdf"
    pdf.write_bytes(b"%PDF-1.4 synthetic")
    store = store_for("local")
    record = store.load()
    remember_handoff(record, {"job_id": "greenhouse_101", "pdf_path": str(pdf),
                              "sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(), "version": 2,
                              "validation_status": "PASS", "resume_match_score": 0.8}, True)
    store.save(record)


def test_apply_without_a_job_offers_the_next_step(jobs_client):  # noqa: F811
    page = jobs_client.get("/v2/apply").json()
    assert page["job"] is None and page["empty"]["action_page"] == "/jobs"


def test_ready_track_and_mark_applied(jobs_client, tmp_path):  # noqa: F811
    _with_tailored_resume(jobs_client, tmp_path)
    page = jobs_client.get("/v2/apply").json()
    assert page["view"]["stage"] == "ready" and page["view"]["can_track"] is True
    assert page["handoff"] == {"version": 2, "has_file": True}
    labels = {f["label"]: f for f in page["kit"]}
    assert labels["Email"]["value"] and labels["Resume"]["value"] == "tailored_resume_v2.pdf"
    assert '"jobCopilotKit": 1' in page["helper_code"]
    assert {m["name"]: m["available"] for m in page["view"]["modes"]}["Auto"] is False
    assert jobs_client.post("/v2/apply/applied").status_code == 409  # track first

    tracked = jobs_client.post("/v2/apply/track").json()
    assert tracked["view"]["stage"] == "tracked" and tracked["view"]["can_mark_applied"] is True
    assert jobs_client.post("/v2/apply/track").status_code == 409
    assert jobs_client.post("/v2/apply/applied").json()["view"]["stage"] == "applied"
    assert jobs_client.get("/v2/apply/resume").content.startswith(b"%PDF")


def test_tracker_views_detail_next_action_and_status(jobs_client, tmp_path):  # noqa: F811
    _with_tailored_resume(jobs_client, tmp_path)
    jobs_client.post("/v2/apply/track")
    board = jobs_client.get("/v2/tracker").json()
    assert board["total"] == 1 and board["rows"][0]["role"] == "Senior Data Analyst"
    app_id = board["rows"][0]["application_id"]

    detail = jobs_client.put(f"/v2/tracker/{app_id}/next-action",
                             json={"text": "Email the recruiter", "due": "2026-10-12", "notes": ""}).json()
    assert detail["next_action"] == {"text": "Email the recruiter", "due": "2026-10-12", "notes": ""}
    assert jobs_client.put(f"/v2/tracker/{app_id}/next-action", json={"due": "soon"}).status_code == 400

    moved = jobs_client.post(f"/v2/tracker/{app_id}/status", json={"status": "interview", "note": "Panel"}).json()
    assert moved["row"]["status"] == "interview" and moved["history"][0]["who"] == "you"
    assert jobs_client.post(f"/v2/tracker/{app_id}/status", json={"status": "interview"}).status_code == 400
    assert jobs_client.get("/v2/tracker/nope").status_code == 404
    assert jobs_client.put("/v2/tracker/weekly-goal", json={"goal": 4}).json() == {"weekly_goal": 4}
    assert jobs_client.post(f"/v2/tracker/{app_id}/retailor").json() == {"next": "/tailor"}


def test_a_pasted_email_is_only_a_suggestion_until_confirmed(jobs_client, tmp_path):  # noqa: F811
    _with_tailored_resume(jobs_client, tmp_path)
    jobs_client.post("/v2/apply/track")
    app_id = jobs_client.get("/v2/tracker").json()["rows"][0]["application_id"]
    reading = jobs_client.post("/v2/tracker/email/read", json={"text": REJECTION}).json()
    assert reading["status"] == "rejected" and reading["chosen"] == app_id and reading["email_date"] == "2026-10-01"
    assert jobs_client.get(f"/v2/tracker/{app_id}").json()["row"]["status"] == "ready_to_apply"
    confirmed = jobs_client.post("/v2/tracker/email/confirm", json={
        "application_id": app_id, "status": "rejected", "email_date": reading["email_date"], "evidence": reading["subject"]}).json()
    assert confirmed["row"]["status"] == "rejected"
    assert confirmed["history"][0]["who"] == "you, from an email" and "Oct 01, 2026" in confirmed["history"][0]["note"]
