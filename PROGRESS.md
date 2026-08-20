# Project Progress

## 2026-08-19: [Cross-cutting] Restore US-16 audit onto current develop2
- Restored the preserved US-16 work and synchronized the feature branch onto `origin/develop2` at `28daa62`, retaining current RBAC, area resolution, notification, per-track aggregation, camera-stream, and privacy behavior; the audit migration is linear revision `20260819_01` after `20260815_03`.
- Added immutable `decision_context_v1`, Event Detail, false-alarm audit, server-owned review actor and retention deadlines; resolved events remain in official statistics while false alarms do not.
- Fixed Alembic logging reconfiguration so migration tests cannot disable the operational JSONL writer for later tests. Full verification is recorded in the US-16 implementation plan.

## 2026-08-18: [Cross-cutting] Add standalone mock camera streamer
- Added the independent `streamer` service on port 8001 with per-camera video upload, persistent local media, looped FFmpeg MJPEG output, camera listing, health endpoint, and a browser upload/test page.
- Added a Docker image that includes FFmpeg, Compose wiring, and the standard `make run` workflow now starts both the streamer and backend. Backend inference integration, RTSP, and HLS remain intentionally deferred until manual MJPEG validation.
- Focused streamer tests and the full `make check` pass. The current development host does not have the `ffmpeg` binary installed, so local playback requires installing FFmpeg or using the Docker service.
- Added real-time FFmpeg input pacing and low-buffer output flags after initial manual testing exposed browser backlog/latency.
- Added camera tabs to the standalone streamer UI so one selected camera is displayed at a time instead of rendering every stream simultaneously.
- Fixed MJPEG startup on the current FFmpeg image by removing the incompatible `low_delay` encoder flag; force-recreated Compose and verified `/stream/cam_1` emits frames.
- Added `DELETE /api/cameras/{camera_id}` and a per-tab **Xóa** action that removes the uploaded video and resets the viewer when no cameras remain.

## 2026-08-19: [Cross-cutting] Add admin-selected active camera stream
- Added `stream_configuration` persistence, `GET/PUT /api/v1/stream-config`, and system-admin-only update authorization for one shared active camera.
- Added the admin **Camera stream** sidebar entry, streamer-container camera discovery, enable/disable controls, and Live Monitor MJPEG empty/error/active states.
- Removed local video upload controls from the app. MJPEG-to-AI inference remains intentionally deferred.
- Added the use-case plan with Mermaid use-case, sequence, and state diagrams at `docs/plans/2026-08-19-001-feat-admin-camera-stream-selection-plan.md`.
- Focused backend tests and all frontend tests/lint/type-check/build pass; the full `make check` baseline is green.

## 2026-08-19: [Frontend] Add demo account shortcuts to login
- Added visible local demo accounts for `admin`, `antoan`, and `khuvuc` with the shared `Sentinel123!` password.
- Added one-click account filling and copy-email actions without changing authentication contracts.

## 2026-08-19: [Frontend] Move camera stream to sidebar navigation
- Moved **Camera stream** out of the account tabs into a dedicated System Admin sidebar entry directly below **Quản trị hệ thống**.
- Changed the active camera card action from disabled **Đang phát** to an explicit **Tắt stream** action; clearing active state is verified through the backend API.

## 2026-08-20: [Cross-cutting] Add streamer Docker Hub publish script
- Added `scripts/push_streamer.sh` to build and push the standalone streamer image with a configurable Docker Hub image name and tag.
- The script defaults to `nguyennaht4/streamer:dev`, uses existing `docker login` credentials, and never handles credentials directly.

## 2026-08-20: [Cross-cutting] Clarify separate streamer deployment
- Documented Compose as local-only and production streamer as a separate service.
- Added `VITE_STREAMER_URL` Docker build injection and CI variable `STREAMER_PUBLIC_URL` for the production frontend.

## 2026-08-16: [Vision/Backend] Add YuNet-first identity redaction
- Added the pinned OpenCV YuNet detector, startup artifact/capability validation, cached thread-safe inference, expanded face blur, and the existing upper-person fallback for each person without an associated face.
- Snapshot persistence remains fail-closed: all detected faces are redacted, detector errors fall back for every person with a stable operational warning, no-person frames fail, and database failures still remove the already-redacted file.
- Added focused Vision/backend/startup coverage and a reusable privacy latency benchmark. On the official 512×512 OpenCV sample, 20 CPU iterations detected one face with no fallback at 14.583 ms mean and 19.479 ms p95.

