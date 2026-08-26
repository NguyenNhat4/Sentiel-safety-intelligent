# Spec: Issue #43 — Distributed Vision Tracking State on PostgreSQL

## Status

- Phase: `SPECIFY`
- Issue: `#43 State Management Dính Chặt Với Process Memory (Nghẽn Tracking & Anti-flicker)`
- Approval required before implementation planning and code changes.

## Objective

Move the state required by ByteTrack identity continuity and PPE anti-flicker out of a particular GPU worker process while preserving the current ownership boundaries:

- the Vision layer still owns detection, association, ByteTrack behavior and PPE temporal smoothing;
- the backend owns persistence and session/frame orchestration;
- a GPU worker remains unable to connect directly to PostgreSQL;
- browser REST/WebSocket, rule evaluation, HITL and event contracts remain unchanged.

After this change, consecutive frames from one `monitoring_session_id` may reach different `safety_vision_v2` worker replicas without fragmenting tracking. If a worker stops after an acknowledged frame, another worker can restore the last committed state and continue with the same session-local `track_id` values and anti-flicker counters.

Ultralytics documents that consistent IDs depend on reusing tracker state across consecutive frames with `persist=True`; the current in-process dictionaries provide that continuity only while one process remains alive. This feature makes that state explicit and transferable instead of relying on worker affinity.

## Confirmed Scope

### In scope

- A new additive `safety_vision_v2` worker contract for tracked frames.
- Explicit, validated serialization and restoration of the minimal ByteTrack continuation state.
- Explicit, validated serialization and restoration of per-track PPE temporal smoothing state.
- Backend-owned PostgreSQL persistence with optimistic revision checks.
- Recovery when a GPU worker restarts or a later frame is routed to another replica.
- Cleanup on normal session end plus TTL cleanup for orphaned state.
- Focused migration, contract, concurrency, serialization and restart-continuity tests.
- Deployment documentation and a rollback path to `safety_vision_v1`.

### Out of scope

- Redis or another new datastore.
- A database connection or database credential in the Vision worker.
- Changes to zone/PPE rules, alert debounce, HITL, event identity, UI or frontend wire types.
- Tracking continuity across a newly created monitoring session, a video seek/replay, or frames submitted out of order.
- Backend process recovery for its separate in-memory violation occurrence state.
- New autoscaling policy or a general distributed job queue.
- Persisting images, JPEG bytes, embeddings, faces or biometric identity.

## Assumptions

1. Every tracked request already has the pair `(monitoring_session_id, frame_id)` and `frame_id` increases within the session.
2. PostgreSQL is the canonical production datastore; no Redis will be introduced.
3. State is committed after every accepted tracked frame so the recovery point is the latest acknowledged response.
4. `safety_vision_v1` remains byte-for-byte compatible as a rollback path. Multi-replica safety requires opting into `safety_vision_v2`.
5. A worker failure before the backend commits its response may cause that frame to be retried, but cannot overwrite newer committed state.
6. Normal session completion deletes state immediately. Orphaned rows expire after a configurable TTL whose default is 24 hours.
7. The worker runtime remains pinned to `ultralytics==8.4.115`; changing that version requires a state-compatibility test and, if necessary, a new state schema version.

## Ownership and Runtime Flow

Production owner is `backend`; the public Vision facade remains the provider of the versioned tracker-state representation.

```text
FrameInferenceService
  -> backend tracking-state coordinator
      -> load PostgreSQL row (state, revision, last_frame_id)
      -> RemoteVisionAdapter POST /v2/infer
          -> any GPU worker replica
              -> validate/import state
              -> YOLO detection + one ByteTrack update + PPE smoothing
              -> validate/export next state
      -> compare-and-swap PostgreSQL row
  -> existing backend rules, violation tracking, HITL and response flow
```

Dependency direction remains:

```text
backend services -> backend integration adapter -> worker HTTP boundary -> vision facade
backend services -> SQLAlchemy model -> PostgreSQL
vision facade -X-> backend database/model/service
```

## Worker Contract

### Compatibility

- Keep `GET /ping` and `POST /v1/infer` unchanged with `safety_vision_v1`.
- Add `GET /v2/ping` and `POST /v2/infer` with `safety_vision_v2`.
- Existing v1 clients and health checks must continue to pass unchanged.
- The backend uses v2 only when configured for the new contract. A rollback changes configuration back to v1; it does not require a schema downgrade.

### `POST /v2/infer` request

Multipart fields:

| Field | Contract |
|---|---|
| `request_id` | UUID, required; response correlation |
| `monitoring_session_id` | UUID, required |
| `frame_id` | integer `>= 0`, required |
| `state_revision` | integer `>= 0`, required; backend revision being advanced |
| `tracking_state` | JSON object or omitted only for revision `0`; validated before inference |
| `image` | valid JPEG, maximum 8 MiB, unchanged from v1 |

