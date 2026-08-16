# Backend migrations

Alembic migrations are the ordered, reversible schema history for backend persistence. Run them from the repository root with `.venv/bin/alembic upgrade head`; the database URL comes from `DATABASE_URL` through backend settings.

US-08 adds the nullable monitoring-session field and the unique event-occurrence mapping used to make reviewed event creation idempotent. Runtime tracking state remains in memory and is not persisted here.

US-28 adds the active `hat_required`/`vest_required` columns, maps the legacy helmet flag to hat, defaults vest OFF and intentionally retains legacy PPE columns plus historical events/occurrences for audit. The revision is reversible.
