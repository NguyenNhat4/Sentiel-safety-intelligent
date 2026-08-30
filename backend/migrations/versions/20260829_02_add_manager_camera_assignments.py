"""Add multi-camera assignments for area managers.

Revision ID: 20260829_02
Revises: 20260829_01
"""

import sqlalchemy as sa
from alembic import op

revision = "20260829_02"
down_revision = "20260829_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("users")}
    if "managed_camera_ids" not in columns:
        op.add_column("users", sa.Column("managed_camera_ids", sa.JSON(), nullable=False, server_default="[]"))
        op.alter_column("users", "managed_camera_ids", server_default=None)


def downgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("users")}
    if "managed_camera_ids" in columns:
        op.drop_column("users", "managed_camera_ids")