### `POST /v2/infer` response

The response retains the v1 observation fields and adds:

```json
{
  "contract_version": "safety_vision_v2",
  "request_id": "4f087f80-6f24-4ae7-b598-4d5a2dc28d43",
  "monitoring_session_id": "a8d50527-c1ad-4329-a5b9-d581170ee50d",
  "frame_id": 42,
  "base_state_revision": 17,
  "model_version": "yolo11m_safety-gpu-v2",
  "canonical_people": [],
  "people": [],
  "detections": [],
  "tracking_state": {
    "schema_version": "bytetrack_ppe_state_v1",
    "tracker": {},
    "smoother": {}
  }
}
```

The backend rejects mismatched request/session/frame/revision correlation before any database write.

### State envelope

`bytetrack_ppe_state_v1` contains only the values needed to continue processing the next consecutive frame:

- tracker frame counter and last allocated global track ID;
- active and temporarily lost tracks;
- for each retained track: identity, lifecycle flags/counters, class, score, bounding box, Kalman mean and covariance;
- smoothing configuration and per-person hat/vest present/missing streaks, confirmed-presence flags and lost-frame count.

Terminal removed tracks are not transferred. They cannot be reactivated and are excluded from the retained lost pool before export. A continuation-equivalence test must prove that omitting them does not change the next-frame output.

The schema enforces:

- finite numbers only; no `NaN` or infinity;
- fixed vector/matrix dimensions;
- allowed tracker lifecycle/class values;
- unique positive track IDs across active/lost pools;
- last allocated ID greater than or equal to every retained ID;
- bounded lists and maximum serialized state size of 512 KiB;
- smoothing histories only for positive track IDs;
- exact supported `schema_version` and compatible model/tracker metadata.

No pickle, Python object deserialization, executable data or arbitrary class import is allowed.

## Vision Execution Model

The v2 path is stateless between HTTP requests:

1. Run the shared YOLO model in predict mode for classes `hat`, `person` and `vest`.
2. Create a fresh ByteTrack instance using the pinned `bytetrack.yaml` configuration.
3. Restore the validated active/lost tracks, Kalman state, frame counter and last allocated ID.
4. Apply one ByteTrack update to the current detections.
5. Restore and apply the PPE temporal smoother.
6. Produce the same canonical observations as v1 and export the next state.

A worker-wide inference lock protects the shared Ultralytics predictor and its process-global track ID counter. Horizontal throughput comes from multiple worker replicas; unrelated sessions never share tracker state inside a replica.

The existing v1 per-session in-memory path remains present only for compatibility/rollback.

## PostgreSQL Model

Add one backend-owned table:

```text
vision_tracking_states
├── monitoring_session_id  varchar(36) primary key
├── contract_version       varchar(32) not null
├── state_schema_version   varchar(40) not null
├── revision               bigint not null, >= 0
├── last_frame_id          bigint not null, >= 0
├── state_payload          jsonb not null
├── updated_at             timestamptz not null
└── expires_at             timestamptz not null, indexed
```

There is intentionally no foreign key to `camera_sessions`: the same inference contract is used by direct-file camera sessions and browser/WebSocket monitoring sessions. `monitoring_session_id` is the lifecycle key in both flows.

The row contains technical tracking state only. It contains no image, snapshot, user identifier, credential or biometric embedding.

## Ordering and Concurrency

The backend coordinator uses short transactions and optimistic compare-and-swap rather than holding a database connection open during GPU inference:

1. Load current `revision`, `last_frame_id` and state.
2. Reject the request if `frame_id <= last_frame_id`.
3. Call any v2 worker with that state and revision.
4. Atomically update only if the stored revision is still the expected revision and the stored frame remains older.
5. On one conflict, reload and retry once if the submitted frame is still newer.
6. If another request already committed the same or a newer frame, raise the existing stale-frame failure. If a second conflict occurs, fail closed with a remote-state conflict; do not reset state.

This ordering has deterministic outcomes:

- if frame 10 commits before frame 11, frame 11 retries from frame 10 state;
- if frame 11 commits first, the late frame 10 is discarded as stale;
- a stale worker response cannot overwrite a newer row.

The SQLAlchemy mapper also declares `revision` as its `version_id_col`, and the explicit conditional update is covered by a two-session concurrency test.

## Retention and Failure Behavior

