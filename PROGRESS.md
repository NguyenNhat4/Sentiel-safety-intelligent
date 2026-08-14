# Project Progress

This is the single progress tracker for the repository. Completed work is grouped by area; current state, known issues, and next steps are project-wide.

## Current State
- `/health` now reaches `ready=true` only after person, PPE, and ByteTrack inference startup warm-up succeeds; a missing tracker dependency fails startup instead of the first WebSocket frame.
- Development configuration is now isolated in `.env.development`, while Docker Compose injects `.env.production` for production runtime.
- Docker production dependencies use a separate headless runtime set, excluding development tools and unneeded Ultralytics GUI/plotting/dataframe dependencies to reduce the shipped image size.
- The production Docker image installs CPU-only PyTorch/torchvision wheels and reuses a BuildKit pip cache, avoiding unnecessary Triton/CUDA downloads on CPU deployments.
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
- Python static checks and frontend lint, type-check, unit/component tests, and production build pass.
- US-07 now has shared default-OFF PPE requirement persistence, typed GET/PUT APIs, an explicit-save frontend panel, and per-person PPE observation plumbing for the fixed `uploaded_video` / `zone_01` pair.
- Backend US-07 follows the approved flat layered layout (`api`, `models`, `schemas`, `services`, `integrations`); the temporary `backend/app/modules` tree has been removed.
- Inference `rule` now echoes the persisted PPE requirement booleans used for that frame, making configured helmet/glasses/gloves state observable in REST and WebSocket responses.
- Required PPE state is rendered on each detected-person box: present is green, qualified absence is red `missing`, and unknown is labeled neutrally.
- Removed legacy safety-shirt labels and rule text from the monitoring UI; the operator now sees the saved helmet/glasses/gloves requirement state instead.
- Moved the canonical US-07 implementation specification to `specs/done/US-07-SPEC.md` and documented the returned rule context plus person-box PPE badges.
- US-13 now specifies a project-owned custom dataset as its primary acceptance source, with scenario coverage, versioned ground truth, calibration/final isolation and reproducible metric/latency evidence.
- US-12 now redacts identity in memory before event persistence, with SH17 face/head detections, a per-person head fallback, fail-closed errors, and server-owned privacy metadata.
- ReviewModal now captures the full native video frame after it pauses at the violating inference timestamp, overlays its person and SH17 boxes with matching aspect ratio, and newly persisted US-12 snapshots contain the same annotations only after in-memory identity redaction.
- Completed US-08 tracking/dedup with session-scoped track IDs, occurrence lifecycle, reconnect semantics, spatial track handoff, and database-enforced event idempotency.
- US-08 core implementation now provides session-isolated ByteTrack IDs, deterministic rule occurrences, stale-frame/session guards, additive REST/WebSocket fields, and database-enforced reviewed-event idempotency.
- Validated US-08 with a local-only synthetic 24-second multi-person video covering continuous presence, distinct concurrent tracks, exit/cooldown, and re-entry; test media is intentionally excluded from Git.
- US-27 is implemented for multiple disjoint four-point danger zones on one video, per-zone simulated machine state, revisioned persistence, zone-scoped dedup, additive inference contracts and atomic grouped-review persistence. PPE remains the unchanged whole-frame `uploaded_video/zone_01` configuration.
- The US-27 feature branch is merged with `origin/develop2` at `9c0141c`; auth, operational metrics and multi-zone routes coexist, and Alembic now advances linearly through auth `20260811_01`, forced-password `20260811_02` and monitoring-zones `20260811_03`.
- Backend now persists lightweight operational request, inference, and WebSocket outcome metrics to rotated JSONL and exposes bounded aggregates at `GET /api/v1/operational-metrics`.
- `make setup` and `make run` now run versioned Alembic upgrades, so a new SQLite database is created at the current schema automatically.
- A separate read-only “Quan sát hệ thống” page now displays JSONL operational request, latency, inference, and error aggregates.

## Completed

