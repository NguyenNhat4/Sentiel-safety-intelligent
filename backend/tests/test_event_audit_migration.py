from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from backend.app.core.config import get_settings


def test_event_audit_migration_is_reversible_and_preserves_legacy_events(tmp_path, monkeypatch):
    database_path = tmp_path / "event-audit-migration.db"
    database_url = f"sqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config("alembic.ini")

    try:
        command.upgrade(config, "20260813_01")
        engine = create_engine(database_url)
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO safety_events (
                        zone_id, camera_id, event_type, severity, timestamp,
                        privacy_blurred, status
                    ) VALUES (
                        'legacy_zone', 'cam_01', 'zone_intrusion', 'high',
                        '2026-08-15 00:00:00', 0, 'acknowledged'
                    )
                    """
                )
            )

        command.upgrade(config, "head")

        with engine.connect() as connection:
            columns = {row[1] for row in connection.execute(text("PRAGMA table_info(safety_events)"))}
            row = connection.execute(
                text(
                    """
                    SELECT decision_context, audit_retention_until, snapshot_retention_until
                    FROM safety_events WHERE zone_id = 'legacy_zone'
                    """
                )
            ).one()
        assert {"decision_context", "audit_retention_until", "snapshot_retention_until"} <= columns
        assert tuple(row) == (None, None, None)

        command.downgrade(config, "20260815_03")
        with engine.connect() as connection:
            downgraded_columns = {row[1] for row in connection.execute(text("PRAGMA table_info(safety_events)"))}
        assert "decision_context" not in downgraded_columns
        assert "audit_retention_until" not in downgraded_columns
        assert "snapshot_retention_until" not in downgraded_columns
    finally:
        get_settings.cache_clear()
