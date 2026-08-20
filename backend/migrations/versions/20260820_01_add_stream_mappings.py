"""Persist up to four camera-to-stream mappings."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260820_01"
down_revision: str | Sequence[str] | None = ("20260819_01", "20260819_02")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("stream_configuration", sa.Column("mappings", sa.JSON(), nullable=True))
    op.execute("UPDATE stream_configuration SET mappings = '[]' WHERE mappings IS NULL")
    with op.batch_alter_table("stream_configuration") as batch_op:
        batch_op.alter_column("mappings", nullable=False, server_default="[]")


def downgrade() -> None:
    with op.batch_alter_table("stream_configuration") as batch_op:
        batch_op.drop_column("mappings")