- Successful tracked inference: advance revision and extend `expires_at` in the same commit.
- Normal session end/replacement/error/completion: delete the matching tracking-state row through the coordinator's `end_session` path.
- Backend or worker crash: leave the last committed row available until TTL expiry.
- Expired state: delete lazily on access and through a bounded cleanup operation; a frame arriving after expiry starts only when its revision is zero, otherwise fails closed so continuity is not silently fabricated.
- Invalid/malformed/oversized worker state: reject response, do not update PostgreSQL, and emit a privacy-safe operational error.
- PostgreSQL unavailable: fail the tracked remote inference; never fall back to worker RAM or silently return a normal safety result.
- Worker timeout/crash: retry policy may resend the frame from the last committed state; only an authenticated, correlated, validated response may advance persistence.

## Configuration and Rollout

Add typed settings with bounded defaults:

```dotenv
VISION_REMOTE_CONTRACT_VERSION=safety_vision_v2
VISION_TRACKING_STATE_TTL_SECONDS=86400
VISION_TRACKING_STATE_MAX_BYTES=524288
```

Rollout order:

1. Deploy the backward-compatible worker image exposing v1 and v2.
2. Deploy the PostgreSQL migration and backend code while backend remains configured for v1.
3. Verify `/v2/ping` and a controlled v2 continuity probe.
4. Switch Railway backend to `safety_vision_v2`.
5. Confirm continuity across two worker instances/restart before raising the RunPod replica limit.

Rollback sets `VISION_REMOTE_CONTRACT_VERSION=safety_vision_v1` and redeploys the backend. Persisted v2 rows may remain until TTL cleanup; they are ignored by v1 and contain no required business record.

## Tech Stack

- Python `3.11`.
- FastAPI and Pydantic v2 for the worker boundary.
- Ultralytics `8.4.115` and ByteTrack for detection association.
- SQLAlchemy 2.x and Alembic for backend persistence/migration.
- PostgreSQL `jsonb` for the versioned, validated state envelope.
- Pytest for unit, integration, contract and migration regression coverage.

Official implementation references:

- Ultralytics tracking persistence: <https://docs.ultralytics.com/modes/track/#persisting-tracks-loop>
- PostgreSQL JSON types: <https://www.postgresql.org/docs/current/datatype-json.html>
- SQLAlchemy version counters: <https://docs.sqlalchemy.org/en/20/orm/versioning.html>

## Commands

No local application runtime is started. Verification commands are:

```bash
PYTHONPATH=. .venv/bin/pytest vision/tests/test_tracking.py -v
PYTHONPATH=. .venv/bin/pytest backend/tests/test_remote_vision.py backend/tests/test_vision_worker.py -v
PYTHONPATH=. .venv/bin/pytest backend/tests/test_vision_tracking_state.py backend/tests/test_vision_tracking_state_migration.py -v
PYTHONPATH=. .venv/bin/alembic heads
make check
make vision-worker-gpu-image
```

Deployment follows the repository's Railway/RunPod runbooks after all checks pass. Image publication, Railway redeploy and RunPod mutation require the existing deployment credentials and use an immutable image tag.

## Project Structure

Only the existing owners/layers are extended:

```text
backend/app/models/vision_tracking_state.py
    SQLAlchemy persistence model
backend/app/schemas/remote_vision.py
    v1 unchanged; bounded v2 wire/state schemas added
backend/app/services/vision_tracking_state_service.py
    load/CAS/retry/delete/expiry orchestration
backend/app/integrations/remote_vision.py
    pure HTTP translation for v1 and v2
backend/app/services/frame_inference_service.py
    passes frame identity to the configured remote coordinator
backend/app/vision_worker.py
    additive /v2 endpoints
backend/migrations/versions/20260825_01_add_vision_tracking_states.py
    reversible PostgreSQL migration
vision/api.py
    public state-aware inference method and smoother export/import
vision/tracking_state.py
    ByteTrack continuation serializer/restorer
vision/tests/test_tracking.py
    same-process versus serialize/restore equivalence
backend/tests/test_remote_vision.py
backend/tests/test_vision_worker.py
backend/tests/test_vision_tracking_state.py
backend/tests/test_vision_tracking_state_migration.py
    boundary, persistence and recovery regression coverage
```

No new top-level directory and no frontend change are needed. Any created module/file and the final filesystem are recorded in `docs/PROJECT_STRUCTURE.md`.

## Code Style

Use typed Pydantic/SQLAlchemy boundaries, explicit domain errors and no unvalidated `dict` crossing the HTTP/database boundary. Keep integration adapters free of persistence decisions.

```python
class TrackingStateConflictError(RuntimeError):
    """A newer frame advanced the persisted session state."""


def compare_and_swap(
    self,
    *,
    session_id: str,
    expected_revision: int,
    frame_id: int,
    state: TrackingStateEnvelope,
) -> int:
    """Persist validated state only when the caller still owns the revision."""
```

