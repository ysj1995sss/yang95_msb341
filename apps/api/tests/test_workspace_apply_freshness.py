"""Single Apply must not bypass the profile-change guard enforced by batch Prepare."""

import json

import pytest

from tests.test_workspace_jobs import jobs_client  # noqa: F401
from tests.test_workspace_tailor import _ready, _run, tailor_client  # noqa: F401


def _reviewed_resume(client, monkeypatch):
    from tests.e2e_server import fake_pdf

    monkeypatch.setattr("resume_tailorer.docx_export.pipeline.convert_docx_to_pdf", fake_pdf)
    _ready(client)
    client.post("/v2/profile/confirm")
    assert _run(client)["status"] == "done"
    review = client.get("/v2/tailor").json()["review"]
    for change in review["changes"]:
        assert client.post("/v2/tailor/decisions", json={
            "change_id": change["id"], "decision": "ACCEPTED",
        }).status_code == 200
    assert client.post("/v2/tailor/rebuild").json()["progress"]["can_continue"] is True


def _edit_profile(client):
    assert client.put("/v2/profile/summary", json={
        "summary": "Analyst who explains numbers plainly.",
    }).status_code == 200
    assert "changed after this was tailored" in client.get("/v2/tailor").json()["stale_message"]


def test_stale_apply_withholds_the_old_resume_and_helper_attachment(tailor_client, monkeypatch):  # noqa: F811
    _reviewed_resume(tailor_client, monkeypatch)
    _edit_profile(tailor_client)

    page = tailor_client.get("/v2/apply").json()
    assert page["view"]["can_open"] is True  # the person may still visit the employer
    assert page["view"]["can_track"] is False
    assert page["handoff"] is None
    assert any("Tailor it again" in item["detail"] for item in page["view"]["checklist"])
    assert next(field for field in page["kit"] if field["label"] == "Resume")["value"] == ""
    assert "resume" not in json.loads(page["helper_code"])
    download = tailor_client.get("/v2/apply/resume")
    assert download.status_code == 409 and "Tailor it again" in download.json()["detail"]


def test_profile_edit_after_ready_page_blocks_track_without_a_record(tailor_client, monkeypatch):  # noqa: F811
    _reviewed_resume(tailor_client, monkeypatch)
    assert tailor_client.get("/v2/apply").json()["view"]["can_track"] is True
    _edit_profile(tailor_client)  # another tab can edit after the readiness page was loaded

    result = tailor_client.post("/v2/apply/track")
    assert result.status_code == 409 and "Tailor it again" in result.json()["detail"]
    assert tailor_client.get("/v2/tracker").json()["total"] == 0


@pytest.mark.parametrize("version", ["absent", None])
def test_legacy_and_one_off_reviews_keep_their_existing_apply_behavior(tailor_client, monkeypatch, version):  # noqa: F811
    from resume_tailorer.identity import artifacts_dir
    from resume_tailorer.review_store import load_review, save_review

    _reviewed_resume(tailor_client, monkeypatch)
    folder = artifacts_dir("local")
    state = load_review(folder, "greenhouse_101")
    if version == "absent":
        state.pop("profile_version")  # pre-spec-014 review
    else:
        state["profile_version"] = None  # one-off file; no relationship to the Career Profile
    assert save_review(folder, "greenhouse_101", state)
    assert tailor_client.put("/v2/profile/summary", json={"summary": "Changed profile."}).status_code == 200

    page = tailor_client.get("/v2/apply").json()
    assert page["view"]["can_track"] is True
    assert tailor_client.get("/v2/apply/resume").status_code == 200
    assert tailor_client.post("/v2/apply/track").status_code == 200


def test_retailoring_in_a_batch_does_not_make_the_old_active_pdf_current(tailor_client, monkeypatch):  # noqa: F811
    from resume_tailorer.identity import artifacts_dir
    from resume_tailorer.review_store import load_review
    from tests.test_workspace_batch import _wait

    _reviewed_resume(tailor_client, monkeypatch)
    old_pdf = tailor_client.get("/v2/apply/resume").content
    contact = tailor_client.get("/v2/profile").json()["profile"]["contact_info"]
    assert tailor_client.put("/v2/profile/contact", json={
        **contact, "email": "updated@example.com",
    }).status_code == 200
    assert tailor_client.post("/v2/batch/again", json={"job_id": "greenhouse_101"}).status_code == 200
    assert _wait(tailor_client)["items"][0]["status"] == "done"
    state = load_review(artifacts_dir("local"), "greenhouse_101")
    assert state["pdf_bytes"] != old_pdf
    assert tailor_client.get("/v2/tailor").json()["stale_message"] == ""  # the new review is current

    page = tailor_client.get("/v2/apply").json()
    assert page["view"]["can_open"] and not page["view"]["can_track"]
    assert page["handoff"] is None
    assert any("Open Tailor" in item["detail"] for item in page["view"]["checklist"])
    assert "resume" not in json.loads(page["helper_code"])
    assert tailor_client.get("/v2/apply/resume").status_code == 409
    assert tailor_client.post("/v2/apply/track").status_code == 409
    assert tailor_client.get("/v2/tracker").json()["total"] == 0

    # Opening the saved review publishes that review's artifact instead of the old active one.
    assert tailor_client.post("/v2/batch/open", json={"job_id": "greenhouse_101"}).status_code == 200
    assert tailor_client.get("/v2/apply/resume").content == state["pdf_bytes"]


def test_a_stale_review_is_not_called_ready_for_apply(tailor_client, monkeypatch):  # noqa: F811
    """Dogfood, 2026-10-13: after a profile edit Tailor still said "Your resume is ready for Apply" and
    offered Continue, while Apply refused the old resume. Tailor uses the same freshness rule."""
    _reviewed_resume(tailor_client, monkeypatch)
    _edit_profile(tailor_client)
    progress = tailor_client.get("/v2/tailor").json()["review"]["progress"]
    assert progress["can_continue"] is False and "changed after this was tailored" in progress["blocker"]


def test_the_tailor_page_checks_freshness_once(tailor_client, monkeypatch):  # noqa: F811
    # Code review, 2026-10-13: the page and its review each loaded the profile to check freshness.
    import resume_tailorer.freshness as freshness

    _reviewed_resume(tailor_client, monkeypatch)
    calls = []
    real = freshness.review_freshness
    monkeypatch.setattr(freshness, "review_freshness", lambda *a, **k: calls.append(1) or real(*a, **k))
    tailor_client.get("/v2/tailor")
    assert len(calls) == 1
