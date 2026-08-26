# Issue #43 Implementation Checklist

## Task 1: Prove portable ByteTrack and PPE smoother state

**Description:** Add a versioned Vision-owned codec that exports/restores the minimal active/lost ByteTrack continuation state and PPE smoother history, then prove equivalence across a fresh facade/tracker boundary.

**Acceptance criteria:**

- [x] DTO round-trip preserves frame counter, last allocated ID, active/lost Kalman state and all PPE streak/confirmation fields.
- [x] Uninterrupted and serialize/restore frame sequences emit identical person track IDs and absence-confirmation transitions.
- [x] State is bounded, finite, session-independent and contains no removed tracks, image bytes or executable serialization.

**Verification:**

- [x] `PYTHONPATH=. .venv/bin/pytest vision/tests/test_tracking.py -v` (`21 passed`)

**Dependencies:** None.

**Files likely touched:**

- `vision/tracking_state.py`
- `vision/api.py`
- `vision/tests/test_tracking.py`

**Estimated scope:** Medium (3 files).

## Checkpoint A: Vision continuation proof

- [x] Task 1 tests pass.
- [x] A fresh worker/facade continuation is equivalent to uninterrupted processing.
- [x] Equivalence succeeded; no spec revision required.

## Task 2: Add bounded v2 worker schemas and endpoint

**Description:** Preserve v1 and add typed v2 health/inference/state contracts plus authenticated worker routing and defensive validation.

**Acceptance criteria:**

- [x] `/ping` and `/v1/infer` behavior/tests remain unchanged.
- [x] `/v2/ping` and `/v2/infer` correlate request/session/frame/revision and return validated next state.
- [x] Invalid JPEG/state, non-finite values, bad dimensions and payloads over 512 KiB fail before Vision execution.

**Verification:**

- [x] `PYTHONPATH=. .venv/bin/pytest backend/tests/test_vision_worker.py -v` (`11 passed`)

**Dependencies:** Task 1.

**Files likely touched:**

- `backend/app/schemas/remote_vision.py`
- `backend/app/vision_worker.py`
- `backend/tests/test_vision_worker.py`

**Estimated scope:** Medium (3 files).

## Task 3: Add pure HTTP v2 adapter support

**Description:** Extend the outbound adapter to select v1/v2, send the state envelope on tracked v2 frames, and reject all untrusted or mismatched responses without persistence logic.

**Acceptance criteria:**

- [x] v1 adapter behavior remains compatible.
- [x] v2 request encodes the correct state/revision/frame and returns a typed correlated result.
- [x] Timeout, auth/status, malformed JSON, bounded state and mismatched correlation fail closed.

**Verification:**

- [x] `PYTHONPATH=. .venv/bin/pytest backend/tests/test_remote_vision.py -v` (`9 passed`)

**Dependencies:** Task 2.

**Files likely touched:**

- `backend/app/integrations/remote_vision.py`
- `backend/tests/test_remote_vision.py`
- `backend/app/core/config.py`

**Estimated scope:** Medium (3 files).

## Checkpoint B: Backward-compatible contract

- [x] Tasks 2–3 focused tests pass (`18 passed`).
- [x] Existing v1 assertions were not weakened or deleted.
- [x] Worker has no PostgreSQL dependency/import/credential.

## Task 4: Add the PostgreSQL tracking-state model and migration

**Description:** Add the backend-owned JSONB state row and a reversible Alembic revision at the current single head.

**Acceptance criteria:**

- [x] The ORM contains the approved key/version/revision/frame/payload/timestamp fields and revision mapper guard.
- [x] Upgrade creates constraints/indexes; downgrade removes them cleanly; no foreign key excludes WebSocket sessions.
- [x] Migration chain has exactly one head and PostgreSQL JSONB is canonical.

**Verification:**

- [x] `PYTHONPATH=. .venv/bin/pytest backend/tests/test_vision_tracking_state_migration.py -v` (`3 passed`)
- [x] `PYTHONPATH=. .venv/bin/alembic heads` (`20260825_01 (head)`)

**Dependencies:** Checkpoint B.

**Files likely touched:**

- `backend/app/models/vision_tracking_state.py`
- `backend/app/models/__init__.py`
- `backend/migrations/versions/20260825_01_add_vision_tracking_states.py`
- `backend/tests/test_vision_tracking_state_migration.py`

**Estimated scope:** Medium (4 files).

## Task 5: Implement load/CAS/retry state persistence

**Description:** Add a backend service that loads validated state, advances it with a conditional revision/frame update, retries one conflict and handles TTL/deletion without holding DB resources during remote inference.

**Acceptance criteria:**

- [x] First frame creates revision 1; later frames advance monotonically.
- [x] Stale frame/response cannot overwrite newer state; one valid conflict retries, a second fails closed.
- [x] Payload limits, TTL and validation apply before commit, and the remote callback runs outside a DB transaction.

**Verification:**

- [x] `PYTHONPATH=. .venv/bin/pytest backend/tests/test_vision_tracking_state.py -v` (`10 passed`)

**Dependencies:** Task 4.

**Files likely touched:**

- `backend/app/services/vision_tracking_state_service.py`
- `backend/tests/test_vision_tracking_state.py`
- `backend/app/core/config.py`