## 2026-08-16: [Cross-cutting] Add CI-gated Railway release workflow
- [x] Standardized the Python project lock and local interpreter pin on Python 3.11, matching Docker and the supported test runtime.
- [x] Replaced the legacy requirements-based CI with parallel locked uv, frontend and scoped Docker checks for PRs and pushes on `main`; added a non-blocking nightly dependency audit.
- [x] Added a Docker Hub `:latest` publication after successful `main` CI, followed by Railway CLI redeploy and `/health` readiness polling.
- [x] Added `docs/CI_CD.md` so a new contributor can configure repository secrets, Railway Docker-image deployment, production variables and migrations, branch protection, release, rollback and incident triage.

## 2026-08-16: [Documentation] Add component and runtime data-flow diagrams
- [x] Added `docs/architecture_diagram.md` with Mermaid component and runtime data-flow diagrams; the root architecture document remains the canonical boundary and invariant reference.
- [x] Replaced the nested sequence diagram with a render-compatible flowchart covering WebSocket backpressure, four-frame debounce, redaction-first snapshot handling and fail-closed persistence.

## 2026-08-16: [Cross-cutting] Human-authoritative PPE log reconciliation
- A missing-PPE log is reviewable after six consecutive missing frames and opens its modal only when the Safety Officer clicks it.
- The review modal now displays the selected log's saved title/detail instead of the latest live-frame status.
- AI updates remain isolated per monitoring-session TrackID and per PPE item. Before a log exists, one explicit present observation resets its pending missing sequence. After a log exists, explicit presence must continue for two seconds before retracting only that item's warning; `missing` or `unknown` resets the revoke timer. Six new consecutive missing frames are required to create another warning. Submitted `acknowledged`/`false_alarm` outcomes remain authoritative.
- Merged the latest `origin/develop2` while preserving its CI/Railway and YuNet privacy changes; reapplied only the branch-owned tracking, HITL, migration compatibility, and PostgreSQL environment behavior removed by the upstream revert.
- Full equivalent checks pass after merge resolution and the two-second PPE revocation update: 20 root tests, 159 backend/vision tests, 53 frontend tests, lint, type-check, formatting, and production build.

## 2026-08-16: [Cross-cutting] Zone-intrusion debounce restored
- A person must remain inside the same active danger zone for four consecutive sampled frames before the backend opens a `zone_intrusion` occurrence.
- Whole-camera restricted-area alerts remain immediate; missing PPE requires six consecutive sampled frames.

## 2026-08-15: [Cross-cutting] One accumulated event per tracked person
- Human-in-the-Loop review now isolates the selected tracked person and saves one `person_safety_violation` event containing every observed hat, vest, restricted-area, and zone rule.
- Later violations for the same `(monitoring_session_id, track_id)` merge into the existing event. Added a portable Alembic uniqueness constraint and focused backend/frontend coverage.

## 2026-08-15: [Cross-cutting] Area log details and resolution workflow
- Area managers now see individual logs only for their assigned area, can open a log to inspect its snapshot/context, and can mark it **Đã giải quyết** or **Không phải vi phạm**.
- Backend authorization rejects updates to another area's event. Focused event tests, frontend lint, type-check, and production build pass.

## 2026-08-15: [Cross-cutting] Confirmed violations now reach the correct area manager
- AI detections no longer notify area managers before Human-in-the-Loop review. A confirmed `acknowledged` event now routes to the manager assigned to its `zone_id`.
- Area-manager event history and summary statistics are server-filtered to the assigned area; focused backend routing tests and frontend checks pass.

## 2026-08-14: [Frontend] Human-in-the-Loop review no longer pauses live streaming
- The monitor keeps streaming after a violation, surfaces compact critical/PPE counts above the video, and records the candidate in the Human-in-the-Loop log.
- Safety officers open the snapshot and review/escalation choices only by selecting a log entry.

## 2026-08-14: [Frontend] PPE configuration follows the selected area
- The PPE requirement controls now load and save against the selected `zone_id`, matching the inference request for that area instead of always editing `zone_01`.

## 2026-08-14: [Frontend] Human-in-the-Loop records individual PPE warnings
- Missing required hats and vests now create separate deduplicated Human-in-the-Loop warning entries per detected person and PPE item; zone intrusion entries remain critical.
- The monitor's rule summary is compact so the right panel has room for the recent warning log.

## 2026-08-15: [Cross-cutting] Repair fresh local SQLite setup
- Development environment defaults now use local SQLite and filesystem snapshots, so `make setup` followed by `make run` does not require or contact production PostgreSQL/S3 resources.
- Legacy SQLite adoption validates the exact known pre-Alembic schema and mutates only revision-owned state; it no longer creates future auth/zone tables from current ORM metadata before Alembic runs.
- Added regression coverage proving a bootstrapped legacy database upgrades cleanly through the current Alembic head.

