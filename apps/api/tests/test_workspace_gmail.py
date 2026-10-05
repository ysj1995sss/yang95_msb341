"""Status from Gmail (spec 005 slice 2). Google's endpoints are stubbed; synthetic data only."""

import base64
import json
from unittest.mock import patch

import pytest

from tests.test_workspace_jobs import jobs_client  # noqa: F401
from tests.workspace_helpers import SECRET, resume_docx, token

REJECTION = ("Thank you for applying for the Senior Data Analyst role at GitLab. After careful review, "
             "we have decided to move forward with other candidates.")


class FakeResponse:
    def __init__(self, status, body):
        self.status_code, self._body = status, body

    def json(self):
        return self._body


class FakeGoogle:
    def __init__(self):
        self.revoked, self.queries = [], []

    def post(self, url, data=None, timeout=None):
        if url.endswith("/token"):
            ok = data.get("refresh_token") == "refresh-123"
            return FakeResponse(200 if ok else 400, {"access_token": "access-abc"} if ok else {})
        if url.endswith("/revoke"):
            self.revoked.append(data["token"])
            return FakeResponse(200, {})
        raise AssertionError(url)

    def get(self, url, params=None, headers=None, timeout=None):
        assert headers["Authorization"] == "Bearer access-abc"
        if url.endswith("/messages"):
            self.queries.append(params["q"])
            return FakeResponse(200, {"messages": [{"id": "m1"}, {"id": "m2"}]})
        body = base64.urlsafe_b64encode(REJECTION.encode()).decode() if url.endswith("/m1") else \
            base64.urlsafe_b64encode(b"Your weekly newsletter").decode()
        return FakeResponse(200, {"payload": {
            "headers": [{"name": "From", "value": "GitLab <no-reply@greenhouse.io>"},
                        {"name": "Date", "value": "Thu, 1 Oct 2026 09:30:00 -0700"},
                        {"name": "Subject", "value": "Your application to GitLab"}],
            "mimeType": "multipart/alternative",
            "parts": [{"mimeType": "text/plain", "body": {"data": body}}]}})


@pytest.fixture()
def gmail(jobs_client, monkeypatch):  # noqa: F811
    monkeypatch.setenv("WORKSPACE_TOKEN_SECRET", SECRET)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    google = FakeGoogle()
    with patch("app.workspace.gmail_router.requests", google):
        yield jobs_client, google


def test_gmail_needs_sign_in_and_a_client(jobs_client):  # noqa: F811
    assert jobs_client.get("/v2/gmail").json()["available"] is False


def test_connect_scan_confirm_dismiss_disconnect(gmail, tmp_path):
    client, google = gmail
    headers = {"Authorization": f"Bearer {token()}"}
    assert client.get("/v2/gmail", headers=headers).json() == {"available": True, "connected": False,
                                                               "connected_at": None, "last_scan": None}
    assert client.post("/v2/gmail/scan", headers=headers).status_code == 409
    client.post("/v2/gmail/connect", headers=headers, json={"refresh_token": "refresh-123"})
    from resume_tailorer.identity import user_dir
    from app.workspace.identity import owner_from_token

    owner = owner_from_token(token(), SECRET).owner_id
    stored = json.loads((user_dir(owner) / "gmail.json").read_text())
    assert "refresh-123" not in json.dumps(stored)  # encrypted at rest

    # A tracked application for this user, then a scan.
    client.post("/v2/profile/resume", headers=headers, files={"file": ("r.docx", resume_docx(), "application/octet-stream")})
    client.post("/v2/jobs/search", headers=headers, json={"job_title": "Data Analyst"})
    client.post("/v2/jobs/greenhouse_101/action", headers=headers, json={"action": "apply"})
    pdf = tmp_path / "t.pdf"
    pdf.write_bytes(b"%PDF-1.4 synthetic")
    from resume_tailorer.active_job import remember_handoff
    from resume_tailorer.profile_import import store_for
    import hashlib
    store = store_for(owner)
    record = store.load()
    remember_handoff(record, {"job_id": "greenhouse_101", "pdf_path": str(pdf), "sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
                              "version": 1, "validation_status": "PASS", "resume_match_score": 0.8}, True)
    store.save(record)
    assert client.post("/v2/apply/track", headers=headers).status_code == 200

    found = client.post("/v2/gmail/scan", headers=headers).json()["suggestions"]
    assert "from:(greenhouse.io" in google.queries[0] and "newer_than:30d" in google.queries[0]
    assert len(found) == 1 and found[0]["status"] == "rejected" and found[0]["chosen"]
    app_id = found[0]["chosen"]
    assert client.get(f"/v2/tracker/{app_id}", headers=headers).json()["row"]["status"] == "ready_to_apply"  # unchanged
    client.post("/v2/tracker/email/confirm", headers=headers, json={"application_id": app_id, "status": "rejected",
                                                                     "email_date": found[0]["email_date"], "evidence": found[0]["subject"]})
    client.post("/v2/gmail/dismiss", headers=headers, json={"message_id": "m1"})
    assert client.post("/v2/gmail/scan", headers=headers).json()["suggestions"] == []

    assert client.request("DELETE", "/v2/gmail", headers=headers).json()["connected"] is False
    assert google.revoked == ["refresh-123"]