### Backend
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
- [x] Moved root `.pt` model files (`ppe_yolov8n.pt`, `yolo11n.pt`) to dedicated `models/` directory, added `models/README.md`, updated `docs/PROJECT_STRUCTURE.md`, and updated backend configuration and service model resolution.
- [x] Fixed person false positives caused by using the SH17 PPE checkpoint as the person detector; frame inference now uses the dedicated YOLO11 person checkpoint while SH17 remains responsible for PPE/object observations.
- [x] Added SH17 identity redaction for face/head classes with a conservative 40%-of-person-head fallback and pure-CV synthetic-image tests.
- [x] Added pure-CV post-redaction JPEG annotation for reviewed person and SH17 bounding boxes, preserving the input frame and skipping duplicate SH17 `person` boxes.
- [x] Added `scripts/benchmark_model.py` to measure YOLO latency (mean/P50/P95/P99) and inference throughput using `data/test.mp4` by default, including a combined person+PPE pipeline mode.
- [x] Added `eval/results/model-benchmark-report.md` with the combined person+PPE benchmark result and measurement boundaries.
- [x] Added a session-isolated ByteTrack facade with TTL cleanup and a real-model runtime smoke check.

### Frontend
- [x] Curated browser-facing SH17 detection displays to people plus canonical `helmet`, `glasses`, `gloves`, and `safety-vest` classes across the live Canvas, grouped alert list, and review overlay, while preserving the complete inference and review-metadata payload.
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
- [ ] Complete US-18 Docker-local smoke, backup/restore rehearsal and browser UAT evidence on one release commit.
- [ ] Run final browser UAT for the two-zone create/save/reload/inference/grouped-review flow with representative local video.
- [ ] Replace the controlled-demo safety-shirt color heuristic with trained PPE model weights.
- [ ] Establish ground truth, explicit-missing evidence and benchmark targets for the PPE model before production alerting.
- [ ] Chốt US-13 metric protocol, scenario matrix, sample size and acceptance thresholds before recording the custom dataset.
- [ ] Replace the temporary clean SQLite database workaround with a safe legacy-database Alembic upgrade in the two-command setup/run path.

## Known Issues
- Person false-positive/false-negative rates still need validation on representative factory footage; confidence and NMS thresholds should be tuned from labeled data rather than guessed.
- The safety-shirt classifier is a color heuristic and is not production PPE detection.
- The PPE checkpoint is present with recorded provenance and class mapping, but it detects PPE presence only. Backend now derives `missing` from qualified absence; ground truth and false-negative benchmark validation remain US-07 blockers for real alerts.
- SH17 identity redaction is an MVP safeguard only; a dedicated, benchmarked face detector with production-cleared provenance/license remains required before pilot use.
- Bare `make check` currently has three pre-existing analysis-test failures because the global inference service reads required PPE flags from the developer's persistent local database while those legacy zone-only tests assume PPE is OFF. US-27 focused tests isolate PPE and pass; this slice does not change PPE configuration or semantics.
- Chrome DevTools MCP is not configured, so US-27 browser visual/runtime verification remains pending despite passing component tests and production build.
- US-08 browser QA passes with local synthetic media through two reviewed occurrences in one monitoring session; the test media is intentionally not distributed in the repository.
- Legacy unversioned SQLite databases still require a safe Alembic upgrade path; browser QA passes against a newly created schema, while the original pre-US-08 database remains preserved as a backup.

## Next Steps
1. Run US-27 browser UAT with two disjoint zones, mixed machine states, reload restoration and grouped review/event verification.
2. Chốt US-13 metric protocol, annotation guide, scenario matrix, sample size and acceptance thresholds with the Product Owner.
3. Record and annotate the custom US-13 calibration/final evaluation dataset with manifest and checksums.
4. Make Alembic adoption safe for existing unversioned SQLite databases in the two-command setup/run path.
5. Isolate legacy analysis tests from developer PPE database state without changing PPE runtime semantics.
6. Replace the safety-shirt heuristic while preserving the inference response contract.
7. Preserve the passing US-08 browser sequence as an automated repository E2E test.
8. Validate or replace the MVP redactor with a dedicated face detector before pilot/production use.
9. Validate authentication and the complete migration chain against PostgreSQL.
10. Replace the JSONL writer with a centralized sink before any multi-worker deployment.
