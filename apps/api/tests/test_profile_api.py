import io

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

from tests.conftest import auth_headers


def _fake_resume_pdf_bytes() -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    lines = [
        "Jane Doe",
        "jane.doe@example.com",
        "",
        "EDUCATION",
        "BS Computer Science",
        "MIT | 2020",
        "",
        "WORK EXPERIENCE",
        "Backend Engineer",
        "Acme Corp | Remote | Jan 2020 - Present",
        "- Built REST APIs with Python and FastAPI",
        "- Increased throughput by 40%",
        "",
        "SKILLS",
        "Python, FastAPI, SQL",
    ]
    y = 750
    for line in lines:
        c.drawString(72, y, line)
        y -= 18
    c.save()
    return buf.getvalue()


def test_upload_resume_extracts_real_structure(client):
    headers = auth_headers(client)
    pdf_bytes = _fake_resume_pdf_bytes()

    r = client.post(
        "/profile/upload",
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["contact_info"]["email"] == "jane.doe@example.com"
    assert "Python" in data["skills"]

    r2 = client.get("/profile", headers=headers)
    assert r2.status_code == 200
    assert r2.json()["contact_info"]["email"] == "jane.doe@example.com"


def test_upload_preserves_original_file_bytes(client):
    """Spec 001 item 1: 'Original resume is preserved and never overwritten.'
    Uploading must not just parse-and-discard -- the raw bytes must be
    retrievable byte-for-byte afterward."""
    headers = auth_headers(client)
    pdf_bytes = _fake_resume_pdf_bytes()

    r = client.post(
        "/profile/upload",
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
        headers=headers,
    )
    assert r.status_code == 200

    original = client.get("/profile/original", headers=headers)
    assert original.status_code == 200
    assert original.content == pdf_bytes
    assert original.headers["content-type"] == "application/pdf"
    assert "resume.pdf" in original.headers["content-disposition"]


def test_get_original_resume_404_when_none_uploaded(client):
    headers = auth_headers(client)
    r = client.get("/profile/original", headers=headers)
    assert r.status_code == 404


def test_reuploading_replaces_the_stored_original(client):
    headers = auth_headers(client)
    first = _fake_resume_pdf_bytes()
    client.post("/profile/upload", files={"file": ("resume.pdf", first, "application/pdf")}, headers=headers)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    c.drawString(72, 750, "Second Resume")
    c.save()
    second = buf.getvalue()
    client.post("/profile/upload", files={"file": ("resume_v2.pdf", second, "application/pdf")}, headers=headers)

    original = client.get("/profile/original", headers=headers)
    assert original.content == second
    assert "resume_v2.pdf" in original.headers["content-disposition"]


def test_reuploading_archives_the_previous_version_instead_of_losing_it(client):
    """The old row is still replaced (test_reuploading_replaces_the_stored_
    original), but its bytes must survive somewhere -- spec 001's version
    history requirement."""
    headers = auth_headers(client)
    first = _fake_resume_pdf_bytes()
    client.post("/profile/upload", files={"file": ("resume_v1.pdf", first, "application/pdf")}, headers=headers)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    c.drawString(72, 750, "Second Resume")
    c.save()
    second = buf.getvalue()
    client.post("/profile/upload", files={"file": ("resume_v2.pdf", second, "application/pdf")}, headers=headers)

    versions = client.get("/profile/resume-versions", headers=headers).json()
    assert len(versions) == 2
    current = next(v for v in versions if v["is_current"])
    archived = next(v for v in versions if not v["is_current"])
    assert current["filename"] == "resume_v2.pdf"
    assert current["version"] == 2
    assert archived["filename"] == "resume_v1.pdf"
    assert archived["version"] == 1


def test_resume_meta_reports_hash_size_and_version(client):
    headers = auth_headers(client)
    raw = _fake_resume_pdf_bytes()
    client.post("/profile/upload", files={"file": ("resume.pdf", raw, "application/pdf")}, headers=headers)

    meta = client.get("/profile/resume-meta", headers=headers).json()
    import hashlib

    assert meta["sha256"] == hashlib.sha256(raw).hexdigest()
    assert meta["size_bytes"] == len(raw)
    assert meta["version"] == 1
    assert meta["id"] is not None

    client.post("/profile/upload", files={"file": ("resume.pdf", raw, "application/pdf")}, headers=headers)
    meta2 = client.get("/profile/resume-meta", headers=headers).json()
    assert meta2["version"] == 2
    assert meta2["id"] != meta["id"]


def test_upload_rejects_empty_file(client):
    headers = auth_headers(client)
    r = client.post("/profile/upload", files={"file": ("resume.pdf", b"", "application/pdf")}, headers=headers)
    assert r.status_code == 400


def test_upload_rejects_oversized_file(client, monkeypatch):
    import app.profile.router as profile_router_module

    monkeypatch.setattr(profile_router_module, "_MAX_UPLOAD_BYTES", 10)
    headers = auth_headers(client)
    r = client.post(
        "/profile/upload",
        files={"file": ("resume.pdf", b"x" * 100, "application/pdf")},
        headers=headers,
    )
    assert r.status_code == 400


def test_upload_rejects_unsupported_extension(client):
    headers = auth_headers(client)
    r = client.post(
        "/profile/upload",
        files={"file": ("resume.txt", b"hello", "text/plain")},
        headers=headers,
    )
    assert r.status_code == 400


def test_put_and_get_profile(client):
    headers = auth_headers(client)
    body = {
        "contact_info": {"name": "Jane", "email": "jane@example.com", "phone": "", "location": ""},
        "education": [],
        "work_experience": [],
        "skills": ["Strategy"],
        "tools": [],
        "certifications": [],
        "accomplishments": [],
    }
    r = client.put("/profile", json=body, headers=headers)
    assert r.status_code == 200
    assert r.json()["skills"] == ["Strategy"]
    r2 = client.get("/profile", headers=headers)
    assert r2.json()["skills"] == ["Strategy"]


def test_new_skill_added_via_put_becomes_user_verified(client):
    """The realistic flow: upload establishes a resume_verified baseline
    (verification map empty), then a user's edit of just ONE field is the
    only thing that gets tagged."""
    headers = auth_headers(client)
    client.post(
        "/profile/upload",
        files={"file": ("resume.pdf", _fake_resume_pdf_bytes(), "application/pdf")},
        headers=headers,
    )
    assert client.get("/profile/verification", headers=headers).json() == {}

    parsed = client.get("/profile", headers=headers).json()
    with_new_skill = {**parsed, "skills": [*parsed["skills"], "Power BI"]}
    client.put("/profile", json=with_new_skill, headers=headers)

    verification = client.get("/profile/verification", headers=headers).json()
    new_skill_index = len(parsed["skills"])
    assert verification == {f"skills[{new_skill_index}]": "user_verified"}


def test_reuploading_resets_verification_state(client):
    headers = auth_headers(client)
    body = {
        "contact_info": {"name": "Jane", "email": "jane@example.com", "phone": "", "location": ""},
        "education": [],
        "work_experience": [],
        "skills": ["Excel"],
        "tools": [],
        "certifications": [],
        "accomplishments": [],
    }
    client.put("/profile", json=body, headers=headers)
    client.put("/profile", json={**body, "skills": ["Excel", "SQL"]}, headers=headers)
    assert client.get("/profile/verification", headers=headers).json() != {}

    client.post(
        "/profile/upload",
        files={"file": ("resume.pdf", _fake_resume_pdf_bytes(), "application/pdf")},
        headers=headers,
    )
    assert client.get("/profile/verification", headers=headers).json() == {}


def test_unchanged_field_keeps_no_verification_tag(client):
    """A field that's identical between old and new PUT bodies is
    resume_verified (absent from the map), not user_verified -- only
    genuinely new/changed facts get tagged."""
    headers = auth_headers(client)
    client.post(
        "/profile/upload",
        files={"file": ("resume.pdf", _fake_resume_pdf_bytes(), "application/pdf")},
        headers=headers,
    )
    parsed = client.get("/profile", headers=headers).json()
    client.put("/profile", json=parsed, headers=headers)
    assert client.get("/profile/verification", headers=headers).json() == {}
