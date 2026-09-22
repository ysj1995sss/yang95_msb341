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
