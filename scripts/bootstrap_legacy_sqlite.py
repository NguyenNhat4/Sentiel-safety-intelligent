"""Adopt the known pre-Alembic local SQLite schema before an upgrade."""

import shutil
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from backend.app.core.config import get_settings
from backend.app.core.database import Base
from backend.app.models import event, ppe_requirement  # noqa: F401

ALEMBIC_HEAD = "20260807_01"


def bootstrap_legacy_sqlite(database_url: str) -> bool:
    url = make_url(database_url)
    if url.drivername != "sqlite" or not url.database or url.database == ":memory:":
        return False
    database_path = Path(url.database)
    if not database_path.exists():
        return False
    engine = create_engine(database_url)
    tables = set(inspect(engine).get_table_names())
    if "safety_events" not in tables:
        return False
    if "alembic_version" in tables:
        with engine.connect() as connection:
            if connection.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar_one_or_none():
                return False
    columns = {column["name"] for column in inspect(engine).get_columns("safety_events")}
    if not {"id", "zone_id", "camera_id", "event_type", "severity"}.issubset(columns):
        raise RuntimeError("Legacy SQLite schema is not recognized; restore from backup and migrate manually.")
    backup_path = database_path.with_name(
        f"{database_path.name}.pre-alembic-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.bak"
    )
    shutil.copy2(database_path, backup_path)
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        if "monitoring_session_id" not in columns:
            connection.execute(text("ALTER TABLE safety_events ADD COLUMN monitoring_session_id VARCHAR(36)"))
        if "ix_safety_events_monitoring_session_id" not in {
            index["name"] for index in inspect(connection).get_indexes("safety_events")
        }:
            connection.execute(text("CREATE INDEX ix_safety_events_monitoring_session_id ON safety_events (monitoring_session_id)"))
        if "alembic_version" not in tables:
            connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        connection.execute(text("INSERT INTO alembic_version (version_num) VALUES (:version)"), {"version": ALEMBIC_HEAD})
    print(f"Bootstrapped legacy SQLite schema; backup: {backup_path}")
    return True


if __name__ == "__main__":
    bootstrap_legacy_sqlite(get_settings().database_url)
