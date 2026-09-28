"""
Additive-only startup migration for SQLite: Base.metadata.create_all()
creates missing TABLES but never adds columns to a table that already
exists, so a new nullable/defaulted column added to an existing model
(ResumeFile, Profile) needs an explicit ALTER TABLE here or every
pre-existing local dev database breaks on first query. Deliberately does
nothing destructive -- only ever adds a column that's missing; never drops,
renames, or alters an existing one. No real migration tool (Alembic) is
actually wired up despite being a listed dependency, so this is the
smallest safe stand-in rather than introducing a new migration framework
for two additive column sets.
"""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

# (table, column, SQL column-definition) -- order doesn't matter, each is
# independently guarded by an existence check.
_ADDITIVE_COLUMNS: list[tuple[str, str, str]] = [
    ("resume_files", "id", "VARCHAR(36)"),
    ("resume_files", "sha256", "VARCHAR(64)"),
    ("resume_files", "size_bytes", "INTEGER"),
    ("resume_files", "version", "INTEGER DEFAULT 1"),
    ("profiles", "verification_json", "TEXT DEFAULT '{}'"),
    ("tailoring_runs", "baseline_tailored_text", "TEXT DEFAULT ''"),
    ("tailoring_runs", "source_kind", "VARCHAR(8) DEFAULT 'PDF'"),
    ("tailoring_runs", "profile_snapshot_json", "TEXT DEFAULT '{}'"),
]


def apply_additive_migrations(engine: Engine) -> None:
    if not engine.url.get_backend_name().startswith("sqlite"):
        return  # Only SQLite is used for local dev; nothing else to guard.

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table, column, definition in _ADDITIVE_COLUMNS:
            if table not in existing_tables:
                continue  # Base.metadata.create_all() will create it fresh with the column already present.
            existing_columns = {col["name"] for col in inspector.get_columns(table)}
            if column in existing_columns:
                continue
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))
