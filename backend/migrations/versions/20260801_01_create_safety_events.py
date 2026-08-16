"""Create the baseline safety events table.

Revision ID: 20260801_01
Revises: None
Create Date: 2026-08-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260801_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "safety_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("zone_id", sa.String(50), nullable=False),
        sa.Column("camera_id", sa.String(50), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("snapshot_path", sa.String(255), nullable=True),
        sa.Column("privacy_blurred", sa.Boolean(), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("acknowledged_by", sa.String(100), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_safety_events_id", "safety_events", ["id"])
    op.create_index("ix_safety_events_zone_id", "safety_events", ["zone_id"])
    op.create_index("ix_safety_events_event_type", "safety_events", ["event_type"])
    op.create_index("ix_safety_events_timestamp", "safety_events", ["timestamp"])
    op.create_index("ix_safety_events_status", "safety_events", ["status"])


def downgrade() -> None:
    op.drop_index("ix_safety_events_status", table_name="safety_events")
    op.drop_index("ix_safety_events_timestamp", table_name="safety_events")
    op.drop_index("ix_safety_events_event_type", table_name="safety_events")
    op.drop_index("ix_safety_events_zone_id", table_name="safety_events")
    op.drop_index("ix_safety_events_id", table_name="safety_events")
    op.drop_table("safety_events")
