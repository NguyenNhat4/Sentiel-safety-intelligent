"""Adopt the known pre-Alembic local SQLite schema before an upgrade."""

import shutil
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from backend.app.core.config import get_settings

ALEMBIC_HEAD = "20260807_01"
KNOWN_LEGACY_COLUMNS = {
    "safety_events": {
        "id",
        "zone_id",
        "camera_id",
        "event_type",
        "severity",
        "timestamp",
        "snapshot_path",
        "privacy_blurred",
        "status",
        "acknowledged_by",
        "acknowledged_at",
        "details",
    },
    "ppe_requirements": {
        "id",
        "camera_id",
        "zone_id",
        "helmet_required",
        "safety_glasses_required",
        "gloves_required",
        "updated_at",
    },
    "event_occurrences": {"id", "occurrence_id", "event_id"},
}


def bootstrap_legacy_sqlite(database_url: str) -> bool:
    url = make_url(database_url)
    if url.drivername != "sqlite" or not url.database or url.database == ":memory:":
        return False
    database_path = Path(url.database)
    if not database_path.exists():
        return False
    engine = create_engine(database_url)
    try:
        schema = inspect(engine)
        tables = set(schema.get_table_names())
        if not tables:
            return False
        if "safety_events" not in tables:
            raise RuntimeError("Legacy SQLite schema is not recognized; restore from backup and migrate manually.")
        if "alembic_version" in tables:
            with engine.connect() as connection:
                if connection.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar_one_or_none():
                    return False

        missing_tables = KNOWN_LEGACY_COLUMNS.keys() - tables
        unexpected_tables = tables - KNOWN_LEGACY_COLUMNS.keys() - {"alembic_version"}
        missing_columns = {
            table: required - {column["name"] for column in schema.get_columns(table)}
            for table, required in KNOWN_LEGACY_COLUMNS.items()
            if table in tables
        }
        missing_columns = {table: columns for table, columns in missing_columns.items() if columns}
        if missing_tables or unexpected_tables or missing_columns:
            raise RuntimeError("Legacy SQLite schema is not recognized; restore from backup and migrate manually.")

        safety_event_columns = {column["name"] for column in schema.get_columns("safety_events")}
        backup_path = database_path.with_name(
            f"{database_path.name}.pre-alembic-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.bak"
        )
        shutil.copy2(database_path, backup_path)
        with engine.begin() as connection:
            if "monitoring_session_id" not in safety_event_columns:
                connection.execute(text("ALTER TABLE safety_events ADD COLUMN monitoring_session_id VARCHAR(36)"))
            if "ix_safety_events_monitoring_session_id" not in {
                index["name"] for index in inspect(connection).get_indexes("safety_events")
            }:
                connection.execute(
                    text("CREATE INDEX ix_safety_events_monitoring_session_id ON safety_events (monitoring_session_id)")
                )
            if "alembic_version" not in tables:
                connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
            connection.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:version)"),
                {"version": ALEMBIC_HEAD},
            )
        print(f"Bootstrapped legacy SQLite schema; backup: {backup_path}")
        return True
    finally:
        engine.dispose()


if __name__ == "__main__":
    bootstrap_legacy_sqlite(get_settings().database_url)
