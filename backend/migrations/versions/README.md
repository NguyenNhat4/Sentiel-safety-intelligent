# Alembic revisions

Contains ordered database schema revisions for the FastAPI backend. Each revision must provide reversible `upgrade` and `downgrade` operations and remain compatible with the configured SQLite local/test and PostgreSQL production targets.

`20260819_01` adds the US-16 event decision context and retention-deadline columns without rewriting historical rows.