## 2026-08-15: [Cross-cutting] Complete US-16 immutable event decision audit
- Added additive `decision_context_v1` persistence with server-owned rule version, debounce, camera/zone/severity, authenticated HITL actor, and separate metadata/snapshot retention deadlines.
- Event Detail now retrieves and displays the structured AI observation → rule decision → human review chain plus a source-labelled deterministic/optional-LLM summary; legacy events remain readable as limited audits.
- Confirmed violations and false alarms are separate audit filters for Safety Officer and Area Manager views. False alarms remain retrievable but are excluded from all official violation statistics.
- Added reversible Alembic migration and focused backend/frontend coverage for immutability, actor trust, retention, legacy compatibility, summary fallback, false-alarm metrics, API auth headers, context capture and audit UI.

## 2026-08-13: [Frontend] Human-in-the-Loop alert tones clarify safety response
- The Human-in-the-Loop panel now prioritizes red for a person in a forbidden zone, orange for missing configured PPE, yellow for required PPE that cannot be determined, and green/no-alert messaging when detected people have all required PPE.
- Added focused UI-state coverage for the alert priority; frontend type-check, lint, tests, and production build pass.

## 2026-08-13: [Frontend] Video upload is scoped to the selected monitoring area
- Browser-local video uploads are now retained by selected `zone_id`; selecting another area shows only that area's video or an empty state.
- Live inference uses the selected area's polygon and machine state through the compatible single-zone WebSocket configuration, rather than evaluating the selected video's frames against every saved area.

## 2026-08-13: [Backend] Analysis PPE requirement loading uses the request database session
- Frame inference REST and WebSocket paths now load the active PPE profile through their injected SQLAlchemy session, so test database overrides and runtime database selection are respected.
- Added Alembic's OS-aware `path_separator` setting to remove the deprecated legacy path parsing warning.

This is the single progress tracker for the repository. Completed work is grouped by area; current state, known issues, and next steps are project-wide.

## 2026-08-15: [Cross-cutting] Per-zone restricted-area detection
- Added the **Vùng cấm** switch beside the selected zone's mũ/áo configuration; its value persists per `camera_id` + `zone_id` and defaults OFF.
- When enabled, any detected person anywhere in the camera frame creates an immediate critical, red Human-in-the-Loop log, independent of polygon and machine state. Existing hat/vest and polygon intrusion behavior remains unchanged.
- Added Alembic revision `20260815_02_add_restricted_area_detection.py`; focused backend and frontend tests pass.

