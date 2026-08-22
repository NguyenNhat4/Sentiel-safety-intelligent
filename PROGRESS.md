# Project Progress

Updated: 2026-08-22

This file is the current project snapshot, not a chronological changelog. Use Git history for completed implementation detail. Entries are grouped by owning area so contributors can load only the context relevant to the next task.

## Current State

### Cross-cutting

- The MVP is a React 19 frontend, FastAPI modular monolith, Vision facade, PostgreSQL persistence, and a separate streamer/MediaMTX media plane.
- The standard contributor workflow remains `make setup` then `make run`; Alembic upgrades are part of that flow.
- Three authenticated roles are supported: `system_admin`, `safety_manager`, and `area_manager`. New and administrator-reset accounts must replace their temporary password.
- The implemented safety flow covers camera mapping, per-camera zones/rules, server-side RTSP inference, Human-in-the-Loop review, immutable decision context, privacy-redacted evidence, event history, and area-scoped follow-up.

### Backend

- Up to four unique persisted camera mappings are supported. Disconnect is idempotent.
- Each connected camera can have revisioned, disjoint four-point zones and persisted rules keyed by `(camera_id, zone_id)`.
- Authenticated `/api/v1/ws/camera-detections` publishes camera-correlated detection metadata for mapped cameras to `system_admin` and `safety_manager`.
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

### Frontend

- Live Monitor is the all-camera HLS view with source-coordinate SVG detection overlays.
- `system_admin` has a separate camera configuration page for selecting a mapped camera, previewing HLS, and editing zones and rules.
- HITL logs retain their own inference frame/context and are opened explicitly by the Safety Officer. Pending counts exclude reviewed logs.
- Area managers have a server-scoped compliance/event workspace and may resolve or mark false alarm only for events in their assigned area.

### Media And Delivery

- FFmpeg publishes one private H.264 RTSP path per simulated camera to pinned MediaMTX `1.20.1`.
- Backend/Vision consumes RTSP at a bounded 2 FPS sample rate. Browsers consume authenticated HLS through the public streamer gateway; MJPEG remains the rollback transport.
- MediaMTX is private. Streamer administration uses Basic Auth; P-047 browser playback uses short-lived Bearer tokens. Secrets remain outside frontend build variables.
- `scripts/deploy_all_production.sh` gates, publishes, redeploys, waits for Railway success, and checks both health endpoints.
- `Dockerfile.ai` and `requirements.ai.txt` package a standalone CPU proof worker with `/ping` and `/v1/infer`; deployment remains a separate rollout step.

## Latest Verification

- `VISION_PROVIDER=local make check` passes after rebasing the remote Vision worker onto `develop2`: Ruff/ESLint/type-check/build pass, frontend `72 passed`, core/streamer `46 passed`, and backend/Vision `210 passed`.
- The standalone `p047-vision:dev` CPU image builds successfully and its live `/ping` smoke returns `safety_vision_v1`; frontend dependency audit reports zero known vulnerabilities after the compatible `nanoid` patch update.
- Production `p047-app` deployment `ffa10050-7657-4bab-8014-a411d044b09a` and streamer deployment `851de566-1c31-492d-8d68-04f234c0b914` reached `SUCCESS`.
- Public authenticated HLS smoke returned non-empty manifests for `xuong1` and `xuong2`; direct authenticated MediaMTX and streamer-gateway playlist checks returned `200`.
- Latest focused evidence: PPE API `20 passed`, per-zone inference `2 passed`, camera/RTSP backend `13 passed`, frontend focused tests `15 passed`, plus TypeScript, ESLint, production build, and focused Ruff checks.
- The available real RTSP proof decoded H.264 1280x720 at 10 FPS and a valid HLS fMP4 segment. This is functional evidence, not a capacity claim.

## Open Gates

- FastAPI lifespan integration and WebSocket integration hang locally during model preload; live RTSP-to-alert evidence remains incomplete.
- Run browser UAT for camera configuration, two-zone save/reload, mixed rule states, overlays, grouped review, Event Detail, and Area Manager follow-up.
- Run a real 200-viewer x four-camera 30-minute soak with CPU, RSS, egress, errors, and first-frame latency before making a capacity claim.
- Complete the PostgreSQL-only runtime migration and validate the full Alembic chain against PostgreSQL.
- Add the retention cleanup scheduler for persisted US-16 metadata/snapshot deadlines.
- Complete US-13 protocol, representative ground truth, calibration/final split, accuracy thresholds, association/tracking evidence, and target-device latency.
- Configure S3 snapshot storage so production application health can become fully ready.
- Configure and exercise the GitHub production environment, first protected release PR, and immutable rollback procedure.
- Deploy one remote Vision worker, verify backend-to-worker health/inference, and benchmark the Railway/RunPod hop before GPU optimization.

## Known Limitations

- Six missing frames, two-second PPE revoke, four intrusion frames, confidence, and NMS values are MVP defaults pending held-out calibration.
- YuNet plus person fallback is fail-closed but still needs representative privacy recall and license/provenance sign-off before pilot use.
- JSONL operational metrics do not support multi-worker deployment; use a centralized sink before scaling backend workers.
- Telegram delivery is disabled until `TELEGRAM_BOT_TOKEN` and recipient chat IDs are configured; provider failure never blocks inference.
- Only three of four required local demo media assets were previously available, and browser DevTools automation is not configured.

## Next Steps

1. Unblock lifespan integration and prove RTSP frame to model, rule, HITL log, and persisted event end to end.
2. Run the two-zone browser UAT and record results.
3. Finish PostgreSQL-only cleanup and verify `make setup`, `make run`, and migrations on a fresh environment.
4. Finalize and execute the US-13 evaluation protocol.
5. Run the four-camera capacity soak and close production readiness dependencies.
6. Implement retention cleanup and automate the proven US-08 browser sequence.
7. Deploy and benchmark the single-worker remote Safety Vision path before adding GPU or worker affinity.