Naming uses `monitoring_session_id` at public boundaries, `session_id` only as a local shorthand, `state_revision` on the wire and `revision` in the ORM model. Ruff formatting/lint rules remain authoritative.

## Testing Strategy

### Test-first sequence

1. Add a failing serializer round-trip test for ByteTrack and PPE smoothing.
2. Add a failing continuation-equivalence test: uninterrupted frames and a serialize/restore boundary must return the same person track IDs and absence-confirmation sequence.
3. Add failing v2 request/response validation tests, including size, dimensions, finite floats, correlation and auth.
4. Add failing PostgreSQL model/migration and CAS conflict tests.
5. Add a failing coordinator recovery test that alternates fake worker replicas and simulates a worker restart.
6. Implement the smallest slice needed to pass each group.

### Required cases

- v1 health/inference tests remain unchanged and pass.
- First v2 frame creates state at revision 1.
- A later frame restores the exact numeric person `track_id` after using another facade/worker instance.
- Hat/vest grace and missing streaks continue across restart without one-frame flicker/reset.
- Two unrelated sessions stay isolated even when alternated through the same process.
- A stale frame and a stale worker response cannot overwrite newer state.
- One CAS conflict retries from the winning state; a second conflict fails closed.
- End-session deletion and TTL expiry are covered.
- Invalid, oversized or non-finite state never reaches PostgreSQL or the tracker.
- Worker has no database dependency/credential.
- Existing backend rule, violation and frontend contract suites show no regression.

The repository currently has nine known baseline test failures inherited from `develop2`; verification must distinguish those unchanged failures from any new regression and must not delete or weaken the baseline tests.

## Performance and Security Constraints

- Do not hold a PostgreSQL transaction/connection during the remote GPU call.
- At the current four-camera, 2 FPS default, PostgreSQL receives at most eight state updates per second before retries.
- Record state payload bytes and persistence duration through the existing privacy-safe operational metric boundary; never log the payload.
- Benchmark p50/p95 database persistence and total remote RTT before raising worker replicas. The feature is acceptable only if persistence remains within the existing frame budget and the 512 KiB cap is not reached during the controlled multi-camera test.
- Authenticate v2 exactly as v1, compare bearer tokens safely, retain the 8 MiB JPEG limit and add the independent state-size limit.
- Validate all worker output as untrusted input. Never deserialize pickle or import a class named by the payload.
- Do not store raw images, credentials, face data or user data in `vision_tracking_states`.

## Boundaries

### Always do

- Preserve backend/Vision ownership and v1 compatibility.
- Validate state before inference and again before persistence.
- Use optimistic revision/frame guards and fail closed on ambiguity.
- Keep migrations reversible and update root `DECISIONS.md`, `PROGRESS.md`, context/deployment docs and current project structure.
- Run focused tests and `make check` before deployment.

### Ask first

- Any breaking browser, REST, WebSocket, rule or event change.
- Adding Redis, a message queue, a new dependency or a new top-level directory.
- Giving a Vision worker database credentials.
- Changing state retention beyond the confirmed technical-state purpose.
- Publishing an image, pushing Git, changing Railway variables or raising RunPod replicas if credentials/scope are not already available.

### Never do

- Edit `docs/FUTURE_PROJECT_STRUCTURE.md`.
- Put database/query code in `vision/` or the worker.
- Fall back to process RAM when v2 persistence fails.
- Reset tracking silently and report a fabricated normal result.
- Persist/log JPEG bytes, tokens or the full state payload.
- Remove/relax existing tests to hide regressions.

## Success Criteria

1. A controlled sequence processed uninterrupted and the same sequence split across two fresh worker instances produces identical person `track_id` sequences and PPE absence-confirmation transitions.
2. Killing the first worker after a committed frame and routing the next frame to another worker preserves the existing IDs and anti-flicker history.
3. Alternating two independent monitoring sessions across replicas never leaks IDs, Kalman state or smoother history between sessions.
4. Concurrent/stale updates are deterministically rejected or retried; no older state overwrites a newer frame.
5. v1 contract tests remain unchanged and passing; backend browser contracts, safety rules and event semantics do not change.
6. PostgreSQL rows contain only bounded, schema-versioned technical JSON state and are deleted on normal end or after TTL.
7. The worker image contains no PostgreSQL client configuration and receives no `DATABASE_URL`.
8. Focused new tests pass, `make check` introduces no new failures beyond the documented nine-test baseline, and the GPU image builds.
9. Railway migration/backend and the backward-compatible GPU worker are deployed in the stated order, health-checked, and have a tested v1 configuration rollback.

## Open Questions

None. Any discovery that invalidates an assumption above must update this spec and return it for approval before implementation continues.
