# Implementation Plan: US-16 Event Decision Audit

## Overview

Complete US-16 by persisting a versioned, immutable decision context for every newly reviewed alert, exposing an additive event-detail contract with a grounded natural-language summary, and giving Safety Managers and Area Managers an accessible detail view. The feature preserves legacy event creation and never stores continuous raw video.

## Execution Status

Implementation and automated verification are complete after synchronization onto `origin/develop2` at `28daa62`. `make check` passes with 25 root/streamer tests, 169 backend/vision tests and 62 frontend tests, plus lint, formatting, type-check and production build. The migration/operational-logger order regression found during restoration has a focused guard. Browser UAT remains pending because Chrome DevTools is not configured in this environment.

## Architecture Decisions

- Keep searchable event fields as SQL columns and add one nullable `decision_context` JSON document with `schema_version=decision_context_v1`; legacy events remain readable with no backfill fabrication.
- Build the stored review actor, review timestamp, rule-policy version and retention deadlines in the backend. The frontend supplies typed inference evidence, but cannot set server-owned audit metadata.
- Keep `GET /events` backward compatible. Extend `GET /events/{event_id}` with an additive summary generated from persisted structured data; deterministic Vietnamese text is always available and optional LLM output never replaces audit data.
- Retain structured audit metadata for 365 days and protected snapshots for 90 days by default. Both durations are configurable; automatic deletion is a separate retention-enforcement task.
- Store false-alarm reviews for audit/model-quality use while keeping acknowledged-only queries as the official violation source.

## Task List

### Phase 1: Persistence and contract foundation

#### Task 1: Add the versioned audit persistence contract

**Description:** Define strict Pydantic input/stored schemas, add nullable event audit/retention columns, and create a reversible Alembic revision.

**Acceptance criteria:**
- [ ] New reviewed events can carry `decision_context_v1`; legacy requests without it still succeed.
- [ ] Stored context has typed rule, scene, system-decision and human-review sections.
- [ ] Migration upgrades and downgrades on SQLite while preserving existing events.

**Verification:**
- [ ] `PYTHONPATH=. .venv/bin/pytest backend/tests/test_event_audit.py backend/tests/test_event_audit_migration.py -v`

**Dependencies:** None

**Files likely touched:** `backend/app/schemas/event.py`, `backend/app/models/event.py`, `backend/app/core/config.py`, `backend/migrations/versions/20260819_01_add_event_decision_audit.py`, focused tests.

**Estimated scope:** Medium

#### Task 2: Canonicalize immutable context and generate grounded summaries

**Description:** Build server-owned actor/timestamps/version/retention metadata during event persistence and return a deterministic-or-LLM summary from event detail.

**Acceptance criteria:**
- [ ] Authenticated actor overrides client-supplied reviewer identity for new requests.
- [ ] PATCH operations cannot replace the stored decision context.
- [ ] Event detail returns a source-labelled summary; LLM failure produces deterministic text from persisted context.

**Verification:**
- [ ] `PYTHONPATH=. .venv/bin/pytest backend/tests/test_event_audit.py backend/tests/test_events.py -v`

**Dependencies:** Task 1

**Files likely touched:** `backend/app/api/dependencies.py`, `backend/app/api/v1/events.py`, `backend/app/services/event_service.py`, `backend/app/services/llm_service.py`, focused tests.

**Estimated scope:** Medium

### Checkpoint: Backend vertical slice

- [ ] Migration, event creation, retrieval, immutability and fallback tests pass.
- [ ] Existing event list/create response fields remain compatible.

### Phase 2: Browser capture and event detail

#### Task 3: Capture typed decision evidence during review

**Description:** Extend frontend wire types and payload builders so single-zone and grouped reviews submit the exact inference evidence needed for audit.

**Acceptance criteria:**
- [ ] Payload includes rule keys, PPE configuration, frame/time, zone snapshot, machine state, observations and system result.
- [ ] Event requests send the current bearer token so the backend can own the review actor.
- [ ] Existing privacy and occurrence-idempotency payload behavior is preserved.