## Current State
- Runtime frame inference now uses only `models/yolo11m_safety.pt`: one `[0,3,4]` predict/track call supplies canonical people, ByteTrack IDs, hat and vest; YOLO11n is no longer loaded or called.
- Area managers now land on a dedicated compliance/event workspace; system administrators retain the complete safety-officer monitor/log experience and receive the additional account-management navigation.
- New and administrator-reset accounts must replace their temporary password after login; normal self-service password changes are disabled and forgotten-password recovery returns to System Admin.
- The current MVP and two-command developer workflow default to SQLite. PostgreSQL remains supported through an explicit `DATABASE_URL`; runtime fallback and `/health` backend reporting from `develop2` are preserved.
- Authentication now exposes exactly system admin, safety officer, and area manager; the legacy simulation-operator role and demo account are removed.
- System administrators have a tabbed account-management workspace in the existing one-column sidebar layout, backed by RBAC-protected create/delete/role/password APIs.
- The persisted `system_admin` identity is supported consistently by backend authentication and frontend wire types.
- Authentication now starts successfully, persists hashed server sessions, and the browser uses the real login/me/logout API with a tab-scoped token.
- The baseline upload → four-point zone → binary WebSocket inference → foot-point zone review → event save flow is implemented.
- FastAPI serves the React production build at `/` and provides REST plus WebSocket APIs.
- Frontend uses React 19, TypeScript, Vite, typed feature boundaries, and a tested transport layer.
- Python static checks, full root/backend/vision tests, frontend lint/type-check/unit/component tests, and production build pass through `make check` on Python 3.11.
- US-28 is implemented with pinned `yolo11m_safety.pt`, exact source-mapping validation, one-call-per-frame class filter `[0,3,4]`, and public `hat_vest_v1` observations for the fixed `uploaded_video` / `zone_01` pair.
- Backend US-07 follows the approved flat layered layout (`api`, `models`, `schemas`, `services`, `integrations`); the temporary `backend/app/modules` tree has been removed.
- Inference `rule` now echoes `ppe_profile=hat_vest_v1` plus persisted `hat_required`/`vest_required` values in REST and WebSocket responses.
- Required PPE state is rendered on each detected-person box: present is green, qualified absence is red `missing`, and unknown is labeled neutrally.
- Removed legacy safety-shirt/helmet/glasses/gloves capability from the current contract and UI; the operator now sees only saved hat/vest requirement state.
- Moved the canonical US-07 implementation specification to `specs/done/US-07-SPEC.md` and documented the returned rule context plus person-box PPE badges.
- US-13 now specifies a project-owned custom dataset as its primary acceptance source, with scenario coverage, versioned ground truth, calibration/final isolation and reproducible metric/latency evidence.
- Snapshot privacy is now independent from PPE: the fail-closed adapter redacts the upper 40% of every canonical person box in memory before hat/vest annotation and persistence.
- ReviewModal now captures the full native video frame after it pauses at the violating inference timestamp, overlays canonical person and hat/vest boxes with matching aspect ratio, and persistence retains the same order `redact → annotate → persist`.
- Completed US-08 tracking/dedup with session-scoped track IDs, occurrence lifecycle, reconnect semantics, spatial track handoff, and database-enforced event idempotency.
- US-08 core implementation now provides session-isolated ByteTrack IDs, deterministic rule occurrences, stale-frame/session guards, additive REST/WebSocket fields, and database-enforced reviewed-event idempotency.
- Validated US-08 with a local-only synthetic 24-second multi-person video covering continuous presence, distinct concurrent tracks, exit/cooldown, and re-entry; test media is intentionally excluded from Git.
- US-27 is implemented for multiple disjoint four-point danger zones on one video, per-zone simulated machine state, revisioned persistence, zone-scoped dedup, additive inference contracts and atomic grouped-review persistence. PPE remains the unchanged whole-frame `uploaded_video/zone_01` configuration.
- The US-27 feature branch is merged with `origin/develop2` at `9c0141c`; auth, operational metrics and multi-zone routes coexist, and Alembic now advances linearly through auth `20260811_01`, forced-password `20260811_02` and monitoring-zones `20260811_03`.
- Backend now persists lightweight operational request, inference, and WebSocket outcome metrics to rotated JSONL and exposes bounded aggregates at `GET /api/v1/operational-metrics`.
- `make setup` and `make run` now run versioned Alembic upgrades, so a new SQLite database is created at the current schema automatically.
- Single-checkpoint two-command smoke passed: `make setup` completed, `make run` preloaded YOLO11m Safety, and `/health` returned `200` with SQLite selected.
- A separate read-only “Quan sát hệ thống” page now displays JSONL operational request, latency, inference, and error aggregates.

## Completed

### Backend
- [x] [Cross-cutting] Completed US-28 prototype cutover: versioned `hat_vest_v1` REST/WebSocket/Pydantic/TypeScript contracts, deterministic `missing_ppe:hat|vest` rules, and retirement of legacy glasses/gloves/shirt fields.
- [x] [Backend] Added Alembic revision `20260813_01`, mapping legacy helmet configuration to hat, defaulting vest OFF, preserving legacy columns and historical event/occurrence audit, with migration regression coverage.
- [x] [Backend] Split PPE inference and fail-closed privacy into separate integration adapters so SH17 is no longer a runtime privacy dependency.
- [x] [Backend] Fixed grouped-review occurrence lookup on PostgreSQL by replacing row-wide `DISTINCT` over JSON event details with an `EXISTS` relationship filter; database lookup failures now return a typed `503 Service Unavailable`, with focused regression coverage and local pool pre-ping enabled.
- [x] Optimized remote PostgreSQL CRUD latency with reusable LIFO pooling, optional pre-ping, TCP keepalive, connection recycling, non-expiring committed ORM state, and removal of redundant post-commit refresh queries.
- [x] Added system-admin-only user listing, creation, deletion, role assignment, and password reset with self-removal/last-admin safeguards and session revocation.
- [x] Restored auth router and startup wiring, and added an Alembic authentication schema revision after the current PPE revision.
- [x] Added database-backed authentication endpoints for login, current-session lookup, and logout, with seeded development users and persisted token digests.
- [x] Established the FastAPI modular monolith, typed settings, SQLAlchemy database layer, REST APIs, and test scaffolding.
- [x] Added safety-event lifecycle, reviewed snapshot persistence, statistics, and Safety Agent endpoints.
- [x] Added YOLO person detection, foot-point polygon evaluation, safety-shirt baseline rule, and REST frame inference.
- [x] Added binary WebSocket inference with configuration, correlation metadata, one-frame processing, validation, and structured errors.
- [x] Documented frontend/backend interaction and the recommended confirmed-warning persistence lifecycle.
- [x] Added rules-owned PPE requirement persistence, strict GET/PUT contracts, migration, rollback behavior, and the ON/OFF missing-PPE truth table.
- [x] Refactored PPE configuration from capability submodules into the flat backend layers while preserving runtime contracts.
- [x] Added the US-12 event privacy gate: raw snapshots are decoded only in memory, redacted before write, rejected on no candidate or processing failure, and cleaned up if the database transaction fails.
- [x] Added transient reviewed-frame box metadata and a post-redaction snapshot annotator, so persisted JPEG evidence contains person and SH17 boxes without allowing annotations to affect privacy or rule decisions.
- [x] Added session-scoped occurrence lifecycle, WebSocket stale-frame/session guards, and idempotent reviewed-event persistence keyed by occurrence IDs.
- [x] [Backend] Added revisioned monitoring-zone collection persistence and GET/PUT APIs, atomic geometry validation, saved-revision checks for REST/WebSocket inference, per-person memberships, per-zone results and zone-scoped occurrence keys.
- [x] [Backend] Added atomic grouped-review event batches with one zone-specific event per candidate, one shared redacted snapshot, occurrence/session/zone validation, database retry idempotency and rollback cleanup.
- [x] Added privacy-safe rotating JSONL operational metrics, bounded aggregate API, HTTP/WebSocket instrumentation, and focused tests without external monitoring services.
- [x] Added the idempotent `make db-upgrade` target to the standard setup/run flow; verified a new SQLite database reaches the current Alembic revision.

