"""Add revisioned monitoring zone collections.

Revision ID: 20260811_03
Revises: 20260811_02
Create Date: 2026-08-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260811_03"
down_revision: str | None = "20260811_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("monitoring_zone_collections"):
        op.create_table(
            "monitoring_zone_collections",
            sa.Column("camera_id", sa.String(50), nullable=False),
            sa.Column("revision", sa.Integer(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("camera_id"),
        )
    if not inspector.has_table("monitoring_zones"):
        op.create_table(
            "monitoring_zones",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("camera_id", sa.String(50), nullable=False),
            sa.Column("zone_id", sa.String(50), nullable=False),
            sa.Column("normalized_zone_id", sa.String(50), nullable=False),
            sa.Column("display_name", sa.String(100), nullable=False),
            sa.Column("points", sa.JSON(), nullable=False),
            sa.Column("machine_state", sa.String(20), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("order", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["camera_id"], ["monitoring_zone_collections.camera_id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("camera_id", "normalized_zone_id", name="uq_monitoring_zones_camera_normalized_id"),
        )
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("monitoring_zones")}
    if "ix_monitoring_zones_camera_id" not in indexes:
        op.create_index("ix_monitoring_zones_camera_id", "monitoring_zones", ["camera_id"])


def downgrade() -> None:
    op.drop_index("ix_monitoring_zones_camera_id", table_name="monitoring_zones")
    op.drop_table("monitoring_zones")
    op.drop_table("monitoring_zone_collections")
