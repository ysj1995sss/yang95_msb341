import io

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

from app.main import app
from app.tailor.router import get_optimizer
from tests.conftest import auth_headers

from resume_tailorer.tailorer.optimizer import OptimizationResult

_PROFILE = {
    "contact_info": {"name": "Jane Doe", "email": "jane@example.com", "phone": "", "location": ""},
    "education": [],
    "work_experience": [
        {
            "employer": "Acme Corp",
            "title": "Backend Engineer",
            "dates": "2020-2023",
            "responsibilities": ["Built REST APIs with Python and FastAPI"],
            "accomplishments": ["Deployed services on AWS"],
        }
    ],
    "skills": ["Python", "FastAPI"],
    "tools": ["Docker", "AWS"],
    "certifications": [],
    "accomplishments": [],
}


class _FakeTailorer:
    def tailor(self, profile, job_analysis, gap_report):
        return "Initial tailored resume draft."


class _FakeOptimizer:
    def __init__(self):
        self.tailorer = _FakeTailorer()

    def optimize(self, profile, job_analysis, initial_tailored, gap_report):
        return OptimizationResult(
            tailored_resume="- Built REST APIs with Python and FastAPI\n- Deployed services on AWS",
            final_score=0.9,
            iterations=2,
            ceiling_reached=False,
            missing_qualifications=[],
        )


def test_tailor_preview_rejects_a_too_sparse_profile(client):
    """
    Safety gate added after a real failure (2026-09-22): a profile with no
    skills and no work-experience content must be refused before ever
    calling the LLM, not handed to it to fill in the gaps.
    """
    headers = auth_headers(client)
    client.put(
        "/profile",
        json={
            "contact_info": {"name": "Empty Profile", "email": "empty@example.com", "phone": "", "location": ""},
            "education": [],
            "work_experience": [],
            "skills": [],
            "tools": [],
            "certifications": [],
            "accomplishments": [],
        },
        headers=headers,
    )

    app.dependency_overrides[get_optimizer] = lambda: _FakeOptimizer()
    try:
        r = client.post("/tailor/preview", json={"job_description": "Need Python."}, headers=headers)
    finally:
        app.dependency_overrides.pop(get_optimizer, None)

    assert r.status_code == 422


def test_tailor_preview_requires_profile(client):
    headers = auth_headers(client)
    app.dependency_overrides[get_optimizer] = lambda: _FakeOptimizer()
    try:
        r = client.post("/tailor/preview", json={"job_description": "Need Python and AWS."}, headers=headers)
    finally:
        app.dependency_overrides.pop(get_optimizer, None)
    assert r.status_code == 400


def test_tailor_preview_returns_gap_report_and_diff(client):
    headers = auth_headers(client)
    client.put("/profile", json=_PROFILE, headers=headers)

    app.dependency_overrides[get_optimizer] = lambda: _FakeOptimizer()
    try:
        r = client.post(
            "/tailor/preview",
            json={"job_description": "Required: Python, AWS, Kubernetes experience."},
            headers=headers,
        )
    finally:
        app.dependency_overrides.pop(get_optimizer, None)

    assert r.status_code == 200
    data = r.json()
    assert "Built REST APIs" in data["tailored_resume"]
    assert data["final_score"] == 0.9
    assert data["iterations"] == 2
    assert 0.0 <= data["original_match_score"] <= 1.0
    assert any(g["requirement"] for g in data["gaps"])
    assert data["pdf_base64"] is None  # generate_pdf defaults to False


def test_tailor_preview_can_generate_a_real_pdf(client):
    headers = auth_headers(client)
    client.put("/profile", json=_PROFILE, headers=headers)

    app.dependency_overrides[get_optimizer] = lambda: _FakeOptimizer()
    try:
        r = client.post(
            "/tailor/preview",
            json={"job_description": "Required: Python, AWS.", "generate_pdf": True},
            headers=headers,
        )
    finally:
        app.dependency_overrides.pop(get_optimizer, None)

    assert r.status_code == 200
    data = r.json()
    assert data["pdf_base64"], "expected a real generated PDF"