### Vision
- [x] [Vision] Consolidated canonical person detection, ByteTrack and hat/vest observation into one YOLO11m Safety call per frame; retired YOLO11n from runtime configuration and preload without changing REST/WebSocket semantics.
- [x] Pinned `wesjos/Yolo-hard-hat-safety-vest/yolo11m_safety.pt` at revision `95ffeeb1e0897d60564c811ace5935bcd43d982b`, SHA-256 `f53324f39d76da6017d41038e74f95b3dceb33524738721e03f69f3ea58a1ece`, under Git LFS.
- [x] Added full five-source-class startup validation, selected only `hat/person/vest`, promoted Safety class `3` to canonical person, and verified a real-model CPU inference smoke run.
- [x] [Historical baseline] Recorded the superseded YOLO11n + YOLO11m Safety pipeline at P50 472.20 ms and P95 504.02 ms; the benchmark script now measures the single-model runtime.
- [x] Moved root `.pt` model files (`ppe_yolov8n.pt`, `yolo11n.pt`) to dedicated `models/` directory, added `models/README.md`, updated `docs/PROJECT_STRUCTURE.md`, and updated backend configuration and service model resolution.
- [x] [Historical baseline, superseded] Separated YOLO11 person detection from the retired SH17 PPE checkpoint before the later single-YOLO11m Safety cutover.
- [x] Added SH17 identity redaction for face/head classes with a conservative 40%-of-person-head fallback and pure-CV synthetic-image tests.
- [x] Added pure-CV post-redaction JPEG annotation for reviewed person and SH17 bounding boxes, preserving the input frame and skipping duplicate SH17 `person` boxes.
- [x] Added `scripts/benchmark_model.py` to measure YOLO latency (mean/P50/P95/P99) and inference throughput using `data/test.mp4` by default, including the current unified person+PPE runtime mode.
- [x] Added `eval/results/model-benchmark-report.md` with the historical combined two-model benchmark result and measurement boundaries.
- [x] Integrated session-isolated ByteTrack state and TTL cleanup into the unified YOLO11m Safety facade.

