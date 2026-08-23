# Project Progress

Updated: 2026-08-23

This file is the current project snapshot, not a chronological changelog. Use Git history for completed implementation detail. Entries are grouped by owning area so contributors can load only the context relevant to the next task.

## Current State

### 2026-08-23 Conflict resolution

- [Cross-cutting] Đã hợp nhất conflict camera configuration: `asset_id` nullable, disconnect ngoài dropdown, preview empty state và lưu được trạng thái null.
- [Vision] Đã hợp nhất rule zone/PPE: zone intrusion không phụ thuộc machine state; PPE chỉ áp dụng cho người inside zone khi máy running; bỏ fallback requirement của zone khác.
- [Cross-cutting] Đã thêm cảnh báo contract bắt buộc đọc trong `docs/architecture/alert-rule-contract.md`.

### Cross-cutting

- The MVP is a React 19 frontend, FastAPI modular monolith, Vision facade, PostgreSQL persistence, and backend-owned media assets in a Railway Bucket with an application-volume inference cache.
- The standard contributor workflow remains `make setup` then `make run`; Alembic upgrades are part of that flow.
- Three authenticated roles are supported: `system_admin`, `safety_manager`, and `area_manager`. New and administrator-reset accounts must replace their temporary password.
- The implemented safety flow covers four fixed camera slots, per-camera zones/rules, direct video/image inference, Human-in-the-Loop review, immutable decision context, privacy-redacted evidence, event history, and area-scoped follow-up.
- Documentation under `docs/` is organized into `docs/architecture/`, `docs/ops/`, and `docs/data/` subdirectories; root `context-map.md` and `docs/PROJECT_STRUCTURE.md` are updated to reflect the new paths.
- Deployment flow diagrams and team runbook for `deploy_all_production.sh` and CI/CD are documented in `docs/ops/DEPLOYMENT_FLOW.md` and indexed in `context-map.md`.
- `scripts/sync_code_to_google_drive.sh` provides an opt-in rclone backup of Python source from `backend/app` and `vision` only; credentials remain in the user's rclone configuration.

### Backend

- US-29 backend runtime owns bucket-backed media assets, atomic fixed-camera configuration aggregates, and explicit direct OpenCV image/video sessions with persisted lifecycle evidence.
- Four fixed camera configurations support unique READY asset assignment and atomic asset/zone/PPE saves.
- Each configured camera can have revisioned, disjoint four-point zones and persisted rules keyed by `(camera_id, zone_id)`.
- Authenticated `/api/v1/ws/camera-detections` publishes session-correlated detection metadata for fixed cameras.
- Event persistence is idempotent by occurrence. One tracked person/session log accumulates active hat, vest, restricted-area, and zone rules; submitted human outcomes remain authoritative.
- `decision_context_v1` stores immutable observation, rule, actor, outcome, and retention deadlines. False alarms remain auditable but are excluded from official violation statistics.
- Operational metrics use a bounded, privacy-safe rotated JSONL file and support one writer process.
- PostgreSQL-only is the approved database contract. Removal and end-to-end verification of any remaining legacy SQLite defaults/fallbacks is still an open migration task.

### Vision

- `models/yolo11m_safety.pt` is the only runtime safety detector. One `[0,3,4]` call per sampled frame supplies canonical `person`, `hat`, and `vest` observations plus session-isolated ByteTrack IDs.
- Safety Vision can run in-process or through the versioned `safety_vision_v1` HTTP worker. The backend keeps rule evaluation and persistence in both modes; local remains the default and remote is opt-in.
- Missing PPE is derived by deterministic backend rules, not emitted by the model.
- PPE review opens after six consecutive missing frames for the same session track/item. An unreviewed warning retracts only after two continuous seconds of explicit presence.
- Zone intrusion opens after four consecutive sampled frames in the same active zone. Restricted-area detection remains immediate.
- Snapshot persistence runs YuNet face redaction first, falls back per person, then annotates and persists. Failure remains closed.
- Fixed-camera sessions now use isolated YOLO/ByteTrack instances concurrently, serialize only same-session access, and release model state on completion/error while retaining occurrence context for queued review.

### Frontend

- Live Monitor always renders four slots with direct video/image playback, source-coordinate overlays, server lifecycle, rolling inference FPS, and per-video Replay at EOF.
- Camera configuration is hidden from the sidebar and opens only when `safety_manager` selects a Live Monitor slot; `system_admin` owns the media library.
- Camera configuration binds hat/vest draft state directly to the selected zone, reloads persisted switches correctly, and no longer offers unsaveable PPE controls when no zone exists.
- HITL logs retain their own inference frame/context and are opened explicitly by the Safety Officer. Pending counts exclude reviewed logs.
- Area managers have a server-scoped compliance/event workspace and may resolve or mark false alarm only for events in their assigned area.
- Camera configuration now exposes camera-wide machine state immediately after camera selection; PPE controls appear for a selected draft zone before its four points are complete.
- Live Monitor queues direct-camera review candidates with their inference snapshot and persists one idempotent reviewed event per affected tracked person before advancing the queue.

### Media And Delivery

- Sys Admin uploads image/video assets directly to the Singapore Railway Bucket through presigned POST. Backend verifies metadata and the first decoded frame before `READY`; `MEDIA_ASSET_DIR` is the OpenCV read-through cache.
- Presigned GET playback preserves byte-range streaming without proxying full videos through `p047-app`. Run starts every valid configured camera; Replay creates one fresh camera session and resets playback to the beginning.
- Explicit Run starts every valid camera independently; Replay creates a fresh session for one completed video. Sessions never auto-resume after restart.
- Images infer exactly once without frame debounce. Videos stop at EOF and report inference throughput over a rolling five-second window.
- `scripts/deploy_all_production.sh` gates, publishes, redeploys, waits for Railway success, and checks the application health endpoint.
- `Dockerfile.ai` and `requirements.ai.txt` package a standalone CPU proof worker with `/ping` and `/v1/infer`; deployment remains a separate rollout step.

