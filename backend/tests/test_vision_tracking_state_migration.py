from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB

from backend.app.core.config import get_settings
from backend.app.models.vision_tracking_state import VisionTrackingState


def test_tracking_state_mapper_uses_revision_as_version_counter():
    assert VisionTrackingState.__mapper__.version_id_col is VisionTrackingState.__table__.c.revision


def test_tracking_state_mapper_uses_jsonb_on_postgresql():
    dialect_type = VisionTrackingState.__table__.c.state_payload.type.dialect_impl(postgresql.dialect())
    assert isinstance(dialect_type, JSONB)


def test_tracking_state_migration_is_reversible(tmp_path, monkeypatch):
    database_path = tmp_path / "vision-tracking-state.db"
    database_url = f"sqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config("alembic.ini")
    engine = create_engine(database_url)

    try:
        command.upgrade(config, "head")
        table = inspect(engine).get_columns("vision_tracking_states")
        assert {column["name"] for column in table} == {
            "monitoring_session_id",
            "contract_version",
            "state_schema_version",
            "revision",
            "last_frame_id",
            "state_payload",
            "updated_at",
            "expires_at",
        }
        assert {index["name"] for index in inspect(engine).get_indexes("vision_tracking_states")} == {
            "ix_vision_tracking_states_expires_at"
        }
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO vision_tracking_states (
                        monitoring_session_id, contract_version, state_schema_version,
                        revision, last_frame_id, state_payload, updated_at, expires_at
                    ) VALUES (
                        'session-1', 'safety_vision_v2', 'bytetrack_ppe_state_v1',
                        1, 7, '{}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                    """
                )
            )

        command.downgrade(config, "20260824_02")
        assert "vision_tracking_states" not in inspect(engine).get_table_names()
    finally:
        engine.dispose()
        get_settings.cache_clear()
