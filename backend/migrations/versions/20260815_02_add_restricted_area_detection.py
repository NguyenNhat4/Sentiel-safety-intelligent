"""Add the per-zone whole-camera restricted-area detection switch.

Revision ID: 20260815_02
Revises: 20260814_01
Create Date: 2026-08-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260815_02"
down_revision: str | None = "20260814_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("ppe_requirements") as batch_op:
        batch_op.add_column(
            sa.Column("restricted_area_detection_enabled", sa.Boolean(), server_default=sa.false(), nullable=False)
        )


def downgrade() -> None:
    with op.batch_alter_table("ppe_requirements") as batch_op:
        batch_op.drop_column("restricted_area_detection_enabled")