### Frontend
- [x] Replaced PPE controls, typed payloads, rule summaries, Canvas/list/review overlays and component tests with the two-item `hat_vest_v1` profile.
- [x] Curated browser-facing SH17 detection displays to people plus canonical `helmet`, `glasses`, `gloves`, and `safety-vest` classes across the live Canvas, grouped alert list, and review overlay, while preserving the complete inference and review-metadata payload.
- [x] [Frontend] Added confirmed monitoring-zone deletion that removes the zone immediately from the list/canvas draft, selects and reorders remaining zones safely, and persists the reduced collection only through the explicit save action.
- [x] Added WebSocket route connection counts for inference and alert channels to the separate operational-observability view.
- [x] Added a separate operational-observability page with selectable window, refresh, aggregate KPIs, latency table, inference outcomes, errors, and loading/error/partial-data states.
- [x] Added the system-admin sidebar entry and account, role/permission, and security tabs using the real authentication API.
- [x] Removed the browser-only streaming simulation page, its login card, sidebar navigation, styles, and tests.
- [x] Replaced the temporary authentication mock with typed login/session-restore/logout transport and focused token lifecycle tests.
- [x] Added role-aware login/logout entry points backed by persisted server sessions.
- [x] Added local video playback, normalized four-point zone editing, Canvas overlays, and foot-point visualization.
- [x] Added 2 FPS WebSocket inference with one frame in flight and same-origin/port-8000 fallback.
- [x] Pause playback only when a returned person foot point is inside the configured polygon while the machine is running.
- [x] Added actual-violation and false-alarm review actions with REST event persistence.
- [x] After acknowledged save, close the review state and keep the monitor visible; load confirmed snapshots when the operator opens “Nhật ký vi phạm”.
- [x] Added development localhost CORS support for frontend/backend ports.
- [x] Use local SQLite for baseline event persistence and clean up snapshots when a database transaction fails.
- [x] Refactored the 686-line `app.js` into build-free ES modules with a 29-line composition root.
- [x] Restored Play-button activation immediately after video metadata loads.
- [x] Refactored the validated Sentinel flow from Vanilla ES modules to React 19 + TypeScript + Vite.
- [x] Added typed REST/WebSocket contracts, transport backpressure tests, Canvas tests, and React component tests.
- [x] Integrated the Vite production build with FastAPI and the single-service multi-stage Docker image.
- [x] Added accessible helmet/glasses/gloves requirement switches with backend hydration, explicit save, retry states, and no `localStorage` dependency.
- [x] Added Person-grouped object detection list to `AlertPanel` with class-matched bounding box colors, and implemented centered `ReviewModal` pop-up dialog with 70% screen 16:9 snapshot container for Human-in-the-Loop review.
- [x] Fixed WebSocket client configuration timeout when starting video playback without 4 zone points.
- [x] Resolved potential `IndexError` in `FrameInferenceService` when `observations` length is smaller than `detected_people`, and optimized detection loop in `PpeVisionFacade`.
- [x] Added `SnapshotOverlay` SVG boxes to the Human-in-the-Loop popup, captured the full video frame after seeking to the detected violation timestamp, and forwarded its typed frame metadata solely for persisted-snapshot annotation.
- [x] Kept one monitoring-session UUID and monotonic frame sequence across review/reconnect, rendered track IDs, and persisted only newly opened occurrence IDs.
- [x] Fixed review resume to preserve the monotonic frame sequence, then passed the synthetic-video browser flow with two distinct occurrences in one monitoring session and no duplicate pause during continuous presence.
- [x] Added spatial track-ID handoff within the lost-track grace window so a nearby ByteTrack ID switch while a person exits preserves the reviewed occurrence instead of opening a duplicate popup; distant people remain independent.
- [x] [Frontend] Added the explicit **Tạo vùng** entrypoint, four-click draft workflow, cancel/reset, revisioned backend hydration/save, per-zone name/enabled/machine controls and multi-polygon Canvas overlays.
- [x] [Frontend] Switched the monitor to saved multi-zone WebSocket configuration and grouped review payloads while retaining the legacy event path for non-zone/PPE review behavior.

