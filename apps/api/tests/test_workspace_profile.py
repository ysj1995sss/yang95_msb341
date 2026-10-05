"""Workspace API, phase 1: identity, Home and Career Profile (spec 009)."""

from tests.workspace_helpers import SECRET, resume_docx, token


def _import(client):
    r = client.post("/v2/profile/resume", files={"file": ("riley.docx", resume_docx(), "application/octet-stream")})
    assert r.status_code == 200, r.text
    return r.json()


def test_local_mode_without_a_secret(workspace_client):
    assert workspace_client.get("/v2/me").json() == {"name": "Local user", "signed_in": False, "mode": "local"}


def test_signed_tokens_are_required_once_a_secret_is_set(workspace_client, monkeypatch):
    monkeypatch.setenv("WORKSPACE_TOKEN_SECRET", SECRET)
    assert workspace_client.get("/v2/me").status_code == 401
    assert workspace_client.get("/v2/me", headers={"Authorization": f"Bearer {token(secret='x' * 40)}"}).status_code == 401
    assert workspace_client.get("/v2/me", headers={"Authorization": f"Bearer {token(minutes=-1)}"}).status_code == 401
    me = workspace_client.get("/v2/me", headers={"Authorization": f"Bearer {token()}"}).json()
    assert me == {"name": "Riley Park", "signed_in": True, "mode": "google"}


def test_two_signed_in_users_never_share_a_profile(workspace_client, monkeypatch):
    monkeypatch.setenv("WORKSPACE_TOKEN_SECRET", SECRET)
    riley = {"Authorization": f"Bearer {token(sub='a')}"}
    sam = {"Authorization": f"Bearer {token(sub='b', name='Sam')}"}
    r = workspace_client.post("/v2/profile/resume", headers=riley,
                              files={"file": ("r.docx", resume_docx(), "application/octet-stream")})
    assert r.status_code == 200
    assert workspace_client.get("/v2/profile", headers=sam).json()["readiness"]["has_resume"] is False
    assert workspace_client.get("/v2/profile", headers=riley).json()["readiness"]["has_resume"] is True


def test_first_visit_home_asks_for_a_resume(workspace_client):
    home = workspace_client.get("/v2/home").json()
    assert home["view"]["mode"] == "first_time"
    assert home["view"]["next_action"]["inline"] == "upload"


def test_import_then_edit_then_confirm(workspace_client):
    view = _import(workspace_client)
    assert view["readiness"]["has_resume"] is True
    assert view["profile"]["contact_info"]["email"] == "riley@example.com"
    assert view["profile"]["work_experience"][0]["title"] == "Data Analyst"

    r = workspace_client.put("/v2/profile/contact", json={"name": "Riley Park", "email": "riley@example.com",
                                                          "phone": "555-0100", "location": "Boulder, CO"})
    assert r.json()["changed"] >= 1 and "contact_info.location" in r.json()["edited"]

    role = view["profile"]["work_experience"][0]
    r = workspace_client.put("/v2/profile/work", json={"index": 0, "title": role["title"], "employer": role["employer"],
                                                       "dates": role["dates"], "bullets": ["Built SQL dashboards"]})
    assert r.status_code == 200
    assert workspace_client.put("/v2/profile/work", json={"index": 9, "bullets": []}).status_code == 404

    confirmed = workspace_client.post("/v2/profile/confirm").json()
    assert confirmed["confirmed"] >= 1 and confirmed["readiness"]["facts_confirmed"] is True


def test_goals_and_authorization_are_only_what_the_user_chose(workspace_client):
    _import(workspace_client)
    assert workspace_client.put("/v2/profile/goals", json={"job_title": "  "}).status_code == 400
    view = workspace_client.put("/v2/profile/goals", json={"job_title": "Data Analyst", "remote_preference": "remote",
                                                           "authorized_to_work": True, "weekly_goal": 5}).json()
    assert view["preferences"]["job_title"] == "Data Analyst" and view["preferences"]["weekly_goal"] == 5
    assert view["authorization"] == {"authorized_to_work": True, "sponsorship_required": None}
    assert workspace_client.get("/v2/home").json()["weekly_goal"] == 5


def test_rejects_other_file_types(workspace_client):
    r = workspace_client.post("/v2/profile/resume", files={"file": ("x.exe", b"MZ", "application/octet-stream")})
    assert r.status_code == 400


def test_saved_answers(workspace_client):
    answers = workspace_client.post("/v2/answers", json={"question": "Why Acme?", "answer": "Analytics."}).json()
    key = answers["answers"][0]["question_key"]
    assert workspace_client.delete(f"/v2/answers/{key}").json()["answers"] == []
