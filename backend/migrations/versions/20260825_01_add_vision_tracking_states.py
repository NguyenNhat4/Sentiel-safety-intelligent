"""Persist worker-neutral ByteTrack and PPE temporal continuation state.

Revision ID: 20260825_01
Revises: 20260824_02
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260825_01"
down_revision: str | Sequence[str] | None = "20260824_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    state_payload_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    op.create_table(
        "vision_tracking_states",
        sa.Column("monitoring_session_id", sa.String(36), primary_key=True),
        sa.Column("contract_version", sa.String(32), nullable=False),
        sa.Column("state_schema_version", sa.String(40), nullable=False),
        sa.Column("revision", sa.BigInteger(), nullable=False),
        sa.Column("last_frame_id", sa.BigInteger(), nullable=False),
        sa.Column("state_payload", state_payload_type, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("revision >= 0", name="ck_vision_tracking_states_revision"),
        sa.CheckConstraint("last_frame_id >= 0", name="ck_vision_tracking_states_last_frame_id"),
    )
    op.create_index(
        "ix_vision_tracking_states_expires_at",
        "vision_tracking_states",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_vision_tracking_states_expires_at", table_name="vision_tracking_states")
    op.drop_table("vision_tracking_states")
