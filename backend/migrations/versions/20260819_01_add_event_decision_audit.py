"""Add versioned event decision audit context and retention deadlines.

Revision ID: 20260819_01
Revises: 20260815_03
Create Date: 2026-08-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260819_01"
down_revision: str | None = "20260815_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("safety_events") as batch_op:
        batch_op.add_column(sa.Column("decision_context", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("audit_retention_until", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("snapshot_retention_until", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("safety_events") as batch_op:
        batch_op.drop_column("snapshot_retention_until")
        batch_op.drop_column("audit_retention_until")
        batch_op.drop_column("decision_context")
