import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from backend.app.core.config import get_settings


def test_sqlite_migration_allows_replay_after_completed_session(tmp_path, monkeypatch):
    database_path = tmp_path / "camera-session-index.db"
    database_url = f"sqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config("alembic.ini")
    engine = create_engine(database_url)

    try:
        command.upgrade(config, "20260823_02")
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO camera_sessions (
                        id, camera_id, asset_id, media_type, status,
                        config_revision, inference_fps, started_at, completed_at
                    ) VALUES (
                        'completed-session', 'cam_1', 'asset-1', 'video', 'COMPLETED',
                        1, 1.0, '2026-08-24 00:00:00', '2026-08-24 00:01:00'
                    )
                    """
                )
            )

        command.upgrade(config, "head")

        with engine.begin() as connection:
            index_sql = connection.execute(
                text(
                    """
                    SELECT sql FROM sqlite_master
                    WHERE type = 'index' AND name = 'uq_camera_sessions_active_camera'
                    """
                )
            ).scalar_one()
            connection.execute(
                text(
                    """
                    INSERT INTO camera_sessions (
                        id, camera_id, asset_id, media_type, status,
                        config_revision, inference_fps, started_at
                    ) VALUES (
                        'replay-session', 'cam_1', 'asset-1', 'video', 'STARTING',
                        1, 0, '2026-08-24 00:02:00'
                    )
                    """
                )
            )

        assert "WHERE status IN ('STARTING','RUNNING')" in index_sql

        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        INSERT INTO camera_sessions (
                            id, camera_id, asset_id, media_type, status,
                            config_revision, inference_fps, started_at
                        ) VALUES (
                            'duplicate-active-session', 'cam_1', 'asset-1', 'video', 'RUNNING',
                            1, 1.0, '2026-08-24 00:03:00'
                        )
                        """
                    )
                )
    finally:
        engine.dispose()
        get_settings.cache_clear()