### Documentation
- [x] Closed US-28 into `specs/done`, documented the pinned artifact/runtime/license/checksum, synchronized architecture/current structure, and migrated US-13 templates from helmet/glasses/gloves to hat/vest.
- [x] Added an operational-metrics guide covering JSONL events, privacy boundary, API/UI, retention, local operation, and single-process limits.
- [x] [Vision] Added the US-13 Task 2 guide for consented custom recording, ground-truth annotation, cross-review, manifest/checksum generation, and locked calibration/final splits.
- [x] [Vision] Added ready-to-use US-13 shooting-sheet, ground-truth and manifest templates plus a deterministic manifest validator with focused tests.
- [x] [Frontend] Stabilized the login layout, reserved error-message space, and changed the three role cards into non-interactive descriptions.
- [x] Documented current/future project structure, WebSocket contracts, runtime diagrams, and review persistence recommendations.
- [x] Consolidated module tracking into central root `DECISIONS.md` and `PROGRESS.md` files.
- [x] Added new-developer setup, API documentation, testing, and manual smoke-test instructions to the root README.
- [x] Clarified the WebSocket inference input sequence, output fields, decision rule, and common outcomes in the backend README.
- [x] Added a PRD-aligned user story backlog separating completed, partial, and remaining MVP work with acceptance criteria.
- [x] Created detailed spec files for completed user stories (US-01 to US-06) covering what, why, how, diagrams, and API contracts.
- [x] Created `specs/backlog/` with synchronized story files for incomplete and partially completed stories from US-07 to US-26.
- [x] Realigned US-07–US-26 with the problem statement: expanded PPE to helmet/glasses/gloves, moved authentication and image analysis into MVP, corrected deployment dependencies, and synchronized the five-week plan and backlog specs.
- [x] Separated MVP closure in the current week from the subsequent five-week advanced delivery plan, with acceptance criteria, implementation tasks, dependencies, milestones, and release gates.
- [x] Integrated `uv` environment management with `make setup` (`uv sync` + `npm ci` + `.env`), created technical setup guide `docs/guide/setup/uv-setup.md`, and updated root `README.md` onboarding.
- [x] Finalized the capability-owned future repository structure with explicit module scope, dependency direction, contract ownership, CODEOWNERS/module README rules, AI guardrails, and an incremental migration sequence.
- [x] Made the approved future structure a mandatory read-only coding policy in `AGENTS.md`, including task-to-owner mapping and incremental migration rules.
- [x] Added a separate future-structure interpretation guide covering every major path, responsibility boundaries, task-routing examples, and common agent misunderstandings without modifying the read-only baseline.
- [x] Added shared API and database contracts covering REST/WebSocket conventions, RBAC, event lifecycle, capability-owned ERD, privacy, retention, migrations, and traceability for MVP plus the five-week advanced delivery.
- [x] Moved the completed US-08 implementation specification to `specs/done/US-08-SPEC.md` and removed its obsolete backlog story file.
- [x] Split the shared API and database contracts into task-routed chapter directories with lightweight README indexes to prevent AI context-window overflow.
- [x] Marked both shared contract directories as mandatory read-only references in `AGENTS.md`, their indexes, and the documentation catalog.
- [x] Refreshed the root `README.md` as the project introduction and repository master index, with task-oriented navigation to scope, architecture, read-only contracts, tracking, and development guides.
- [x] Consolidated the target repository structure and its interpretation guide into one sub-150-line document aligned with the current `backend/`, `frontend/`, `vision/`, and legacy `src/` layout.
- [x] Removed stale shared-contract documentation trees and redirected agent/navigation rules to executable API, wire-type, ORM, migration, and test sources of truth.
- [x] Redesigned and consolidated the two architecture documents into one concise root `ARCHITECTURE.md`, aligned with the problem statement, user-story delivery sequence, and approved capability boundaries.
- [x] Made the root README the only documentation index and removed navigation links from architecture, specs, module docs, and nested guide indexes; retained the mandatory agent-workflow exception.
- [x] Refined US-07 with the confirmed persistent per-camera/zone PPE requirement controls, default-OFF behavior, shared backend storage, and ON/OFF alert semantics.
- [x] Added the Phase 1 spec for US-07 covering behavior, REST/inference contracts, ownership, testing, boundaries, success criteria, and implementation gates; awaiting human approval before planning.
- [x] Added the Phase 2 US-07 implementation plan and dependency-ordered task list; awaiting human approval before production implementation.
- [x] [Vision] Updated US-07 with the full 17-class SH17 checkpoint inventory, source-class IDs, and the boundary that only helmet/glasses/gloves feed the current public PPE observation.
- [x] [Cross-cutting] Re-specified US-07 to expose and render all 17 SH17 detections, while allowing qualified absence of required helmet/glasses/gloves to create an alert.
- [x] [Cross-cutting] Implemented the additive 17-class REST/WebSocket detection contract, canvas overlay labels, and qualified absence rule for required helmet/glasses/gloves; focused tests and `make run` startup pass.
- [x] [Cross-cutting] Decoupled inference from zone setup: playback now streams detection boxes without a four-point zone; zone intrusion remains active only with exactly four points.
- [x] [Vision] Configured US-07 person detection to use SH17 class `person` (ID 0), matching the PPE/object checkpoint.
- [x] [Cross-cutting] Condensed the completed US-07 specification to its active behavior, public contract, ownership, tests, boundaries, and production gates.
- [x] [Cross-cutting] Added an execution-flow diagram and safety-priority order to US-07 for operator and implementation clarity.
- [x] [Backend] Specified the deterministic US-07 rule-engine boundary: model observation plus UI configuration produces `normal` or `violate`, with violation always routed to human review.
- [x] [Cross-cutting] Updated and synchronized US-13 to require a consented custom evaluation dataset; recorded the dataset, split, privacy and benchmark constraints.
- [x] [Cross-cutting] Implemented US-12 privacy persistence with a server-owned `privacy_blurred` value, SH17 identity/head redaction, fail-closed processing, rollback cleanup, and completed specification.
- [x] [Cross-cutting] Added review and persisted-snapshot bounding boxes after the US-12 redaction gate, with focused Python and frontend component tests.
- [x] [Cross-cutting] Completed Product Owner review of the US-27 Phase 1 specification: unlimited zone count at product level, disjoint polygons, grouped review with atomic zone-specific events, and PPE explicitly unchanged/out of scope.
- [x] [Frontend] Amended US-27 with one explicit **Tạo vùng** button as the only creation entrypoint, a single four-point draft drawing mode, cancel/reset behavior and focused UI/E2E acceptance criteria.
- [x] [Cross-cutting] Implemented US-27 and merged the latest `develop2` with a fully passing migrated clean-SQLite check, frontend production build and the complete Alembic chain through `20260811_03`.
- [x] [Cross-cutting] Closed US-27 documentation by moving the multi-zone implementation specification to `specs/done/` and removing the redundant `specs/backlog/US-27.md` story file; the root context map and current structure now point to the completed spec.

