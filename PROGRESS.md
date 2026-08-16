# Project Progress

## 2026-08-16: [Cross-cutting] Decouple the camera-wide machine switch from danger zones
- The machine control is now always enabled, including before a zone is created or selected. Its state is sent as a camera-wide WebSocket configuration value and immediately refreshes the active inference configuration.
- Zone intrusion remains independent of machine state. The camera-wide state now controls only PPE evaluation, so a stopped machine suppresses PPE alerts consistently across all zones.

## 2026-08-16: [Frontend] Align danger-zone UI copy and event metadata with the active rule
- The monitor review pop-up, alert summary and confirmed-event history now say **Có người vào vùng cấm** for either machine state; the machine state remains visible only as operating context.
- The legacy single-event fallback now writes the canonical `zone_intrusion` event type, matching the existing backend event contract. Focused popup tests cover a stopped-machine zone intrusion.

## 2026-08-16: [Backend] Alert enabled danger-zone intrusion for either machine state
- Updated deterministic and multi-zone inference rules so a detected foot point inside any enabled zone makes the frame violate whether its machine is `running` or `stopped`; machine state remains audit/UI context.
- Required PPE is now evaluated only while the relevant machine state is `running`; stopped machines keep PPE observations visible but suppress PPE alerts. Kept the existing frame-level review popup, per-track/per-zone occurrence deduplication, and per-zone event persistence.

## 2026-08-15: [Frontend] Replay the uploaded video without selecting it again
- When the uploaded video ends, the monitor preserves its existing browser object URL, captures the final preview frame, rewinds to `0`, and enables the **Phát lại** control.
- A UI regression test verifies that ending an uploaded video leaves the replay control enabled and reuses the same video rather than requiring a second file selection.

## 2026-08-15: [Frontend] Explain concrete reasons in the HITL review pop-up
- The review title, summary and pending-review message now derive from the inference result: each affected person’s missing required hat/vest and each active danger-zone entry are named explicitly. A combined PPE and zone violation displays both reasons rather than a generic zone-only message.

## 2026-08-15: [Backend] Lock hat/vest and danger-zone rule truth table
- Added deterministic regression coverage for required hat/vest, zero or multiple detected people, and danger-zone entry. A violation is raised when any detected person lacks a required PPE item or enters an enabled danger zone regardless of simulated machine state.
- Restored the additive legacy GET aliases on `PpeRequirementResponse`: callers of the canonical `hat_vest_v1` response no longer need to supply legacy fields, while `helmet_required` continues to mirror `hat_required`.

## 2026-08-15: [Backend] Smooth violation alerts with four consecutive frames
- Added `VIOLATION_FRAME=4` to development and production environment templates. The session-local tracker now opens a review only after four consecutive observations of the same track/rule; any non-violating frame resets the pending sequence.

## 2026-08-15: [Backend] Bridge stale PPE browser payloads to the hat/vest contract
- `PUT /api/v1/ppe-requirements/{camera_id}/{zone_id}` now accepts the complete former helmet/glasses/gloves boolean payload as a temporary compatibility path, mapping helmet to hat and requiring vest.
- Canonical `hat_vest_v1` persistence and inference remain unchanged; GET includes read-only aliases so an old browser can load and save without 422. Focused contract tests cover legacy mapping and reject mixed payloads.

## 2026-08-15: [Cross-cutting] Isolate Docker Compose test database
- `docker-compose.yml` loads `.env.development` and starts a dedicated disposable PostgreSQL service; only `DATABASE_URL` is redirected away from the developer-configured database.
- Once the database healthcheck succeeds, the container runs migrations, starts in development mode, and idempotently seeds demo users; remaining application variables still come from `.env.development`.

## 2026-08-15: [Vision/Backend] Restore single YOLO11m Safety deployment artifact
- Production image, Compose and hosted environment examples now use only the pinned `models/yolo11m_safety.pt`; startup verifies its approved SHA-256 before serving traffic.
- Removed stale `PERSON_MODEL_PATH`, YOLO11n and SH17 PPE artifact wiring from the active deployment path, preventing a wrongly named checkpoint from reaching inference.

