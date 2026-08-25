"""Persist PPE requirements on the camera configuration.

Revision ID: 20260824_02
Revises: 20260824_01
Create Date: 2026-08-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260824_02"
down_revision: str | Sequence[str] | None = "20260824_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "camera_configurations",
        sa.Column("hat_required", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "camera_configurations",
        sa.Column("vest_required", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute(
        """
        UPDATE camera_configurations
        SET hat_required = CASE WHEN EXISTS (
            SELECT 1 FROM ppe_requirements
            WHERE ppe_requirements.camera_id = camera_configurations.camera_id
              AND ppe_requirements.hat_required = true
        ) THEN true ELSE false END,
            vest_required = CASE WHEN EXISTS (
            SELECT 1 FROM ppe_requirements
            WHERE ppe_requirements.camera_id = camera_configurations.camera_id
              AND ppe_requirements.vest_required = true
        ) THEN true ELSE false END
        """
    )


def downgrade() -> None:
    op.drop_column("camera_configurations", "vest_required")
    op.drop_column("camera_configurations", "hat_required")