## Latest Verification

- Camera-configuration regression coverage passes with both hat and vest enabled through save/reload; all 75 frontend tests and the production build pass. Full `make check` remains blocked only by the pre-existing `.env.production` expectation in `backend/tests/test_config.py`; ESLint has only the pre-existing `App.tsx` exhaustive-deps warning.
- Repository verification passes: 25 root tests, 199 backend/Vision tests, 72 frontend tests, Ruff, ESLint, TypeScript and production build.
- Railway deployment `4b593f2a-18c8-49b0-811a-d2297a2e5ad3` reached `SUCCESS`; PostgreSQL is at `20260823_01`, the app media volume is writable, `/health` is ready in production, and authenticated media/configuration/session smoke passed.
- Production Streamer and MediaMTX services were removed, the old Streamer volume was scheduled for deletion, and obsolete HLS/RTSP/Streamer variables were removed from `p047-app`.
- Server-camera inference now bypasses the internal JPEG/Base64 encode-decode round trip, downsizes oversized frames to the configured inference size, and restores detections to source-frame coordinates. The focused inference/media suite passes `24 passed`; a 1080p synthetic micro-benchmark measured the removed round trip at `39.36 ms/frame` versus `0.99 ms/frame` for the retained resize on this workstation.
- The standalone `p047-vision:dev` CPU image builds successfully and its live `/ping` smoke returns `safety_vision_v1`; frontend dependency audit reports zero known vulnerabilities after the compatible `nanoid` patch update.
- Railway deployment `bfe08eab-c477-4e9f-b211-bba93166ccd0` reached `SUCCESS`; PostgreSQL is at `20260823_02`, `/health` is ready, and production completed a 31,389,527-byte direct bucket upload with `POST .../complete` returning 200 in 1.882 seconds.
- The existing `cbucket` is shared safely by prefixes: `snapshots/` for redacted evidence and `media-assets/` for uploaded media. The one legacy 26,193,014-byte volume asset was copied, size-verified, switched to S3 in PostgreSQL, and removed from canonical volume storage.
- Inference hardening now applies restricted-area rules camera-wide, closes PPE occurrences when their zone/machine requirement becomes inapplicable, runs independent camera models concurrently, drops stale sampled frames, throttles per-frame session DB writes, records direct-camera latency/drop outcomes, validates fixed-camera occurrence ownership, and restores direct-camera HITL persistence.
- Violation review alerts are now limited to one per person (`track_id`) for the full `monitoring_session_id`; later rules or re-violations remain observable without opening another review.
- Railway worktree deployment `c617b5ca-93ca-4ad1-93f2-515024d8e1a0` reached `SUCCESS`; `/health` reports production ready with PostgreSQL and snapshot storage ready. The local Docker publish path was unavailable, so the configured mutable Docker Hub source still needs republishing before a later image-source redeploy.

## Open Gates

- Measure end-to-end direct-file inference freshness and model latency on Railway; focused evidence does not yet prove four-camera throughput.
- Complete browser UAT from upload through real-model HITL review and persisted event.
- Run browser UAT for camera configuration, two-zone save/reload, mixed rule states, overlays, grouped review, Event Detail, and Area Manager follow-up.
- Run a real 200-viewer x four-camera 30-minute soak with CPU, RSS, egress, errors, and first-frame latency before making a capacity claim.
- Complete the PostgreSQL-only runtime migration and validate the full Alembic chain against PostgreSQL.
- Add the retention cleanup scheduler for persisted US-16 metadata/snapshot deadlines.
- Complete US-13 protocol, representative ground truth, calibration/final split, accuracy thresholds, association/tracking evidence, and target-device latency.
- Configure and exercise the GitHub production environment, first protected release PR, and immutable rollback procedure.
- Deploy one remote Vision worker, verify backend-to-worker health/inference, and benchmark the Railway/RunPod hop before GPU optimization.

## Known Limitations

- Six missing frames, two-second PPE revoke, four intrusion frames, confidence, and NMS values are MVP defaults pending held-out calibration.
- YuNet plus person fallback is fail-closed but still needs representative privacy recall and license/provenance sign-off before pilot use.
- JSONL operational metrics do not support multi-worker deployment; use a centralized sink before scaling backend workers.
- Telegram delivery is disabled until `TELEGRAM_BOT_TOKEN` and recipient chat IDs are configured; provider failure never blocks inference.
- Only three of four required local demo media assets were previously available, and browser DevTools automation is not configured.

## Next Steps

0. [Frontend] Đã sửa Live Monitor giữ playback request sau khi Replay/Run trả về session COMPLETED sớm; focused test, lint, type-check và production build đã pass. Chưa deploy Railway vì worktree còn thay đổi ngoài scope cần được tách trước.
1. Prove an uploaded asset reaches model, rule, HITL log, and persisted event end to end on Railway.
2. Run the two-zone browser UAT and record results.
3. Finish PostgreSQL-only cleanup and verify `make setup`, `make run`, and migrations on a fresh environment.
4. Finalize and execute the US-13 evaluation protocol.
5. Run the four-camera capacity soak and close production readiness dependencies.
6. Implement retention cleanup and automate the proven US-08 browser sequence.
7. Deploy and benchmark the single-worker remote Safety Vision path before adding GPU or worker affinity.
