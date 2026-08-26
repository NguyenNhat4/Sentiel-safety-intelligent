# Implementation Plan: Issue #43 Distributed Tracking State

## Status

- Specification: approved by the user on 2026-08-25.
- Source of truth: `specs/ISSUE-43-DISTRIBUTED-TRACKING-STATE-SPEC.md`.
- Phase: implementation, RunPod GPU v2 activation and Railway v2 rollout complete; controlled restart/two-replica and rollback evidence remains.
- Prior US-29 implementation is delivered; its remaining browser UAT gate remains tracked in root `PROGRESS.md`.

## Overview

Add a backward-compatible `safety_vision_v2` path that transfers validated ByteTrack and PPE temporal state on every tracked frame. The backend persists the state in PostgreSQL with frame/revision compare-and-swap; GPU workers stay database-free and can be replaced or horizontally replicated without resetting session-local identity or anti-flicker history.

## Dependency Graph

```text
Vision continuation codec + equivalence proof
    -> bounded v2 Pydantic contract
        -> v2 worker endpoint
        -> outbound v2 HTTP adapter
            -> PostgreSQL model + migration
                -> tracking-state CAS service
                    -> frame inference orchestration
                        -> lifecycle cleanup + observability
                            -> deployment/docs/verification
```

The codec is the first gate because the remaining design is invalid unless a fresh tracker can continue with equivalent IDs and smoothing transitions.

## Architecture Decisions

- Keep `safety_vision_v1` unchanged; v2 is additive and configuration-selected.
- Use an explicit JSON DTO, never pickle, for active/lost ByteTrack state and PPE smoother histories.
- Keep the worker stateless between v2 requests. A worker-wide lock protects the shared Ultralytics predictor and process-global ByteTrack ID counter.
- Keep persistence orchestration in a backend service; the HTTP adapter performs protocol translation only and `vision/` has no database imports.
- Store one JSONB row per `monitoring_session_id`, with `revision`, `last_frame_id`, timestamps and schema/contract versions.
- Use short transactions and conditional revision/frame updates. Never hold a database connection during GPU inference.
- Allow one bounded CAS retry. Reject a late frame or repeated conflict without resetting the tracker.
- Delete state on normal session end and expire crash-orphaned rows after the configured TTL.
- Keep frontend, rule, HITL and event contracts unchanged.

## Implementation Phases

### Phase 1: Prove portable Vision state

- Task 1: Implement and prove ByteTrack/PPE state continuation.
- Checkpoint A: uninterrupted and serialize/restore runs are equivalent; session isolation holds.

### Phase 2: Establish the backward-compatible worker boundary

- Task 2: Add bounded v2 wire schemas and worker endpoint.
- Task 3: Add v2 support to the outbound HTTP adapter.
- Checkpoint B: all v1 tests remain unchanged; v2 auth, correlation and validation tests pass.

### Phase 3: Persist and coordinate state

- Task 4: Add PostgreSQL model and reversible Alembic migration.
- Task 5: Add the backend tracking-state CAS repository/service.
- Checkpoint C: PostgreSQL create/upgrade/downgrade and two-session CAS tests pass without holding a transaction across a fake remote call.

### Phase 4: Integrate the complete frame/session flow

- Task 6: Route tracked remote frames through the persistent coordinator.
- Task 7: Add end-session/TTL cleanup and privacy-safe operational evidence.
- Checkpoint D: alternating fake replicas and simulated restart preserve IDs/smoothing; stale frames fail closed; existing rules/events remain unchanged.

### Phase 5: Document, verify and deploy

- Task 8: Update decisions, progress, architecture/runbooks and environment examples.
- Task 9: Run full verification, build the GPU image, deploy in compatibility-first order and execute recovery/rollback smoke tests.
- Checkpoint E: no new regression beyond the documented nine-test `develop2` baseline, immutable worker image healthy, Railway migration/backend healthy, and v1 rollback proven.

## Verification Checkpoints

### Checkpoint A — Vision codec

```bash
PYTHONPATH=. .venv/bin/pytest vision/tests/test_tracking.py -v
```

Required evidence: identical person track IDs and PPE absence-confirmation transitions on uninterrupted versus serialize/restore sequences.

### Checkpoint B — HTTP contract

```bash
PYTHONPATH=. .venv/bin/pytest backend/tests/test_remote_vision.py backend/tests/test_vision_worker.py -v
```

Required evidence: existing v1 tests pass without changed expectations; v2 rejects malformed, oversized, non-finite and mismatched state.

### Checkpoint C — PostgreSQL persistence

```bash
PYTHONPATH=. .venv/bin/pytest backend/tests/test_vision_tracking_state.py backend/tests/test_vision_tracking_state_migration.py -v
PYTHONPATH=. .venv/bin/alembic heads
```

Required evidence: one Alembic head, reversible table creation and deterministic CAS conflict behavior. The migration/CAS path must also be exercised against PostgreSQL in the deployment verification environment.

### Checkpoint D — Integrated recovery

```bash
PYTHONPATH=. .venv/bin/pytest backend/tests/test_frame_inference_ppe.py backend/tests/test_us29_media_runtime.py -v
```

Required evidence: worker replacement does not reset ID/smoothing, cleanup executes on completion/error/replacement, and no browser/rule payload changes.

### Checkpoint E — Release

```bash
make check
make vision-worker-gpu-image
```

Deployment verification uses immutable tags and repository Railway/RunPod runbooks. No Git push, image push, Railway mutation or RunPod replica change is implicit in a local test command.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Ultralytics internal tracker fields change | Restored state becomes invalid | Pin worker `8.4.115`, version DTO, validate dimensions, and run equivalence/startup tests |
| ByteTrack uses a process-global ID counter | IDs leak or race across sessions | Fresh tracker per request plus worker-wide lock and explicit last-ID restore |
| JSON state grows with track history | Latency/bandwidth/DB pressure | Export only active/lost tracks, cap lists and payload at 512 KiB, measure bytes/p95 |
| Concurrent same-session frames race | Older state overwrites newer state | `frame_id` guard, revision CAS, one retry, then fail closed |
| DB transaction held during GPU request | Pool exhaustion | Load and CAS in separate short transactions; remote call occurs between them |
| Worker returns hostile/corrupt state | Crash or unsafe deserialization | Strict Pydantic validation, finite numbers, fixed dimensions, no pickle/dynamic imports |
| v2 rollout breaks production | Camera inference unavailable | Deploy dual-contract worker first, migrate backend while v1 remains active, switch by config, retain v1 rollback |
| Existing branch has nine baseline failures | New regressions are obscured | Capture focused green suites and compare full failures to the documented `develop2` baseline |

## Files and Ownership

- Vision owner: `vision/tracking_state.py`, `vision/api.py`, `vision/tests/test_tracking.py`.
- Backend schema/integration owner: `backend/app/schemas/remote_vision.py`, `backend/app/integrations/remote_vision.py`, `backend/app/vision_worker.py` and focused tests.
- Backend persistence/service owner: new ORM model, migration, tracking-state service and focused tests.
- Backend runtime owner: `frame_inference_service.py`, `camera_session_runtime.py` and current runtime tests.
- Cross-cutting documentation: root decision/progress/context files, current structure and remote-worker deployment runbook.

## Open Questions

None. A failed continuation-equivalence checkpoint requires revising the approved spec before proceeding to persistence or deployment.
