from app.db import get_db
from app.main import app
from app.models import Job
from tests.conftest import auth_headers

_JOB = {
    "company": "Globex",
    "title": "Product Manager",
    "location": "Remote",
    "description": "PM role.",
    "source": "api",
    "original_url": "https://careers.example.com/job/?gh_jid=111",
    "discovered_at": "2026-09-21T00:00:00Z",
}


def test_upsert_rekeys_legacy_row_and_keeps_triage_state(client):
    headers = auth_headers(client)
    first = client.post("/jobs/upsert", json=_JOB, headers=headers).json()
    assert client.post(f"/jobs/{first['job_id']}/state", json={"state": "save"}, headers=headers).status_code == 200

    # Simulate a row stored before query params were part of the key.
    db = next(app.dependency_overrides[get_db]())
    row = db.get(Job, first["job_id"])
    row.dedupe_key = "url:https://careers.example.com/job"
    db.commit()

    again = client.post("/jobs/upsert", json=_JOB, headers=headers).json()
    assert again["job_id"] == first["job_id"]
    assert again["created"] is False
    db.expire_all()
    assert db.get(Job, first["job_id"]).dedupe_key == "url:https://careers.example.com/job?gh_jid=111"

    items = client.get("/jobs", headers=headers).json()
    assert len(items) == 1


def test_distinct_query_param_jobs_stay_separate(client):
    headers = auth_headers(client)
    a = client.post("/jobs/upsert", json=_JOB, headers=headers).json()
    b = client.post("/jobs/upsert", json={**_JOB, "original_url": "https://careers.example.com/job/?gh_jid=222"}, headers=headers).json()
    assert a["job_id"] != b["job_id"]
