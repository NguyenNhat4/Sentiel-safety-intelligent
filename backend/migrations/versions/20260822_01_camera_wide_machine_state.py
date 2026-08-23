"""Move machine state from zones to camera mappings.

Revision ID: 20260822_01
Revises: 20260821_01
Create Date: 2026-08-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260822_01"
down_revision: str | Sequence[str] | None = "20260821_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    table = sa.table("stream_configuration", sa.column("id", sa.Integer), sa.column("mappings", sa.JSON))
    rows = connection.execute(sa.text("SELECT id, mappings FROM stream_configuration")).mappings().all()
    for row in rows:
        mappings = row["mappings"] or []
        normalized = [{**mapping, "machine_state": mapping.get("machine_state", "stopped")} for mapping in mappings]
        connection.execute(table.update().where(table.c.id == row["id"]).values(mappings=normalized))


def downgrade() -> None:
    # Keeping the field is intentional: old clients can continue reading the
    # legacy zone column while the mapping contract is rolled out.
    pass
