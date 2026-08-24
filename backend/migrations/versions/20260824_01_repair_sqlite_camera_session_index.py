"""Repair the active-camera session index created on SQLite.

Revision ID: 20260824_01
Revises: 20260823_02
Create Date: 2026-08-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260824_01"
down_revision: str | Sequence[str] | None = "20260823_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ACTIVE_SESSION_PREDICATE = sa.text("status IN ('STARTING','RUNNING')")


def upgrade() -> None:
    if op.get_bind().dialect.name != "sqlite":
        return

    op.drop_index("uq_camera_sessions_active_camera", table_name="camera_sessions")
    op.create_index(
        "uq_camera_sessions_active_camera",
        "camera_sessions",
        ["camera_id"],
        unique=True,
        sqlite_where=_ACTIVE_SESSION_PREDICATE,
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "sqlite":
        return

    op.drop_index("uq_camera_sessions_active_camera", table_name="camera_sessions")
    op.create_index(
        "uq_camera_sessions_active_camera",
        "camera_sessions",
        ["camera_id"],
        unique=True,
    )
