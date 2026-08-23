"""Add persisted active mock camera stream configuration.

Revision ID: 20260819_01
Revises: 20260815_03
Create Date: 2026-08-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260819_02"
down_revision: str | None = "20260815_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stream_configuration",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("active_camera_id", sa.String(length=64), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("stream_configuration")
