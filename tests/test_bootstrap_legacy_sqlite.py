import sqlite3

from scripts.bootstrap_legacy_sqlite import bootstrap_legacy_sqlite


def test_bootstrap_legacy_sqlite_adds_missing_column_and_version(tmp_path):
    database_path = tmp_path / "legacy.db"
    connection = sqlite3.connect(database_path)
    connection.execute(
        "CREATE TABLE safety_events (id INTEGER PRIMARY KEY, zone_id TEXT, camera_id TEXT, event_type TEXT, severity TEXT)"
    )
    connection.commit()
    connection.close()

    changed = bootstrap_legacy_sqlite(f"sqlite:///{database_path}")

    connection = sqlite3.connect(database_path)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(safety_events)")}
    version = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    connection.close()
    assert changed is True
    assert "monitoring_session_id" in columns
    assert version == "20260807_01"
    assert list(tmp_path.glob("legacy.db.pre-alembic-*.bak"))
