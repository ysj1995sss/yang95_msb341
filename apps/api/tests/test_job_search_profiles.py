from tests.conftest import auth_headers


def test_create_and_list_job_search_profiles(client):
    headers = auth_headers(client)
    r = client.post(
        "/job-search-profiles",
        json={"name": "Marketing - Dallas", "goals": {"titles": ["Marketing Manager"], "locations": ["Dallas, TX"]}},
        headers=headers,
    )
    assert r.status_code == 201
    created = r.json()
    assert created["name"] == "Marketing - Dallas"
    assert created["status"] == "active"
    assert created["goals"]["titles"] == ["Marketing Manager"]

    r = client.get("/job-search-profiles", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_multiple_profiles_coexist_independently(client):
    """The core Step 3 gap: unlike the single-row Goals table, a user must
    be able to have several named profiles at once."""
    headers = auth_headers(client)
    client.post("/job-search-profiles", json={"name": "Marketing - Dallas", "goals": {}}, headers=headers)
    client.post("/job-search-profiles", json={"name": "Strategy - Nationwide", "goals": {}}, headers=headers)
    client.post("/job-search-profiles", json={"name": "Product Marketing - Remote", "goals": {}}, headers=headers)

    r = client.get("/job-search-profiles", headers=headers)
    names = {p["name"] for p in r.json()}
    assert names == {"Marketing - Dallas", "Strategy - Nationwide", "Product Marketing - Remote"}


def test_update_job_search_profile(client):
    headers = auth_headers(client)
    created = client.post(
        "/job-search-profiles", json={"name": "Draft", "goals": {"titles": ["Analyst"]}}, headers=headers
    ).json()

    r = client.put(
        f"/job-search-profiles/{created['id']}",
        json={"name": "Analyst - Remote", "goals": {"titles": ["Analyst"], "work_arrangements": ["remote"]}},
        headers=headers,
    )
    assert r.status_code == 200
    updated = r.json()
    assert updated["name"] == "Analyst - Remote"
    assert updated["goals"]["work_arrangements"] == ["remote"]


def test_pause_and_activate_job_search_profile(client):
    headers = auth_headers(client)
    created = client.post("/job-search-profiles", json={"name": "P1", "goals": {}}, headers=headers).json()

    r = client.post(f"/job-search-profiles/{created['id']}/pause", headers=headers)
    assert r.json()["status"] == "paused"

    r = client.post(f"/job-search-profiles/{created['id']}/activate", headers=headers)
    assert r.json()["status"] == "active"


def test_duplicate_job_search_profile(client):
    headers = auth_headers(client)
    created = client.post(
        "/job-search-profiles", json={"name": "Original", "goals": {"titles": ["PM"]}}, headers=headers
    ).json()

    r = client.post(f"/job-search-profiles/{created['id']}/duplicate", headers=headers)
    assert r.status_code == 201
    copy = r.json()
    assert copy["id"] != created["id"]
    assert copy["name"] == "Original (copy)"
    assert copy["goals"]["titles"] == ["PM"]

    r = client.get("/job-search-profiles", headers=headers)
    assert len(r.json()) == 2


def test_delete_job_search_profile(client):
    headers = auth_headers(client)
    created = client.post("/job-search-profiles", json={"name": "Temp", "goals": {}}, headers=headers).json()

    r = client.delete(f"/job-search-profiles/{created['id']}", headers=headers)
    assert r.status_code == 204

    r = client.get("/job-search-profiles", headers=headers)
    assert r.json() == []


def test_profile_not_found_for_other_user(client):
    headers_a = auth_headers(client, email="a@example.com")
    headers_b = auth_headers(client, email="b@example.com")
    created = client.post("/job-search-profiles", json={"name": "A's profile", "goals": {}}, headers=headers_a).json()

    r = client.get(f"/job-search-profiles/{created['id']}", headers=headers_b)
    assert r.status_code == 404


def test_goals_endpoint_still_works_unaffected(client):
    """Backward compatibility: the pre-existing single-profile /goals
    endpoint (used by jobs/ranking.py) must be completely untouched by the
    new multi-profile resource."""
    headers = auth_headers(client)
    r = client.put("/goals", json={"titles": ["Old Endpoint Role"], "exclude_companies": ["Foo Inc"]}, headers=headers)
    assert r.status_code == 200
    r = client.get("/goals", headers=headers)
    assert r.json()["titles"] == ["Old Endpoint Role"]
    assert r.json()["exclude_companies"] == ["Foo Inc"]
