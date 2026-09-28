"""Task 6: TailoringRun/TailoredArtifact are new tables, so create_all()
alone (no additive-column migration) must bring an existing SQLite
database up to date -- confirms nothing about persisting tailoring
artifacts silently depends on a fresh database."""

from sqlalchemy import create_engine, inspect

from app.db import Base
from app.migrations import apply_additive_migrations
from app.models import Job, Profile, User  # noqa: F401 -- registers pre-existing tables


def test_new_tables_are_created_on_an_existing_database(tmp_path):
    db_path = tmp_path / "existing.db"
    engine = create_engine(f"sqlite+pysqlite:///{db_path}")

    # Simulate a database that predates the artifact tables: create only
    # the pre-existing tables first.
    Base.metadata.create_all(bind=engine, tables=[User.__table__, Profile.__table__, Job.__table__])
    inspector = inspect(engine)
    assert "tailoring_runs" not in inspector.get_table_names()

    # The real startup sequence: create_all() for missing tables, then the
    # additive-column migration for existing ones.
    Base.metadata.create_all(bind=engine)
    apply_additive_migrations(engine)

    inspector = inspect(engine)
    assert "tailoring_runs" in inspector.get_table_names()
    assert "tailored_artifacts" in inspector.get_table_names()


def test_migration_does_not_error_on_a_database_that_already_has_the_tables(tmp_path):
    db_path = tmp_path / "current.db"
    engine = create_engine(f"sqlite+pysqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)
    apply_additive_migrations(engine)
    # Running it again must be a safe no-op.
    apply_additive_migrations(engine)
