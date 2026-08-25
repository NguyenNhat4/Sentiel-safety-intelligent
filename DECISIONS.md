# Project Design Decisions

Updated: 2026-08-24

This file contains only decisions that currently constrain implementation. Superseded alternatives are summarized at the end; use Git history when historical rationale is needed. Prefix new decisions with an owning area and merge them into the relevant active section rather than appending duplicate chronology.

## Architecture And Ownership

### [Cross-cutting] Modular monolith with explicit production owners

- `backend`, `frontend`, and `vision` are the only production owners.
- Backend uses the approved layered layout: `api`, `core`, `integrations`, `models`, `schemas`, and `services`.
- Vision emits observations through its public facade; backend owns deterministic safety rules, authorization, event lifecycle, and persistence. Frontend does not decide violations.
- Cross-owner calls use public facades, adapters, or versioned contracts. New top-level boundaries require an explicit architecture decision.
- FastAPI routes, Pydantic schemas, frontend wire types, SQLAlchemy models, Alembic migrations, and focused tests are runtime contract truth.

### [Cross-cutting] Documentation and tracking

- `context-map.md` is the only documentation index. Documents remain standalone.
- Root `PROGRESS.md` and `DECISIONS.md` are the only project trackers; module-level trackers are prohibited.
- `docs/FUTURE_PROJECT_STRUCTURE.md` is the read-only routing and dependency policy.

## Camera, Media, And Rules

### 2026-08-23: [Cross-cutting] Camera disconnect và rule contract

- Camera configuration cho phép `asset_id=null`; UI có nút “Ngắt kết nối nguồn media” ngoài dropdown và vẫn lưu được trạng thái null.
- Zone intrusion là violation bất kể `machine_state`; thiếu PPE chỉ được xét khi máy đang `running` và không phụ thuộc zone.
- `docs/architecture/alert-rule-contract.md` là business contract bắt buộc đọc; không tự ý đổi rule nếu chưa có product approval, decision record và regression tests.

### 2026-08-23: [Backend] One violation alert per person per video session

- A person may remain active, clear, and violate again during one `monitoring_session_id`, but the session emits at most one new alert/review for that person.
- The deduplication key for alert creation is `(monitoring_session_id, track_id)`; occurrence context remains available for rendering and event validation.
- Ending a session clears this alert history, so the same person in a newly started video can produce a new alert.

### 2026-08-23: [Backend] Explicit direct-file simulation runtime

- Backend owns system-admin media uploads, assigns READY assets uniquely to fixed `cam_1` through `cam_4`, and reads validated image/video cache files directly with OpenCV for explicit run/replay sessions.
- Saving camera configuration does not start inference. Sessions never auto-resume after process restart, and the new flow has no streamer, RTSP, HLS, or mapping-supervisor runtime dependency.
- Reviewed events, existing zones/PPE records, and Alembic history remain authoritative; media assets referenced by a configuration or session cannot be deleted.

### 2026-08-23: [Backend/Frontend] Railway Bucket direct media delivery

- New production media uploads use a backend-authorized presigned POST directly from the browser to the Singapore Railway Bucket; credentials never enter frontend code.
- Backend verifies object size/type and decodes the first frame before `READY`. PostgreSQL stores each asset's canonical backend/key; legacy volume rows remain readable until the one-time copy migration completes.
- Playback uses a short-lived presigned GET so video byte ranges bypass the application service. `MEDIA_ASSET_DIR` remains a server-owned OpenCV read-through cache.
- Run starts fresh inference for every valid configured camera. Replay starts only the selected camera and its new session ID resets playback, tracking and overlays.

### 2026-08-24: [Backend/Frontend] Camera-wide PPE and deterministic HITL persistence

- `hat_required` and `vest_required` are persisted on the fixed camera configuration, remain saveable with `zones=[]`, and apply to every qualified person in the frame only while camera-wide machine state is `running`.
- Zone records continue to own `zone_intrusion_enabled` and `restricted_area_detection_enabled`; their embedded PPE fields remain additive compatibility data during migration.
- A grouped HITL popup may contain multiple people, but the browser claims each occurrence ID once, serializes event writes, blocks duplicate submit, and advances the queue only after every valid write succeeds.

### 2026-08-24: [Cross-cutting] Seven-frame HITL debounce

- A violation must be observed in 7 consecutive accepted frames before its first occurrence can set `review_required=true` and open the HITL popup.
- This applies consistently to zone intrusion, restricted-area-compatible generic violations, and missing-PPE alerts; a normal/unknown frame resets the pending consecutive-frame count.
- Vision-side PPE temporal confirmation remains a separate observation-quality gate; it does not bypass the 7-frame HITL debounce.

### 2026-08-23: [Backend/Frontend] Fixed camera configuration and per-zone rules

