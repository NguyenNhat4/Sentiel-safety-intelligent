"""Add per-camera-zone zone intrusion switch.

Revision ID: 20260821_01
Revises: 20260820_01
Create Date: 2026-08-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260821_01"
down_revision: str | Sequence[str] | None = "20260820_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("ppe_requirements") as batch_op:
        batch_op.add_column(
            sa.Column(
                "zone_intrusion_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("ppe_requirements") as batch_op:
        batch_op.drop_column("zone_intrusion_enabled")
