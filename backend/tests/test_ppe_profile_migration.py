from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from backend.app.core.config import get_settings


def test_migration_maps_helmet_to_hat_and_preserves_legacy_columns(tmp_path, monkeypatch):
    database_path = tmp_path / "ppe-migration.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    get_settings.cache_clear()
    config = Config("alembic.ini")

    try:
        command.upgrade(config, "20260811_03")
        engine = create_engine(f"sqlite:///{database_path}")
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO ppe_requirements (
                        camera_id, zone_id, helmet_required,
                        safety_glasses_required, gloves_required, updated_at
                    ) VALUES (
                        'uploaded_video', 'zone_01', 1, 1, 1,
                        '2026-08-13 00:00:00'
                    )
                    """
                )
            )

        command.upgrade(config, "head")

        with engine.connect() as connection:
            row = connection.execute(
                text(
                    """
                    SELECT helmet_required, safety_glasses_required,
                           gloves_required, hat_required, vest_required
                    FROM ppe_requirements
                    """
                )
            ).one()
        assert tuple(row) == (1, 1, 1, 1, 0)

        command.downgrade(config, "20260811_03")
        with engine.connect() as connection:
            columns = {row[1] for row in connection.execute(text("PRAGMA table_info(ppe_requirements)"))}
        assert {"helmet_required", "safety_glasses_required", "gloves_required"} <= columns
        assert "hat_required" not in columns
        assert "vest_required" not in columns
    finally:
        get_settings.cache_clear()
