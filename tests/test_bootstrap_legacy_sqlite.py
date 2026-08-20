import sqlite3

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from backend.app.core.config import get_settings
from scripts.bootstrap_legacy_sqlite import bootstrap_legacy_sqlite


def create_known_legacy_database(database_path):
    connection = sqlite3.connect(database_path)
    connection.execute(
        """
        CREATE TABLE safety_events (
            id INTEGER PRIMARY KEY,
            zone_id VARCHAR(50) NOT NULL,
            camera_id VARCHAR(50) NOT NULL,
            event_type VARCHAR(50) NOT NULL,
            severity VARCHAR(20) NOT NULL,
            timestamp DATETIME,
            snapshot_path VARCHAR(255),
            privacy_blurred BOOLEAN,
            status VARCHAR(20),
            acknowledged_by VARCHAR(100),
            acknowledged_at DATETIME,
            details JSON
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE ppe_requirements (
            id INTEGER PRIMARY KEY,
            camera_id VARCHAR(50) NOT NULL,
            zone_id VARCHAR(50) NOT NULL,
            helmet_required BOOLEAN NOT NULL DEFAULT 0,
            safety_glasses_required BOOLEAN NOT NULL DEFAULT 0,
            gloves_required BOOLEAN NOT NULL DEFAULT 0,
            updated_at DATETIME NOT NULL,
            UNIQUE (camera_id, zone_id)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE event_occurrences (
            id INTEGER PRIMARY KEY,
            occurrence_id VARCHAR(36) NOT NULL UNIQUE,
            event_id INTEGER NOT NULL REFERENCES safety_events(id) ON DELETE CASCADE
        )
        """
    )
    connection.commit()
    connection.close()
    return database_path


def test_bootstrap_legacy_sqlite_adds_only_missing_revision_state(tmp_path):
    database_path = create_known_legacy_database(tmp_path / "legacy.db")

    changed = bootstrap_legacy_sqlite(f"sqlite:///{database_path}")

    connection = sqlite3.connect(database_path)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(safety_events)")}
    version = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    connection.close()
    assert changed is True
    assert "monitoring_session_id" in columns
    assert version == "20260807_01"
    assert "users" not in tables
    assert "user_sessions" not in tables
    assert "monitoring_zone_collections" not in tables
    assert "monitoring_zones" not in tables
    assert list(tmp_path.glob("legacy.db.pre-alembic-*.bak"))


def test_bootstrapped_legacy_sqlite_upgrades_cleanly_to_head(tmp_path, monkeypatch):
    database_path = create_known_legacy_database(tmp_path / "legacy.db")
    database_url = f"sqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()

    try:
        assert bootstrap_legacy_sqlite(database_url) is True
        config = Config("alembic.ini")
        expected_head = ScriptDirectory.from_config(config).get_current_head()
        command.upgrade(config, "head")

        connection = sqlite3.connect(database_path)
        version = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        ppe_columns = {row[1] for row in connection.execute("PRAGMA table_info(ppe_requirements)")}
        connection.close()

        assert version == expected_head
        assert {"users", "user_sessions", "monitoring_zone_collections", "monitoring_zones"} <= tables
        assert {"hat_required", "vest_required"} <= ppe_columns
    finally:
        get_settings.cache_clear()
