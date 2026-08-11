# Project Progress

This is the single progress tracker for the repository. Completed work is grouped by area; current state, known issues, and next steps are project-wide.

## Current State
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
- US-12 now redacts identity in memory before event persistence, with SH17 face/head detections, a per-person head fallback, fail-closed errors, and server-owned privacy metadata.
- ReviewModal now captures the full native video frame after it pauses at the violating inference timestamp, overlays its person and SH17 boxes with matching aspect ratio, and newly persisted US-12 snapshots contain the same annotations only after in-memory identity redaction.
- Added and approved the US-08 tracking/dedup specification with session-scoped track IDs, occurrence lifecycle, reconnect semantics, and database-enforced event idempotency; implementation has started.
- US-08 core implementation now provides session-isolated ByteTrack IDs, deterministic rule occurrences, stale-frame/session guards, additive REST/WebSocket fields, and database-enforced reviewed-event idempotency.
- Validated US-08 with a local-only synthetic 24-second multi-person video covering continuous presence, distinct concurrent tracks, exit/cooldown, and re-entry; test media is intentionally excluded from Git.

## Completed

### Backend
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

### Vision
- [x] Moved root `.pt` model files (`ppe_yolov8n.pt`, `yolo11n.pt`) to dedicated `models/` directory, added `models/README.md`, updated `docs/PROJECT_STRUCTURE.md`, and updated backend configuration and service model resolution.
- [x] Added SH17 identity redaction for face/head classes with a conservative 40%-of-person-head fallback and pure-CV synthetic-image tests.
- [x] Added pure-CV post-redaction JPEG annotation for reviewed person and SH17 bounding boxes, preserving the input frame and skipping duplicate SH17 `person` boxes.
- [x] Added a session-isolated ByteTrack facade with TTL cleanup and a real-model runtime smoke check.

### Frontend
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

### Documentation
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
- [x] [Cross-cutting] Implemented US-12 privacy persistence with a server-owned `privacy_blurred` value, SH17 identity/head redaction, fail-closed processing, rollback cleanup, and completed specification.
- [x] [Cross-cutting] Added review and persisted-snapshot bounding boxes after the US-12 redaction gate, with focused Python and frontend component tests.

## In Progress
- [ ] Replace the controlled-demo safety-shirt color heuristic with trained PPE model weights.
- [ ] Establish ground truth, explicit-missing evidence and benchmark targets for the PPE model before production alerting.
- [ ] Replace the temporary clean SQLite database workaround with a safe legacy-database Alembic upgrade in the two-command setup/run path.

## Known Issues
- The safety-shirt classifier is a color heuristic and is not production PPE detection.
- The PPE checkpoint is present with recorded provenance and class mapping, but it detects PPE presence only. Backend now derives `missing` from qualified absence; ground truth and false-negative benchmark validation remain US-07 blockers for real alerts.
- SH17 identity redaction is an MVP safeguard only; a dedicated, benchmarked face detector with production-cleared provenance/license remains required before pilot use.
- The pytest suite collects successfully but stalls in the shared `TestClient` flow on the current Python 3.14 environment; focused non-`TestClient` checks and live smoke tests pass.
- For the US-07 slice, `make setup` and `make run` startup succeed; full `make check` reaches the legacy Python suite and then stalls under Python 3.14. Chrome DevTools MCP is not configured, so browser visual/runtime verification remains pending.
- US-08 browser QA passes with local synthetic media through two reviewed occurrences in one monitoring session; the test media is intentionally not distributed in the repository.
- Legacy unversioned SQLite databases still require a safe Alembic upgrade path; browser QA passes against a newly created schema, while the original pre-US-08 database remains preserved as a backup.

## Next Steps
1. Make Alembic upgrade safe for the existing unversioned SQLite database and include schema upgrade in the two-command setup/run path.
2. Preserve the passing US-08 browser sequence as an automated repository E2E test.
3. Replace the safety-shirt heuristic while preserving the inference response contract.
4. Validate or replace the MVP redactor with a dedicated face detector before pilot/production use.
5. Implement authenticated Safety Officer identity and validate migrations against PostgreSQL.
