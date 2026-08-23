"""Add backend-owned media assets, camera configurations, and sessions.

Revision ID: 20260823_01
Revises: 20260822_01
Create Date: 2026-08-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260823_01"
down_revision: str | Sequence[str] | None = "20260822_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("media_type", sa.String(10), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("storage_filename", sa.String(80), nullable=False, unique=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("media_type IN ('video','image')", name="ck_media_assets_type"),
        sa.CheckConstraint("status IN ('UPLOADING','READY','ERROR')", name="ck_media_assets_status"),
    )
    op.create_index("ix_media_assets_status", "media_assets", ["status"])
    op.create_table(
        "camera_configurations",
        sa.Column("camera_id", sa.String(16), primary_key=True),
        sa.Column("asset_id", sa.String(36), sa.ForeignKey("media_assets.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("machine_state", sa.String(20), nullable=False, server_default="stopped"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("camera_id IN ('cam_1','cam_2','cam_3','cam_4')", name="ck_camera_configurations_id"),
        sa.CheckConstraint("machine_state IN ('running','stopped')", name="ck_camera_configurations_machine_state"),
        sa.UniqueConstraint("asset_id", name="uq_camera_configurations_asset_id"),
    )
    op.execute(
        """
        INSERT INTO camera_configurations (camera_id, machine_state, revision, updated_at)
        SELECT camera_id, 'stopped', revision, updated_at
        FROM monitoring_zone_collections
        WHERE camera_id IN ('cam_1','cam_2','cam_3','cam_4')
        """
    )
    op.execute(
        """
        INSERT INTO camera_configurations (camera_id, machine_state, revision, updated_at)
        SELECT camera_id, 'stopped', 0, CURRENT_TIMESTAMP
        FROM (
            SELECT 'cam_1' AS camera_id
            UNION ALL SELECT 'cam_2'
            UNION ALL SELECT 'cam_3'
            UNION ALL SELECT 'cam_4'
        ) AS fixed
        WHERE NOT EXISTS (
            SELECT 1 FROM camera_configurations existing WHERE existing.camera_id = fixed.camera_id
        )
        """
    )
    op.create_table(
        "camera_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("camera_id", sa.String(16), nullable=False),
        sa.Column("asset_id", sa.String(36), sa.ForeignKey("media_assets.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("media_type", sa.String(10), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("config_revision", sa.Integer(), nullable=False),
        sa.Column("inference_fps", sa.Float(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("running_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.CheckConstraint("camera_id IN ('cam_1','cam_2','cam_3','cam_4')", name="ck_camera_sessions_id"),
        sa.CheckConstraint("media_type IN ('video','image')", name="ck_camera_sessions_media_type"),
        sa.CheckConstraint(
            "status IN ('STARTING','RUNNING','COMPLETED','ERROR','STOPPED')",
            name="ck_camera_sessions_status",
        ),
    )
    op.create_index("ix_camera_sessions_camera_id", "camera_sessions", ["camera_id"])
    op.create_index("ix_camera_sessions_asset_id", "camera_sessions", ["asset_id"])
    op.create_index("ix_camera_sessions_status", "camera_sessions", ["status"])
    op.create_index(
        "uq_camera_sessions_active_camera",
        "camera_sessions",
        ["camera_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('STARTING','RUNNING')"),
    )


def downgrade() -> None:
    op.drop_index("uq_camera_sessions_active_camera", table_name="camera_sessions")
    op.drop_index("ix_camera_sessions_status", table_name="camera_sessions")
    op.drop_index("ix_camera_sessions_asset_id", table_name="camera_sessions")
    op.drop_index("ix_camera_sessions_camera_id", table_name="camera_sessions")
    op.drop_table("camera_sessions")
    op.drop_table("camera_configurations")
    op.drop_index("ix_media_assets_status", table_name="media_assets")
    op.drop_table("media_assets")