**Verification:**
- [ ] `npm --prefix frontend run test -- use-monitor events`
- [ ] `npm --prefix frontend run type-check`

**Dependencies:** Task 2

**Files likely touched:** `frontend/src/types/index.ts`, `frontend/src/features/monitor/use-monitor.ts`, `frontend/src/features/monitor/use-monitor.test.ts`, `frontend/src/api/events.ts`.

**Estimated scope:** Medium

#### Task 4: Add accessible Event Detail for violation history

**Description:** Add a focused dialog that loads one event, presents structured AI → rule → HITL evidence and its summary, with loading/error/legacy states.

**Acceptance criteria:**
- [ ] An acknowledged event card opens a keyboard-accessible detail dialog.
- [ ] Structured audit remains primary and summary source is labelled.
- [ ] Legacy events without decision context show an explicit limited-audit state.

**Verification:**
- [ ] `npm --prefix frontend run test -- EventDetail EventLog`
- [ ] `npm --prefix frontend run build`

**Dependencies:** Task 3

**Files likely touched:** `frontend/src/features/events/EventDetailDialog.tsx`, colocated tests, `frontend/src/features/events/EventLogPage.tsx`, `frontend/src/api/events.ts`, `frontend/event-log.css`.

**Estimated scope:** Medium

#### Task 5: Expose reviewed audit to the Area Manager

**Description:** Let Area Managers open recent acknowledged and false-alarm reviews from their dashboard without changing official compliance counts.

**Acceptance criteria:**
- [ ] Area Manager can open event details from the dashboard.
- [ ] False alarms are visibly labelled and excluded from official violation KPIs.
- [ ] Empty, loading and API-error states remain clear.

**Verification:**
- [ ] `npm --prefix frontend run test -- App AreaManager`
- [ ] Browser runtime check at mobile and desktop widths when a browser runner is available.

**Dependencies:** Task 4

**Files likely touched:** `frontend/src/features/area/AreaManagerPage.tsx`, its test coverage, `frontend/src/features/events/EventDetailDialog.tsx`, `frontend/src/api/events.ts`, area/event styles.

**Estimated scope:** Medium

### Checkpoint: End-to-end audit flow

- [ ] Save actual violation and false alarm, reload, and open both details.
- [ ] Detail explains AI observation → rule decision → human review without raw video.

### Phase 3: Documentation and release gate

#### Task 6: Record US-16 behavior and verify the repository

**Description:** Update runtime documentation, central decisions/progress, current structure and the completed-story location after all acceptance criteria pass.

**Acceptance criteria:**
- [x] Runtime API/UI and retention policy are documented.
- [x] US-16 status and file placement are current in the repository context map/structure.
- [x] Focused and full checks pass on the synchronized feature branch.

**Verification:**
- [x] `make check`
- [x] `git diff --check`
- [x] Five-axis self-review finds no unresolved required issue.

**Dependencies:** Tasks 1-5

**Files likely touched:** `backend/README.md`, `frontend/src/features/events/README.md`, `docs/PROJECT_STRUCTURE.md`, `DECISIONS.md`, `PROGRESS.md`, US-16 spec/index files.

**Estimated scope:** Medium

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Legacy clients omit audit evidence | Medium | Keep nullable additive context and show a limited-audit state instead of inventing history. |
| Client evidence is inconsistent with event identity | High | Backend derives camera/zone/severity/reviewer/timestamps and validates strict nested input. |
| LLM hallucinates details | High | Structured context is always primary; deterministic fallback is always available and summary source is labelled. |
| Retention deadlines imply deletion that is not implemented | Medium | Document this slice as policy metadata only; track enforcement separately. |
| Stale stash overlaps newer event lifecycle and migration work | High | Keep current RBAC/area/track behavior, rebase the migration after the current head, and require focused plus full regression checks. |

## Open Questions Deferred from This Slice

- Legal-hold overrides and the scheduled retention-deletion worker.
- Append-only history for Area Manager lifecycle transitions after the original immutable HITL review.
- Reconstructing or replaying an entire monitoring session.
