from pathlib import Path

import pytest

from resume_tailorer.identity import (
    LOCAL_OWNER, applications_db_path, job_db_path, resolve_identity, user_dir,
)
from resume_tailorer.job_search.job_service import JobService
from resume_tailorer.job_search.models import JobPosting, JobSource

APP = str(Path(__file__).resolve().parent.parent / "resume_tailorer" / "app.py")


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("JOB_COPILOT_DATA_DIR", str(tmp_path / "data"))
    return tmp_path / "data"


def test_without_sign_in_configured_the_app_is_local_single_user():
    identity = resolve_identity(False, {})
    assert identity.owner_id == LOCAL_OWNER and not identity.signed_in


def test_sign_in_required_when_configured():
    assert resolve_identity(True, {"is_logged_in": False}) is None


def test_owner_ids_are_stable_private_and_distinct():
    alice = resolve_identity(True, {"is_logged_in": True, "sub": "111", "email": "a@example.com", "name": "A"})
    again = resolve_identity(True, {"is_logged_in": True, "sub": "111", "email": "a@example.com"})
    bob = resolve_identity(True, {"is_logged_in": True, "sub": "222", "email": "b@example.com"})
    assert alice.owner_id == again.owner_id != bob.owner_id
    assert "a@example.com" not in alice.owner_id and alice.signed_in


def test_each_owner_has_separate_databases(data_dir):
    alice, bob = "a" * 32, "b" * 32
    assert job_db_path(alice) != job_db_path(bob)
    assert Path(applications_db_path(alice)).parent == data_dir / "users" / alice

    alice_service = JobService(db_path=job_db_path(alice), applications_db_path=applications_db_path(alice))
    alice_service.db.save_job_posting(JobPosting(source=JobSource.GREENHOUSE, source_id="1", company="Acme",
                                                 title="PM", location="Remote", description="d"))
    bob_service = JobService(db_path=job_db_path(bob), applications_db_path=applications_db_path(bob))
    assert bob_service.db.get_job_posting("greenhouse_1") is None
    assert alice_service.db.get_job_posting("greenhouse_1") is not None


@pytest.mark.parametrize("bad", ["", "../other", "a/b", "c:d"])
def test_owner_ids_cannot_escape_the_data_directory(bad):
    with pytest.raises(ValueError):
        user_dir(bad)


