from datetime import datetime, timedelta

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


def _job(company: str, title: str, **extra):
    base = {
        "company": company,
        "title": title,
        "location": "Remote",
        "description": "Looking for a backend engineer with Python and AWS experience.",
        "source": "api",
        "original_url": f"https://example.com/jobs/{company}",
        "discovered_at": "2026-09-21T00:00:00Z",
        "posted_at": datetime.utcnow().isoformat() + "Z",
        "salary": "$120K-$150K",
        "sponsorship": "yes",
        "work_mode": "remote",
    }
    base.update(extra)
    return base


def test_list_jobs_includes_quality_status(client):
    headers = auth_headers(client)
    client.put("/profile", json=_PROFILE, headers=headers)
    client.post("/jobs/upsert", json=_job("Globex", "Backend Engineer"), headers=headers)

    listed = client.get("/jobs", headers=headers)
    assert listed.status_code == 200
    items = listed.json()
    assert len(items) == 1
    assert items[0]["quality_status"] in {"active", "stale", "expired", "broken", "unknown"}


def test_list_jobs_filter_min_fit_and_keyword(client):
    headers = auth_headers(client)
    client.put("/profile", json=_PROFILE, headers=headers)
    client.post(
        "/jobs/upsert",
        json=_job("Globex", "Backend Engineer", description="Python FastAPI AWS"),
        headers=headers,
    )
    client.post(
        "/jobs/upsert",
        json=_job(
            "OtherCo",
            "Sales Manager",
            description="Enterprise sales quota hunting",
            source="linkedin",
        ),
        headers=headers,
    )

    listed = client.get("/jobs", headers=headers, params={"min_fit": 1, "keyword": "Backend"})
    assert listed.status_code == 200
    titles = [i["title"] for i in listed.json()]
    assert "Backend Engineer" in titles
    assert "Sales Manager" not in titles


def test_list_jobs_sort_by_company_asc(client):
    headers = auth_headers(client)
    client.put("/profile", json=_PROFILE, headers=headers)
    client.post("/jobs/upsert", json=_job("Zebra", "Engineer A"), headers=headers)
    client.post("/jobs/upsert", json=_job("Acme", "Engineer B"), headers=headers)

    listed = client.get(
        "/jobs",
        headers=headers,
        params={"sort_by": "company", "sort_dir": "asc"},
    )
    assert listed.status_code == 200
    companies = [i["company"] for i in listed.json()]
    assert companies == sorted(companies, key=str.casefold)


def test_list_jobs_filter_sponsorship_and_quality(client):
    headers = auth_headers(client)
    client.put("/profile", json=_PROFILE, headers=headers)
    client.post(
        "/jobs/upsert",
        json=_job("Sponsors", "Eng", sponsorship="yes"),
        headers=headers,
    )
    stale_posted = (datetime.utcnow() - timedelta(days=90)).isoformat() + "Z"
    client.post(
        "/jobs/upsert",
        json=_job("OldCo", "Eng Old", sponsorship="no", posted_at=stale_posted),
        headers=headers,
    )

    yes_only = client.get("/jobs", headers=headers, params={"sponsorship": "yes"})
    assert all(i["sponsorship"] == "yes" for i in yes_only.json())

    stale_only = client.get("/jobs", headers=headers, params={"quality": "stale"})
    assert stale_only.status_code == 200
    assert all(i["quality_status"] == "stale" for i in stale_only.json())
    assert any(i["company"] == "OldCo" for i in stale_only.json())