def test_tailor_preview_includes_candidate_fit_score(client):
    """Spec 001 item 8/19: Candidate Fit should be reported, not just resume match."""
    headers = auth_headers(client)
    client.put("/profile", json=_PROFILE, headers=headers)

    app.dependency_overrides[get_optimizer] = lambda: _FakeOptimizer()
    try:
        r = client.post(
            "/tailor/preview",
            json={"job_description": "Required: Python, AWS, 2+ years experience."},
            headers=headers,
        )
    finally:
        app.dependency_overrides.pop(get_optimizer, None)

    assert r.status_code == 200
    data = r.json()
    assert data["candidate_fit_score"] is not None
    assert data["candidate_fit_score"] > 0


class _FakeOptimizerWithUnsupportedClaim:
    """A tailorer/optimizer whose output adds a term the profile doesn't
    support, to test the unsupported_claims_added detector end-to-end."""

    def __init__(self):
        self.tailorer = _FakeTailorer()

    def optimize(self, profile, job_analysis, initial_tailored, gap_report):
        return OptimizationResult(
            tailored_resume="- Built REST APIs with Python and FastAPI\n- Deployed on Kubernetes",
            final_score=0.7,
            iterations=1,
            ceiling_reached=True,
            missing_qualifications=[],
        )


def test_tailor_preview_flags_unsupported_claims(client):
    """_PROFILE has no Kubernetes anywhere -- if it shows up in the tailored
    output anyway, the API must surface it, not silently accept it."""
    headers = auth_headers(client)
    client.put("/profile", json=_PROFILE, headers=headers)

    app.dependency_overrides[get_optimizer] = lambda: _FakeOptimizerWithUnsupportedClaim()
    try:
        r = client.post(
            "/tailor/preview",
            json={"job_description": "Required: Python, Kubernetes experience."},
            headers=headers,
        )
    finally:
        app.dependency_overrides.pop(get_optimizer, None)

    assert r.status_code == 200
    data = r.json()
    assert "Kubernetes" in data["unsupported_claims_added"]


def test_tailor_preview_uses_stored_original_for_style_hints_without_crashing(client):
    """Once a real original resume is stored (spec item 1), PDF generation
    should use it for style hints (spec item 16) and must not blow up if the
    stored file can't be parsed cleanly."""
    headers = auth_headers(client)
    client.put("/profile", json=_PROFILE, headers=headers)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    c.drawString(72, 750, "- Some bullet from the original resume")
    c.save()
    client.post(
        "/profile/upload",
        files={"file": ("resume.pdf", buf.getvalue(), "application/pdf")},
        headers=headers,
    )
    # /profile/upload overwrites the parsed profile too -- put the richer
    # test profile back so the tailoring pipeline has real content to work with.
    client.put("/profile", json=_PROFILE, headers=headers)

    app.dependency_overrides[get_optimizer] = lambda: _FakeOptimizer()
    try:
        r = client.post(
            "/tailor/preview",
            json={"job_description": "Required: Python, AWS.", "generate_pdf": True},
            headers=headers,
        )
    finally:
        app.dependency_overrides.pop(get_optimizer, None)

    assert r.status_code == 200
    assert r.json()["pdf_base64"]


def test_tailor_preview_without_llm_config_returns_503(client, monkeypatch):
    headers = auth_headers(client)
    client.put("/profile", json=_PROFILE, headers=headers)

    # Explicitly unset rather than relying on the test environment's ambient
    # state: apps/api/.env may hold real dev credentials (pydantic-settings
    # loading it as a side effect leaks LLM_MODEL/LLM_API_KEY into
    # os.environ for the whole process), so this test previously passed or
    # failed depending on whether a developer happened to have that file
    # configured locally -- a real test-isolation bug, not just a stale
    # assertion.
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_BASE", raising=False)

    # No dependency override: get_optimizer() builds the real
    # ResumeTailoringOptimizer(), which requires LLM_MODEL/LLM_API_KEY.
    # Unset here, so it should fail clearly (503), not 500.
    r = client.post("/tailor/preview", json={"job_description": "Need Python."}, headers=headers)
    assert r.status_code == 503
