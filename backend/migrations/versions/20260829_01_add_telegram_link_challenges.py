"""Add one-time Telegram account-link challenges.

Revision ID: 20260829_01
Revises: 20260825_03
Create Date: 2026-08-29
"""

import sqlalchemy as sa
from alembic import op

revision = "20260829_01"
down_revision = "20260825_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "telegram_link_challenges" not in inspector.get_table_names():
        op.create_table(
            "telegram_link_challenges",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("secret_digest", sa.String(64), nullable=False, unique=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        )
    existing_indexes = {item["name"] for item in sa.inspect(bind).get_indexes("telegram_link_challenges")}
    for name, column in (
        ("ix_telegram_link_challenges_user_id", "user_id"),
        ("ix_telegram_link_challenges_secret_digest", "secret_digest"),
        ("ix_telegram_link_challenges_expires_at", "expires_at"),
    ):
        if name not in existing_indexes:
            op.create_index(name, "telegram_link_challenges", [column])


def downgrade() -> None:
    if "telegram_link_challenges" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("telegram_link_challenges")
