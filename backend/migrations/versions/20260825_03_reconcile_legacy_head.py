"""Recognize databases carrying the legacy 20260825_03 Alembic head.

Revision ID: 20260825_03
Revises: 20260825_01
Create Date: 2026-08-29

The historical `20260825_03` revision was applied to existing deployments, but
its migration files are absent from the current source lineage. Those
deployments already contain the current media and tracking-state schema. This
no-op bridge makes their recorded revision a valid descendant of the current
tracking-state revision without stamping the database or replaying DDL.
"""

revision: str = "20260825_03"
down_revision: str | None = "20260825_01"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Bridge migration history only; the compatible schema already exists."""


def downgrade() -> None:
    """Bridge migration history only; no schema operation to reverse."""
