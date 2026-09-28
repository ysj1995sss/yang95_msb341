"""Task 6: immutable TailoringRun/TailoredArtifact persistence and ownership."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import User
from app.tailor.storage import TailoringRunStore


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def user(db):
    row = User(email="a@example.com", password_hash="x")
    db.add(row)
    db.commit()
    return row


@pytest.fixture()
def other_user(db):
    row = User(email="b@example.com", password_hash="x")
    db.add(row)
    db.commit()
    return row


@pytest.fixture()
def store(db):
    return TailoringRunStore(db)


@pytest.fixture()
def stored_run(store, user):
    return store.create_run(
        user_id=user.id,
        original_resume_id="resume-1",
        original_resume_version=1,
        profile_snapshot_hash="hash-abc",
        profile_snapshot={"name": "Test Candidate"},
        job_snapshot={"company": "Acme", "role": "Analyst"},
        request_options={"target_length": "preserve"},
        candidate_fit={"score": 72.0},
        proposed_changes=[],
        validation={"status": "PASS", "findings": []},
    )


class TestCreateRun:
    def test_create_run_returns_a_persisted_row_owned_by_the_user(self, store, user):
        run = store.create_run(
            user_id=user.id,
            original_resume_id="resume-1",
            original_resume_version=1,
            profile_snapshot_hash="hash-abc",
            profile_snapshot={"name": "Test Candidate"},
            job_snapshot={"company": "Acme"},
            request_options={},
            candidate_fit={},
            proposed_changes=[],
            validation={"status": "PASS", "findings": []},
        )
        assert run.id
        assert run.user_id == user.id
        assert run.state == "PROPOSED"


class TestSaveArtifact:
    def test_regeneration_creates_new_immutable_version(self, store, db, stored_run):
        first = store.save_artifact(stored_run.id, "PDF", b"one", "one.pdf", "PASS")
        second = store.save_artifact(stored_run.id, "PDF", b"two", "two.pdf", "PASS")

        assert (first.version, second.version) == (1, 2)
        # The FIRST artifact's bytes must never change after the second is created.
        from app.models import TailoredArtifact

        assert db.get(TailoredArtifact, first.id).data == b"one"
        assert db.get(TailoredArtifact, second.id).data == b"two"

    def test_versions_are_independent_per_kind(self, store, stored_run):
        pdf_one = store.save_artifact(stored_run.id, "PDF", b"p1", "p1.pdf", "PASS")
        docx_one = store.save_artifact(stored_run.id, "DOCX", b"d1", "d1.docx", "PASS")
        pdf_two = store.save_artifact(stored_run.id, "PDF", b"p2", "p2.pdf", "PASS")

        assert pdf_one.version == 1
        assert docx_one.version == 1
        assert pdf_two.version == 2

    def test_artifact_records_checksum_and_size(self, store, stored_run):
        import hashlib

        artifact = store.save_artifact(stored_run.id, "PDF", b"payload", "f.pdf", "PASS")
        assert artifact.sha256 == hashlib.sha256(b"payload").hexdigest()
        assert artifact.size_bytes == len(b"payload")

    def test_new_artifact_records_what_it_supersedes(self, store, stored_run):
        first = store.save_artifact(stored_run.id, "PDF", b"one", "one.pdf", "PASS")
        second = store.save_artifact(stored_run.id, "PDF", b"two", "two.pdf", "PASS")
        assert second.supersedes_artifact_id == first.id
        assert first.supersedes_artifact_id is None

    def test_artifact_is_owned_by_the_runs_user(self, store, stored_run, user):
        artifact = store.save_artifact(stored_run.id, "PDF", b"one", "one.pdf", "PASS")
        assert artifact.user_id == user.id


class TestOwnership:
    def test_owner_can_read_their_own_run(self, store, stored_run, user):
        assert store.get_owned_run(stored_run.id, user.id) is not None

    def test_non_owner_cannot_read_the_run(self, store, stored_run, other_user):
        assert store.get_owned_run(stored_run.id, other_user.id) is None

    def test_owner_can_read_their_own_artifact(self, store, stored_run, user):
        artifact = store.save_artifact(stored_run.id, "PDF", b"one", "one.pdf", "PASS")
        assert store.get_owned_artifact(artifact.id, user.id) is not None

    def test_non_owner_cannot_read_the_artifact(self, store, stored_run, other_user):
        artifact = store.save_artifact(stored_run.id, "PDF", b"one", "one.pdf", "PASS")
        assert store.get_owned_artifact(artifact.id, other_user.id) is None


class TestNextArtifactVersion:
    def test_starts_at_one(self, store, stored_run):
        assert store.next_artifact_version(stored_run.id, "PDF") == 1

    def test_increments_after_a_save(self, store, stored_run):
        store.save_artifact(stored_run.id, "PDF", b"one", "one.pdf", "PASS")
        assert store.next_artifact_version(stored_run.id, "PDF") == 2