**Estimated scope:** Medium (3 files).

## Checkpoint C: Durable ordering

- [x] Tasks 4–5 focused tests pass.
- [x] Alembic has one head and reversible PostgreSQL DDL.
- [x] Two independent SQLAlchemy sessions prove CAS protection.
- [x] No connection/transaction remains open during fake GPU latency.

## Task 6: Integrate v2 state with frame inference

**Description:** Pass the existing `(monitoring_session_id, frame_id)` identity through the remote v2 coordinator while retaining local/v1 analyzer compatibility and unchanged downstream rule output.

**Acceptance criteria:**

- [x] Remote v2 tracked frames load/call/CAS through the coordinator; untracked and v1 paths retain current behavior.
- [x] Alternating fresh replicas preserves exact IDs and anti-flicker state after a simulated crash.
- [x] Existing browser/rule/event schemas and local Vision behavior remain unchanged.

**Verification:**

- [x] Focused v2 frame-orchestration and remote-adapter tests pass.

**Dependencies:** Task 5.

**Files likely touched:**

- `backend/app/services/frame_inference_service.py`
- `backend/app/services/vision_tracking_state_service.py`
- `backend/tests/test_frame_inference_ppe.py`
- `backend/tests/test_vision_tracking_state.py`

**Estimated scope:** Medium (4 files).

## Task 7: Complete lifecycle cleanup and observability

**Description:** Route completion/error/replacement/end-session through persistent state cleanup and record only bounded privacy-safe size/latency/outcome evidence.

**Acceptance criteria:**

- [x] Normal session completion, error, stop and replacement delete the matching state row.
- [x] Orphaned rows expire through bounded cleanup; unavailable DB or invalid state never falls back to worker RAM.
- [x] Metrics/logs include outcome/duration/bytes but never state, image or credentials.

**Verification:**

- [x] Lifecycle, tracking-state and operational-metric focused suites pass.

**Dependencies:** Task 6.

**Files likely touched:**

- `backend/app/services/camera_session_runtime.py`
- `backend/app/services/frame_inference_service.py`
- `backend/app/services/vision_tracking_state_service.py`
- `backend/tests/test_us29_media_runtime.py`
- `backend/tests/test_vision_tracking_state.py`

**Estimated scope:** Medium (5 files).

## Checkpoint D: Integrated restart recovery

- [x] Tasks 6–7 focused tests pass.
- [x] Two workers/replicas and one restart preserve identity and smoothing.
- [x] Stale/conflicting frames fail closed without fabricated normal results.
- [x] Existing rule, HITL and event contracts are unchanged; full-suite baseline comparison remains in Task 9.

## Task 8: Update decisions, configuration and deployment documentation

**Description:** Record the approved boundary/rollout decision, configuration and operator steps while keeping the context map as the only documentation index.

**Acceptance criteria:**

- [x] Root decision and migration/worker docs describe PostgreSQL ownership, v2 compatibility, TTL and rollback; final verification evidence remains for `PROGRESS.md`.
- [x] Environment examples contain bounded v2 settings without secrets or worker database variables.
- [x] Current project structure lists every created file and the RunPod guide no longer requires affinity for v2.

**Verification:**

- [x] `git diff --check`

**Dependencies:** Checkpoint D.

**Files likely touched:**

- `DECISIONS.md`
- `PROGRESS.md`
- `.env.development.example`
- `docs/ops/RUNPOD_VISION_DEPLOYMENT.md`
- `docs/PROJECT_STRUCTURE.md`

**Estimated scope:** Medium (5 files).

## Task 9: Full verification and compatibility-first deployment

**Description:** Run all repository gates, build/publish an immutable dual-contract GPU image, migrate/deploy Railway while still on v1, switch to v2 only after a controlled probe, and prove rollback.

**Acceptance criteria:**

- [x] Focused suites pass and full verification introduces no failures beyond the documented nine-test baseline.
- [ ] Immutable GPU worker is published and live RunPod v1/v2 health/inference pass; controlled restart/two-replica evidence remains.
- [ ] Railway migration/backend health and the v2 switch pass; an explicit v1 revert smoke remains.

**Verification:**

- [x] `make check` (exact baseline: `9 failed, 288 passed`; root `32 passed`, frontend `89 passed`)
- [x] `make vision-worker-gpu-image`
- [x] Railway PostgreSQL migration/health smoke (`20260825_01`, deployment `7fa46e2a-c38e-4820-95d7-f581ece2dddb`, `/health` 200 ready)
- [ ] RunPod `/v1/infer` and `/v2/infer` pass; restart/two-replica and rollback smoke remain.

**Dependencies:** Task 8.

**Files likely touched:**

- No production source changes; verification evidence updates `PROGRESS.md` only.

**Estimated scope:** Small (1 documentation file plus external deployment state).

## Checkpoint E: Complete

- [ ] All approved spec success criteria are met; live RunPod v2 recovery smoke remains.
- [x] `make check` result and unchanged baseline failures are recorded accurately.
- [x] GPU image is published, RunPod serves the v3 dual-contract worker, and the Railway v2 release is healthy.
- [ ] Rollback path is verified.
- [ ] No commit/push is performed unless the user requests it explicitly.
