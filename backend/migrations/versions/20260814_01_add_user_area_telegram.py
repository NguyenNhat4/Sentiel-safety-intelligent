"""Add area assignment and Telegram delivery identity to users.

Revision ID: 20260814_01
Revises: 20260813_01
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260814_01"
down_revision: str | None = "20260813_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("managed_area_id", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("telegram_username", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("telegram_chat_id", sa.String(length=64), nullable=True))
        batch_op.create_index("ix_users_managed_area_id", ["managed_area_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_managed_area_id")
        batch_op.drop_column("telegram_chat_id")
        batch_op.drop_column("telegram_username")
        batch_op.drop_column("managed_area_id")
