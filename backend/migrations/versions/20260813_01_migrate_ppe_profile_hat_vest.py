"""Migrate PPE requirements to the hat/vest profile.

Revision ID: 20260813_01
Revises: 20260811_03
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260813_01"
down_revision: str | None = "20260811_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("ppe_requirements") as batch_op:
        batch_op.add_column(sa.Column("hat_required", sa.Boolean(), server_default=sa.false(), nullable=False))
        batch_op.add_column(sa.Column("vest_required", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.execute(sa.text("UPDATE ppe_requirements SET hat_required = helmet_required"))


def downgrade() -> None:
    with op.batch_alter_table("ppe_requirements") as batch_op:
        batch_op.drop_column("vest_required")
        batch_op.drop_column("hat_required")
