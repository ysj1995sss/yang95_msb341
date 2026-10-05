"""Your data: export, delete, sign out everywhere (decision 030). Synthetic data only."""

import io
import zipfile

from tests.workspace_helpers import SECRET, resume_docx, token


def _signed(sub="google-riley", sv=None):
    from datetime import datetime, timedelta, timezone

    from jose import jwt

    claims = {"sub": sub, "name": "Riley", "aud": "job-copilot-workspace",
              "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}
    if sv is not None:
        claims["sv"] = sv
    return {"Authorization": "Bearer " + jwt.encode(claims, SECRET, algorithm="HS256")}


def test_export_contains_everything_stored(workspace_client):
    workspace_client.post("/v2/profile/resume", files={"file": ("r.docx", resume_docx(), "application/octet-stream")})
    workspace_client.post("/v2/answers", json={"question": "Why us?", "answer": "Because."})
    r = workspace_client.get("/v2/account/export")
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    names = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
    assert "profile/career_profile.json" in names and "applications.db" in names and "README.txt" in names
    assert any(n.startswith("profile/resume_v1") for n in names)


def test_delete_removes_everything_and_needs_confirmation(workspace_client):
    from resume_tailorer.identity import data_root

    workspace_client.post("/v2/profile/resume", files={"file": ("r.docx", resume_docx(), "application/octet-stream")})
    assert workspace_client.request("DELETE", "/v2/account", json={"confirm": "yes"}).status_code == 400
    assert workspace_client.request("DELETE", "/v2/account", json={"confirm": "DELETE"}).json() == {"deleted": True}
    assert not (data_root() / "users" / "local" / "profile").exists()
    assert workspace_client.get("/v2/profile").json()["readiness"]["has_resume"] is False


def test_sign_out_everywhere_rejects_older_sessions(workspace_client, monkeypatch):
    monkeypatch.setenv("WORKSPACE_TOKEN_SECRET", SECRET)
    assert workspace_client.get("/v2/me", headers=_signed()).status_code == 200
    assert workspace_client.get("/v2/account/session-version", headers=_signed()).json() == {"session_version": 0}
    assert workspace_client.post("/v2/account/sign-out-everywhere", headers=_signed()).json() == {"signed_out": True}
    assert workspace_client.get("/v2/me", headers=_signed()).status_code == 401  # old session
    assert workspace_client.get("/v2/account/session-version", headers=_signed()).json() == {"session_version": 1}
    assert workspace_client.get("/v2/me", headers=_signed(sv=1)).status_code == 200  # a new sign-in
    assert workspace_client.get("/v2/me", headers=_signed(sub="google-sam")).status_code == 200  # others unaffected


def test_local_mode_has_no_other_sessions(workspace_client):
    assert workspace_client.post("/v2/account/sign-out-everywhere").status_code == 400
