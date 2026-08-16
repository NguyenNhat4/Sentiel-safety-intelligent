"""Add one reviewed event per tracked person and monitoring session.

Revision ID: 20260815_03
Revises: 20260815_02
Create Date: 2026-08-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260815_03"
down_revision: str | None = "20260815_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("safety_events") as batch_op:
        batch_op.add_column(sa.Column("track_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_safety_events_track_id", ["track_id"], unique=False)
        batch_op.create_unique_constraint(
            "uq_safety_events_session_track",
            ["monitoring_session_id", "track_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("safety_events") as batch_op:
        batch_op.drop_constraint("uq_safety_events_session_track", type_="unique")
        batch_op.drop_index("ix_safety_events_track_id")
        batch_op.drop_column("track_id")
