# Alembic revisions

Contains ordered database schema revisions for the FastAPI backend. Each new revision must provide reversible `upgrade` and `downgrade` operations for PostgreSQL, the only supported database target. Existing SQLite compatibility is legacy migration history and must not drive new schema design or test requirements.

`20260819_01` adds the US-16 event decision context and retention-deadline columns without rewriting historical rows.

`20260825_01` adds the bounded PostgreSQL JSONB state row used to continue ByteTrack and PPE smoothing across stateless `safety_vision_v2` worker replicas. Its downgrade removes only that table and expiry index.

`20260825_03` is a no-op compatibility head for existing databases that already recorded the legacy revision and contain the compatible schema. It reconnects that history to `20260825_01`; it never runs DDL or data changes.