- Persist exactly four logical slots `cam_1` through `cam_4`; each READY asset may be assigned to at most one slot.
- Live Monitor remains the all-camera operational view. Camera configuration has no sidebar entry and opens only when `safety_manager` selects a Live Monitor slot.
- Zones are revisioned, enabled, disjoint four-point polygons. Rules are persisted by `(camera_id, zone_id)`.
- `hat_required` and `vest_required` are camera-wide per the newer 2026-08-24 decision.
- `zone_intrusion_enabled` is per zone, defaults to `true` for compatibility, ignores machine state, and opens after four consecutive sampled frames in that zone.
- `restricted_area_detection_enabled` is a per-zone configuration switch, defaults OFF, treats any canonical person in the camera as an immediate critical occurrence, and ignores polygon and machine state.
- Backend reads the assigned server-owned cached asset directly and publishes session-correlated source-coordinate metadata for overlays.

## Detection, Tracking, And Privacy

### 2026-08-21: [Vision/Backend] Optional remote Safety Vision worker

- `FrameInferenceService` selects the in-process facade by default or the versioned `safety_vision_v1` HTTP provider when `VISION_PROVIDER=remote`; direct-file sessions use the same rule pipeline.
- The worker owns YOLO11m Safety and session-scoped ByteTrack state only. Backend keeps zone/PPE rules, occurrence lifecycle, HITL, privacy, persistence, and notifications.
- Remote responses are untrusted input: validate contract version, request correlation, payload shape, timeout, and HTTP status; failure is closed and never becomes a fabricated `normal` result.
- The first deployment uses one worker. Multiple workers require affinity or an explicit decision to relocate tracker state.
- Keep the CPU worker image as the rollback artifact. The RunPod image separately pins PyTorch `2.9.1`, torchvision `0.24.1`, and CUDA `12.8`, passes `cuda:0` explicitly to every Ultralytics predict/track call, and fails startup when CUDA is unavailable rather than silently running CPU inference.
- CPU/GPU performance claims use the same CUDA image, checkpoint, input, classes and ByteTrack pipeline on one machine, run sequentially after warm-up, and report mean/P50/P95 plus throughput. Model load, media decode and network latency remain separate measurements.
- The developer comparison UI is a separate, noindex Vite entrypoint. It sends the same browser frame to CPU and GPU concurrently, allows only one comparison cycle in flight, and counts skipped video frames; its RTT is an end-to-end responsiveness diagnostic, not the controlled sequential model-performance claim.
- Independent camera sessions may infer concurrently with one isolated YOLO/ByteTrack instance per session; calls for the same session remain serialized. Terminal sessions release model state while lightweight occurrence context remains available through its TTL for queued human review.

### 2026-08-13: [Vision/Backend] One YOLO11m Safety call per frame

- Pin source revision `95ffeeb1e0897d60564c811ace5935bcd43d982b` and source SHA-256 `f53324f39d76da6017d41038e74f95b3dceb33524738721e03f69f3ea58a1ece`; runtime uses the optimizer-stripped EMA FP16 artifact with SHA-256 `e5b2ad353a33579e821ed9be77ed8406b7bac14bb8abf5d6db77b071ea021218`.
- Run source classes `[0,3,4]` once per sampled frame. Class `3` is canonical `person`; classes `0` and `4` provide `hat` and `vest`.
- Local inference uses separate person/PPE confidence thresholds, `960` image size, anatomical hat/vest association, per-person/class cardinality, and session-local temporal smoothing.
- The public PPE profile is `hat_vest_v1`. Missing PPE is qualified absence derived by backend rules and requires US-13 calibration before non-demo use.
- ByteTrack IDs are monitoring-session-local technical associations, never identity or cross-camera recognition.

### 2026-08-24: [Vision/Backend] Preserve source frames until the YOLO boundary

- Backend direct-camera inference passes each decoded frame at its original resolution to the configured Vision provider; it does not pre-resize to `640x360`.
- Ultralytics owns the only resize/letterbox step, with `YOLO_INFERENCE_IMAGE_SIZE=960` producing the current `960x960` model tensor.
- Detection boxes, foot points, and zone geometry remain in source-frame coordinates without a backend scale-down/restore round trip.
- This favors source detail and PPE recall; four-camera latency and memory must be measured with representative media before production capacity claims.

### 2026-08-16: [Cross-cutting] Occurrence confirmation and reconciliation

