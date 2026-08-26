# Backend migrations

Alembic migrations are the ordered, reversible schema history for backend persistence. Run them from the repository root with `.venv/bin/alembic upgrade head`; the database URL comes from `DATABASE_URL` through backend settings.

US-08 adds the nullable monitoring-session field and the unique event-occurrence mapping used to make reviewed event creation idempotent.

Issue #43 adds `vision_tracking_states`: one backend-owned JSONB continuation row per monitoring session with optimistic revision/frame ordering and TTL expiry. The standalone Vision worker never receives `DATABASE_URL`; v1 can still keep legacy state in memory for rollback, while v2 state is persisted only through the backend service.

US-28 adds the active `hat_required`/`vest_required` columns, maps the legacy helmet flag to hat, defaults vest OFF and intentionally retains legacy PPE columns plus historical events/occurrences for audit. The revision is reversible.

The 2026-08-14 account revision adds nullable area assignment, Telegram username and Telegram chat ID fields. Existing accounts remain readable; new area-manager assignments are validated by the application against a saved monitoring area.

The 2026-08-15 tracked-person event revision adds nullable `track_id` and a unique `(monitoring_session_id, track_id)` constraint. New per-person reviews merge later hat, vest, and zone violations into the same event while legacy events remain compatible.

The monitoring-zone migration recognizes pre-existing zone tables from earlier local runs, creates only missing tables/indexes, and then lets Alembic record its revision normally.

US-16 adds nullable versioned decision-audit JSON and separate audit/snapshot retention deadlines to safety events. Existing rows remain readable with null audit fields, and the revision is reversible.
