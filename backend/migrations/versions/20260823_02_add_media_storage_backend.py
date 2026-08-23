"""Track the canonical storage backend for each media asset.

Revision ID: 20260823_02
Revises: 20260823_01
Create Date: 2026-08-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260823_02"
down_revision: str | Sequence[str] | None = "20260823_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("media_assets") as batch_op:
        batch_op.add_column(sa.Column("storage_backend", sa.String(16), nullable=False, server_default="filesystem"))
        batch_op.create_check_constraint(
            "ck_media_assets_storage_backend",
            "storage_backend IN ('filesystem','s3')",
        )


def downgrade() -> None:
    with op.batch_alter_table("media_assets") as batch_op:
        batch_op.drop_constraint("ck_media_assets_storage_backend", type_="check")
        batch_op.drop_column("storage_backend")