## 2026-08-13: [Backend] Analysis PPE requirement loading uses the request database session
- Frame inference REST and WebSocket paths now load the active PPE profile through their injected SQLAlchemy session, so test database overrides and runtime database selection are respected.
- Added Alembic's OS-aware `path_separator` setting to remove the deprecated legacy path parsing warning.

This is the single progress tracker for the repository. Completed work is grouped by area; current state, known issues, and next steps are project-wide.

## Current State
- `/health` is ready only when runtime models are initialized, the selected database is live PostgreSQL (not SQLite fallback), and the configured S3 bucket answers `HeadBucket`; degraded responses identify the unavailable dependency without exposing provider details or credentials.
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
- Python static checks, focused single-model backend/vision tests, frontend lint/type-check/unit/component tests, and production build pass; full `make check` remains blocked by the documented Python 3.14 test hang.
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
- [x] Pause playback when a returned frame has a newly opened zone/PPE occurrence; enabled-zone intrusion is a violation regardless of simulated machine state.
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
- [x] [Cross-cutting] Implemented US-27 and merged the latest `develop2` with a fully passing migrated clean-SQLite `make check` (8 root, 87 backend, 8 vision and 44 frontend tests), frontend production build and the complete Alembic chain through `20260811_03`. Bare local `make check` still exposes the three pre-existing developer-PPE-state failures recorded below.
- [x] [Cross-cutting] Closed US-27 documentation by moving the multi-zone implementation specification to `specs/done/` and removing the redundant `specs/backlog/US-27.md` story file; the root context map and current structure now point to the completed spec.

## In Progress
- [ ] Run final browser UAT for the two-zone create/save/reload/inference/grouped-review flow with representative local video.
- [ ] Establish final ground truth, qualified-absence evidence and benchmark targets for the hat/vest model before production alerting.
- [ ] Chốt US-13 metric protocol, scenario matrix, sample size and acceptance thresholds before recording the custom dataset.

## Known Issues
- Person false-positive/false-negative rates still need validation on representative factory footage; confidence and NMS thresholds should be tuned from labeled data rather than guessed.
- YOLO11m Safety detects presence; backend derives `missing` from qualified absence. Final US-13 ground truth, false-negative/false-alarm evaluation and target-device latency remain release blockers for real alerts.
- Person-head redaction is a prototype safeguard only; a dedicated, benchmarked face detector with production-cleared provenance/license remains required before pilot use.
- Python 3.14 in the current environment deadlocks AnyIO's blocking portal, so FastAPI/Starlette `TestClient` and full `make check` cannot complete here. Focused non-portal backend tests pass; full API/WebSocket regression must be rerun on the supported CI Python/runtime.
- Chrome DevTools MCP is not configured, so US-27 browser visual/runtime verification remains pending despite passing component tests and production build.
- US-08 browser QA passes with local synthetic media through two reviewed occurrences in one monitoring session; the test media is intentionally not distributed in the repository.
- Legacy unversioned SQLite databases still require a safe Alembic upgrade path; browser QA passes against a newly created schema, while the original pre-US-08 database remains preserved as a backup.

## Next Steps
1. Run US-27 browser UAT with two disjoint zones, mixed machine states, reload restoration and grouped review/event verification.
2. Chốt US-13 metric protocol, annotation guide, scenario matrix, sample size and acceptance thresholds with the Product Owner.
3. Record and annotate the custom US-13 calibration/final evaluation dataset with manifest and checksums.
4. Run the complete API/WebSocket suite on the supported CI Python/runtime and perform `make setup` + `make run` release smoke testing.
5. Preserve the passing US-08 browser sequence as an automated repository E2E test.
6. Validate or replace the person-head MVP redactor with a dedicated face detector before pilot/production use.
7. Validate authentication and the complete migration chain against PostgreSQL.
8. Replace the JSONL writer with a centralized sink before any multi-worker deployment.
