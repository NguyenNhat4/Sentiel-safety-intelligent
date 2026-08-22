# Project Design Decisions

Updated: 2026-08-22

This file contains only decisions that currently constrain implementation. Superseded alternatives are summarized at the end; use Git history when historical rationale is needed. Prefix new decisions with an owning area and merge them into the relevant active section rather than appending duplicate chronology.

## Architecture And Ownership

### [Cross-cutting] Modular monolith with explicit production owners

- `backend`, `frontend`, and `vision` are the production owners. Streamer owns media transport only.
- Backend uses the approved layered layout: `api`, `core`, `integrations`, `models`, `schemas`, and `services`.
- Vision emits observations through its public facade; backend owns deterministic safety rules, authorization, event lifecycle, and persistence. Frontend does not decide violations.
- Cross-owner calls use public facades, adapters, or versioned contracts. New top-level boundaries require an explicit architecture decision.
- FastAPI routes, Pydantic schemas, frontend wire types, SQLAlchemy models, Alembic migrations, and focused tests are runtime contract truth.

### [Cross-cutting] Documentation and tracking

- `context-map.md` is the only documentation index. Documents remain standalone.
- Root `PROGRESS.md` and `DECISIONS.md` are the only project trackers; module-level trackers are prohibited.
- `docs/FUTURE_PROJECT_STRUCTURE.md` is the read-only routing and dependency policy.

## Camera, Media, And Rules

### 2026-08-21: [Cross-cutting] RTSP-first private media plane

- FFmpeg publishes one H.264 RTSP path per simulated camera to exact-version-pinned MediaMTX. Backend/Vision reads RTSP; browsers use HLS.
- MediaMTX remains private and separate from the streamer service. FastAPI is the control plane and does not proxy media bytes.
- Public HLS passes through the streamer gateway. Streamer administration uses separate Basic Auth credentials; browser playback uses short-lived HMAC Bearer tokens available only to `system_admin` and `safety_manager`.
- Valid-role HLS tokens may authorize all valid camera IDs with `cameras: ["*"]`; streamer still validates signature, expiry, role, authentication, and camera ID.
- MJPEG remains the explicit rollback transport. WebRTC/WHEP and removal of MJPEG require separate measured decisions.
- No production capacity claim is allowed without a real 200-viewer x four-camera soak report.

### 2026-08-21: [Backend/Frontend] Persist camera mappings and per-camera zone rules

- Persist up to four unique `stream_camera_id` to named `camera_id` mappings. Disconnect is idempotent.
- Live Monitor remains the all-camera operational view. `system_admin` configures one mapped camera at a time on a separate page.
- Zones are revisioned, enabled, disjoint four-point polygons. Rules are persisted by `(camera_id, zone_id)`.
- `hat_required` and `vest_required` apply to a person whose foot point is inside the zone and only while camera-wide machine state is `running`.
- `zone_intrusion_enabled` is per zone, defaults to `true` for compatibility, ignores machine state, and opens after four consecutive sampled frames in that zone.
- `restricted_area_detection_enabled` is a per-zone configuration switch, defaults OFF, treats any canonical person in the camera as an immediate critical occurrence, and ignores polygon and machine state.
- HLS is display-only. Backend reads mapped RTSP and publishes camera-correlated source-coordinate metadata for overlays.

## Detection, Tracking, And Privacy

### 2026-08-21: [Vision/Backend] Optional remote Safety Vision worker

- `FrameInferenceService` selects the in-process facade by default or the versioned `safety_vision_v1` HTTP provider when `VISION_PROVIDER=remote`; browser and server-side RTSP inference contracts remain unchanged.
- The worker owns YOLO11m Safety and session-scoped ByteTrack state only. Backend keeps zone/PPE rules, occurrence lifecycle, HITL, privacy, persistence, and notifications.
- Remote responses are untrusted input: validate contract version, request correlation, payload shape, timeout, and HTTP status; failure is closed and never becomes a fabricated `normal` result.
- The first deployment uses one worker. Multiple workers require affinity or an explicit decision to relocate tracker state.
- Keep the CPU worker image as the rollback artifact. The RunPod image separately pins PyTorch `2.9.1`, torchvision `0.24.1`, and CUDA `12.8`, passes `cuda:0` explicitly to every Ultralytics predict/track call, and fails startup when CUDA is unavailable rather than silently running CPU inference.
- CPU/GPU performance claims use the same CUDA image, checkpoint, input, classes and ByteTrack pipeline on one machine, run sequentially after warm-up, and report mean/P50/P95 plus throughput. Model load, media decode and network latency remain separate measurements.
- The developer comparison UI is a separate, noindex Vite entrypoint. It sends the same browser frame to CPU and GPU concurrently, allows only one comparison cycle in flight, and counts skipped video frames; its RTT is an end-to-end responsiveness diagnostic, not the controlled sequential model-performance claim.

### 2026-08-13: [Vision/Backend] One YOLO11m Safety call per frame

- Pin `models/yolo11m_safety.pt` at upstream revision `95ffeeb1e0897d60564c811ace5935bcd43d982b`, SHA-256 `f53324f39d76da6017d41038e74f95b3dceb33524738721e03f69f3ea58a1ece`.
- Run source classes `[0,3,4]` once per sampled frame. Class `3` is canonical `person`; classes `0` and `4` provide `hat` and `vest`.
- The public PPE profile is `hat_vest_v1`. Missing PPE is qualified absence derived by backend rules and requires US-13 calibration before non-demo use.
- ByteTrack IDs are monitoring-session-local technical associations, never identity or cross-camera recognition.

### 2026-08-16: [Cross-cutting] Occurrence confirmation and reconciliation

- Event occurrences are keyed by monitoring session, track, and rule; database persistence is idempotent by occurrence ID.
- Missing hat/vest opens after six consecutive missing sampled frames for the same track/item. Present or unknown breaks an unconfirmed sequence.
- An unreviewed PPE warning retracts only after two continuous seconds of explicit presence; missing or unknown resets that timer. Six new missing frames are required to reopen it.
- Zone intrusion opens after four consecutive sampled frames. Restricted-area detection remains immediate.
- Nearby track-ID handoff may transfer active occurrence state during the lost-track grace window. Distant, different-rule, expired, or cross-session tracks remain independent.
- Submitted `acknowledged` and `false_alarm` outcomes are human-authoritative and cannot be rewritten by later AI observations.

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
- Browser-local upload, one active camera, browser-driven production inference, and standalone MJPEG-only playback are superseded by persisted multi-camera RTSP inference with authenticated HLS.
- HSV/SH17 and YOLO11n runtime paths, helmet/glasses/gloves contracts, and three-PPE rules are superseded by the single YOLO11m `hat_vest_v1` contract.
- Build-free JavaScript and Vanilla frontend baselines are superseded by React 19, TypeScript, and Vite.
- Capability-owned backend submodules and separate prose contract trees are superseded by the approved layered backend and executable contract definitions.
- Immediate zone intrusion and time-based initial PPE confirmation are superseded by four-frame intrusion and six-frame missing-PPE confirmation.
