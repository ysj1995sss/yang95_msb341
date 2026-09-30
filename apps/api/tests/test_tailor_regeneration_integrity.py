"""Regeneration must reuse the run's own inputs and re-score the final artifact."""

from datetime import datetime
from types import SimpleNamespace

from app.db import get_db
from app.main import app
from app.models import ResumeFile, ResumeFileVersion, User
from app.tailor import router as tailor_router
from tests.conftest import auth_headers
from tests.test_tailor_review import _PROFILE, _preview


def test_run_resolves_its_exact_resume_version_after_a_reupload(client):
    auth_headers(client)
    db = next(app.dependency_overrides[get_db]())
    user = db.query(User).first()
    db.add(ResumeFileVersion(
        user_id=user.id, filename="v1.docx", content_type="x", data=b"version-one",
        version=1, uploaded_at=datetime(2026, 9, 1),
    ))
    db.add(ResumeFile(user_id=user.id, id="current", filename="v2.docx", content_type="x",
                      data=b"version-two", version=2))
    db.commit()

    old_run = SimpleNamespace(user_id=user.id, original_resume_version=1)
    new_run = SimpleNamespace(user_id=user.id, original_resume_version=2)
    missing_run = SimpleNamespace(user_id=user.id, original_resume_version=7)

    assert tailor_router._run_resume_file(db, old_run).data == b"version-one"
    assert tailor_router._run_resume_file(db, new_run).data == b"version-two"
    assert tailor_router._run_resume_file(db, missing_run) is None


def test_regenerate_scores_the_final_artifact(client, monkeypatch):
    headers = auth_headers(client)
    client.put("/profile", json=_PROFILE, headers=headers)
    data = _preview(client, headers).json()

    monkeypatch.setattr(
        tailor_router.ResumeTailoringOptimizer, "_score_resume",
        staticmethod(lambda text, job_analysis, profile=None: (0.77, [], ["Kubernetes"])),
    )
    result = client.post(f"/tailor/runs/{data['run_id']}/regenerate", headers=headers).json()

    assert result["final_score"] == 0.77
    assert result["report"]["tailored_alignment"] == 0.77
    assert result["missing_qualifications"] == ["Kubernetes"]
