"""Add monitoring session event occurrence idempotency.

Revision ID: 20260807_01
Revises: 20260806_01
Create Date: 2026-08-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260807_01"
down_revision: str | None = "20260806_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("safety_events", sa.Column("monitoring_session_id", sa.String(36), nullable=True))
    op.create_index(
        "ix_safety_events_monitoring_session_id",
        "safety_events",
        ["monitoring_session_id"],
    )
    op.create_table(
        "event_occurrences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("occurrence_id", sa.String(36), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["safety_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("occurrence_id", name="uq_event_occurrences_occurrence_id"),
    )
    op.create_index("ix_event_occurrences_occurrence_id", "event_occurrences", ["occurrence_id"])
    op.create_index("ix_event_occurrences_event_id", "event_occurrences", ["event_id"])


def downgrade() -> None:
    op.drop_index("ix_event_occurrences_event_id", table_name="event_occurrences")
    op.drop_index("ix_event_occurrences_occurrence_id", table_name="event_occurrences")
    op.drop_table("event_occurrences")
    op.drop_index("ix_safety_events_monitoring_session_id", table_name="safety_events")
    op.drop_column("safety_events", "monitoring_session_id")
