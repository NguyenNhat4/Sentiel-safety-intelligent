# Alembic revisions

Contains ordered database schema revisions for the FastAPI backend. Each new revision must provide reversible `upgrade` and `downgrade` operations for PostgreSQL, the only supported database target. Existing SQLite compatibility is legacy migration history and must not drive new schema design or test requirements.

`20260819_01` adds the US-16 event decision context and retention-deadline columns without rewriting historical rows.
