import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def auth_headers(client, email: str = "p@example.com") -> dict:
    r = client.post("/auth/register", json={"email": email, "password": "secret123"})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def workspace_client(tmp_path, monkeypatch):
    """The workspace API in local single-user mode, with its own data folder."""
    from app.workspace.context import forget_services

    monkeypatch.setenv("JOB_COPILOT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("JOB_COPILOT_PREFETCH", "0")
    monkeypatch.delenv("WORKSPACE_TOKEN_SECRET", raising=False)
    forget_services()
    with TestClient(app) as c:
        yield c
    forget_services()