- Event occurrences are keyed by monitoring session, track, and rule; database persistence is idempotent by occurrence ID.
- Occurrence ownership used to validate a queued HITL review is the immutable session/track/rule context from the alert frame. A later nearby ByteTrack handoff may move live tracking state but must not invalidate that earlier review payload.
- Local vision confirms initial PPE absence and holds established presence using `PPE_TEMPORAL_FRAMES` (default 10); a locally confirmed absence opens without a second backend debounce. The remote provider, whose v1 contract has no absence-confirmation field, retains six-frame backend confirmation.
- An unreviewed PPE warning retracts only after two continuous seconds of explicit presence; missing or unknown resets that timer.
- Zone intrusion opens after four consecutive sampled frames. Restricted-area detection remains immediate.
- Nearby track-ID handoff may transfer active occurrence state during the lost-track grace window. Distant, different-rule, expired, or cross-session tracks remain independent.
- Submitted `acknowledged` and `false_alarm` outcomes are human-authoritative and cannot be rewritten by later AI observations.
- Restricted-area switches apply to every canonical person in the camera, regardless of polygon membership. An active PPE occurrence closes when the camera-wide machine requirement becomes inapplicable; an unknown PPE observation still does not retract it.

### 2026-08-16: [Vision/Backend] Fail-closed evidence privacy

- Run pinned OpenCV YuNet when persisting reviewed evidence, blur every expanded face, and apply upper-person fallback only for canonical people without an associated face.
- Missing/corrupt detector artifacts fail startup. Per-frame detector error falls back for every person; no valid person candidate fails persistence.
- Redaction occurs in memory before annotation and storage: `redact -> annotate -> persist`. Database failure removes the newly written file.
- Raw video and replayable monitoring sessions are never persisted.

## Events, Users, And Data

### 2026-08-15: [Cross-cutting] Human-authoritative event audit

- One event per `(monitoring_session_id, track_id)` accumulates that person's observed hat, vest, restricted-area, and zone rules.
- Every reviewed event stores immutable `decision_context_v1`: observations, rule version/configuration, debounce, camera/zone/severity, server-owned actor, outcome, and timestamp.
- False alarms remain retrievable for audit and model evaluation but are excluded from official violation statistics. Resolved confirmed events remain official.
- Default retention is 365 days for reviewed metadata and 90 days for blurred snapshots. Persist deadlines separately; cleanup enforcement remains required.
- LLM summaries are optional and advisory. Deterministic text and structured stored context remain authoritative.

### 2026-08-15: [Backend] Area-scoped authorization and notification

- Roles are exactly `system_admin`, `safety_manager`, and `area_manager`; sessions are server-side and stored as token digests.
- Area managers can view and transition only events in their assigned area. New/updated area-manager accounts require a valid managed area.
- Confirmed events route to the assigned manager. Telegram delivery uses numeric chat IDs, is non-blocking, and never changes inference or in-app persistence on provider failure.
- New and administrator-reset accounts must replace temporary passwords; forgotten-password recovery returns to System Admin.

### 2026-08-20: [Backend] PostgreSQL-only database contract

- PostgreSQL is the only supported relational database for local development, tests, and deployment. SQLite and automatic fallback are deprecated and must be removed.
- `DATABASE_URL` must be reachable from the running environment. Railway private DNS is valid only inside its Railway project/environment.
- `make setup` and `make run` apply reviewed Alembic migrations. Startup must fail clearly rather than write to an unsynchronized fallback.
- PostgreSQL uses a bounded LIFO pool, TCP keepalive, connection recycling, and optional pre-ping.

### 2026-08-11: [Backend] Lightweight operational metrics

- Persist a finite privacy-safe schema to rotated JSONL and expose bounded aggregates. Do not include frames, snapshots, identifiers, raw paths, addresses, credentials, or exception text.
- The current implementation supports one writer process. Multi-worker deployment requires a centralized sink.

## Delivery

### 2026-08-16: [Cross-cutting] CI-gated Railway release

- Protected `main` accepts pull requests only. CI runs locked Python 3.11, frontend, backend, vision, and Docker gates before publishing the production image and redeploying Railway.
- Railway variables own runtime secrets and provider configuration; credentials never enter source or frontend build variables.
- Release success requires terminal Railway deployment success and readiness evidence. Rollback uses a known-good immutable deployment/image reference.
- Team onboarding must remain operable with only `make setup` and `make run`.

## Superseded Summary

- SQLite default, dual-database support, and PostgreSQL-with-SQLite-fallback are superseded by PostgreSQL-only.
- Browser-local upload, one active camera and browser-driven production inference are superseded by backend-owned media assets and explicit fixed-camera sessions.
- Streamer, MediaMTX, HLS/RTSP simulation, stream mappings, Connect/Disconnect, and automatic mapping reconciliation are superseded by backend-owned direct-file media sessions.
- HSV/SH17 and YOLO11n runtime paths, helmet/glasses/gloves contracts, and three-PPE rules are superseded by the single YOLO11m `hat_vest_v1` contract.
- Build-free JavaScript and Vanilla frontend baselines are superseded by React 19, TypeScript, and Vite.
- Capability-owned backend submodules and separate prose contract trees are superseded by the approved layered backend and executable contract definitions.
- Immediate zone intrusion and time-based initial PPE confirmation are superseded by four-frame intrusion and six-frame missing-PPE confirmation.