## In Progress
- [x] [Cross-cutting] Added required monitoring-area assignment for new/updated `area_manager` accounts, Telegram username/chat-ID administration, reversible user-schema migration, and non-blocking area-scoped Telegram delivery for newly opened alerts. Delivery remains disabled until `TELEGRAM_BOT_TOKEN` and recipient chat IDs are configured.
- [x] [Frontend] Changed HITL counting to pending-review logs rather than current-frame violations. Hat, vest and zone occurrences are consolidated into one log per session track/person; reviewed logs remain visible but leave the pending count, and the eight-log display cap was removed.
- [x] [Frontend] Aligned HITL logs with review context: person cards now use backend `track_id`, each log retains its own inference snapshot/result and opens that exact frame, while the rule-result title is derived from current active zone/PPE occurrences instead of a hard-coded zone-intrusion message.
- [x] [Cross-cutting] Reduced transient PPE alerts: backend creates a clickable review log only after six consecutive missing frames and retracts each matching unreviewed item only after two continuous seconds of explicit presence for the same session TrackID. Human review remains authoritative after submission.
- [ ] Run final browser UAT for the two-zone create/save/reload/inference/grouped-review flow with representative local video.
- [ ] Add the retention cleanup scheduler that enforces the US-16 audit/snapshot deadlines; deadline persistence is complete.
- [ ] Establish final ground truth, qualified-absence evidence and benchmark targets for the hat/vest model before production alerting.
- [ ] Chốt US-13 metric protocol, scenario matrix, sample size and acceptance thresholds before recording the custom dataset.

## Known Issues
- `ppe_alert_confirm_frames=6` is an MVP starting value and must be calibrated using held-out, representative footage before production use.
- `ppe_revoke_confirm_seconds=2.0` is also an MVP starting value and requires calibration against intermittent PPE detections.
- Person false-positive/false-negative rates still need validation on representative factory footage; confidence and NMS thresholds should be tuned from labeled data rather than guessed.
- YOLO11m Safety detects presence; backend derives `missing` from qualified absence. Final US-13 ground truth, false-negative/false-alarm evaluation and target-device latency remain release blockers for real alerts.
- Person-head redaction is a prototype safeguard only; a dedicated, benchmarked face detector with production-cleared provenance/license remains required before pilot use.
- Chrome DevTools MCP is not configured, so US-16 Event Detail/Area Manager and US-27 visual/runtime browser verification remain pending despite passing component tests and production build.
- US-08 browser QA passes with local synthetic media through two reviewed occurrences in one monitoring session; the test media is intentionally not distributed in the repository.

## Next Steps
1. Configure the documented GitHub `production` Environment, Railway variables/pre-deploy command, branch protection and `INITIAL_RELEASE_SOURCE_BRANCH=develop2` before opening the first release PR.
2. Run the first `develop2` to `main` PR through CI, deploy, record its SHA and verify `/health` returns `ready: true`.
3. Exercise the manual Railway rollback workflow once with a known-good immutable SHA/tag.
4. Run US-27 browser UAT with two disjoint zones, mixed machine states, reload restoration and grouped review/event verification.
5. Chốt US-13 metric protocol, annotation guide, scenario matrix, sample size and acceptance thresholds with the Product Owner.
6. Record and annotate the custom US-13 calibration/final evaluation dataset with manifest and checksums.
7. Preserve the passing US-08 browser sequence as an automated repository E2E test.
8. Validate or replace the person-head MVP redactor with a dedicated face detector before pilot/production use.
9. Validate authentication and the complete migration chain against PostgreSQL.
10. Replace the JSONL writer with a centralized sink before any multi-worker deployment.
