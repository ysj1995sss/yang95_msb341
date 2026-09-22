from tests.conftest import auth_headers

_PROFILE = {
    "contact_info": {"name": "Jane Doe", "email": "jane@example.com", "phone": "", "location": ""},
    "education": [{"degree": "BS", "field": "Computer Science", "institution": "MIT", "year": 2020}],
    "work_experience": [
        {
            "employer": "Acme Corp",
            "title": "Backend Engineer",
            "dates": "2020-2023",
            "responsibilities": ["Built REST APIs with Python"],
            "accomplishments": ["Increased throughput 40%"],
        }
    ],
    "skills": ["Python", "FastAPI", "AWS"],
    "tools": ["Docker"],
    "certifications": [],
    "accomplishments": [],
}

_JOB = {
    "company": "Globex",
    "title": "Backend Engineer",
    "location": "Remote",
    "description": "Looking for a backend engineer with Python and AWS experience. 3-5 years required.",
    "source": "api",
    "original_url": "https://example.com/jobs/1",
    "discovered_at": "2026-09-21T00:00:00Z",
}


def test_upsert_job_scores_fit_using_candidate_fit_scorer(client):
    headers = auth_headers(client)
    client.put("/profile", json=_PROFILE, headers=headers)

    r = client.post("/jobs/upsert", json=_JOB, headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["created"] is True

    listed = client.get("/jobs", headers=headers)
    assert listed.status_code == 200
    items = listed.json()
    assert len(items) == 1
    # Python + AWS overlap with the profile's skills -- fit score should be > 0.
    assert items[0]["fit_score"] > 0


def test_upsert_job_without_profile_scores_zero(client):
    headers = auth_headers(client)
    r = client.post("/jobs/upsert", json=_JOB, headers=headers)
    assert r.status_code == 200
    listed = client.get("/jobs", headers=headers)
    assert listed.json()[0]["fit_score"] == 0.0
