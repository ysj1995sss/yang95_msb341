"""Task 7: preview persists a run; review dispositions + regenerate."""

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
    def tailor(self, profile, job_analysis, gap_report, conservative=False):
        return "Initial tailored resume draft."


class _FakeOptimizer:
    """Rephrases the one real accomplishment so build_freeform_changes has
    a genuine, similarity-matched (original, tailored) pair to review --
    not a fresh bullet SequenceMatcher would treat as pure addition."""

    def __init__(self):
        self.tailorer = _FakeTailorer()

    def optimize(self, profile, job_analysis, initial_tailored, gap_report, conservative=False):
        return OptimizationResult(
            tailored_resume=(
                "Jane Doe\n"
                "jane@example.com\n\n"
                "EXPERIENCE\n"
                "Acme Corp | Backend Engineer\n"
                "2020-2023\n"
                "- Built REST APIs with Python and FastAPI\n"
                "- Deployed cloud services on AWS infrastructure"
            ),
            final_score=0.9,
            iterations=1,
            ceiling_reached=False,
            missing_qualifications=[],
        )

    def _score_resume(self, resume_text, job_analysis, profile=None):
        return 0.5, [], []


def _preview(client, headers):
    app.dependency_overrides[get_optimizer] = lambda: _FakeOptimizer()
    try:
        return client.post(
            "/tailor/preview",
            json={"job_description": "Required: Python, AWS."},
            headers=headers,
        )
    finally:
        app.dependency_overrides.pop(get_optimizer, None)


def test_preview_persists_run_and_keeps_legacy_fields(client):
    headers = auth_headers(client)
    client.put("/profile", json=_PROFILE, headers=headers)

    r = _preview(client, headers)
    assert r.status_code == 200
    data = r.json()

    # Legacy fields untouched.
    assert data["tailored_resume"]
    assert data["final_score"] == 0.9

    # New, additive fields.
    assert data["run_id"]
    assert data["validation"]["status"] in {"PASS", "WARNING", "FAIL"}
    assert data["report"]["candidate_fit"] == data["candidate_fit_score"]


def test_get_run_is_owned(client):
    headers = auth_headers(client)
    client.put("/profile", json=_PROFILE, headers=headers)
    run_id = _preview(client, headers).json()["run_id"]

    own = client.get(f"/tailor/runs/{run_id}", headers=headers)
    assert own.status_code == 200

    other_headers = auth_headers(client, email="other@example.com")
    other = client.get(f"/tailor/runs/{run_id}", headers=other_headers)
    assert other.status_code == 404


def test_reject_then_regenerate_restores_original(client):
    headers = auth_headers(client)
    client.put("/profile", json=_PROFILE, headers=headers)
    data = _preview(client, headers).json()
    run_id = data["run_id"]

    aws_change = next(
        c for c in data["resume_changes"] if "AWS infrastructure" in c["proposed_text"]
    )

    patch = client.patch(
        f"/tailor/runs/{run_id}/changes",
        headers=headers,
        json={"changes": [{"change_id": aws_change["change_id"], "disposition": "REJECTED"}]},
    )
    assert patch.status_code == 200

    regenerated = client.post(f"/tailor/runs/{run_id}/regenerate", headers=headers)
    assert regenerated.status_code == 200
    result = regenerated.json()

    assert aws_change["proposed_text"] not in result["tailored_resume"]
    assert aws_change["original_text"] in result["tailored_resume"]


def test_regenerate_rejects_unknown_change_id(client):
    headers = auth_headers(client)
    client.put("/profile", json=_PROFILE, headers=headers)
    run_id = _preview(client, headers).json()["run_id"]

    r = client.patch(
        f"/tailor/runs/{run_id}/changes",
        headers=headers,
        json={"changes": [{"change_id": "not-a-real-id", "disposition": "REJECTED"}]},
    )
    assert r.status_code == 400


def test_download_artifact_is_owned(client):
    headers = auth_headers(client)
    client.put("/profile", json=_PROFILE, headers=headers)
    data = _preview(client, headers).json()
    artifact_id = data["artifacts"][0]["artifact_id"]

    own = client.get(f"/tailor/artifacts/{artifact_id}", headers=headers)
    assert own.status_code == 200

    other_headers = auth_headers(client, email="stranger@example.com")
    other = client.get(f"/tailor/artifacts/{artifact_id}", headers=other_headers)
    assert other.status_code == 404
