"""Add persisted PPE requirements.

Revision ID: 20260806_01
Revises: 20260801_01
Create Date: 2026-08-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260806_01"
down_revision: str | None = "20260801_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ppe_requirements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("camera_id", sa.String(length=50), nullable=False),
        sa.Column("zone_id", sa.String(length=50), nullable=False),
        sa.Column("helmet_required", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("safety_glasses_required", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("gloves_required", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("camera_id", "zone_id", name="uq_ppe_requirements_camera_zone"),
    )
    op.create_index("ix_ppe_requirements_camera_id", "ppe_requirements", ["camera_id"])
    op.create_index("ix_ppe_requirements_zone_id", "ppe_requirements", ["zone_id"])


def downgrade() -> None:
    op.drop_index("ix_ppe_requirements_zone_id", table_name="ppe_requirements")
    op.drop_index("ix_ppe_requirements_camera_id", table_name="ppe_requirements")
    op.drop_table("ppe_requirements")
