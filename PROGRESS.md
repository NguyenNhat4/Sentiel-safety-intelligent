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
- Required PPE state is rendered on each detected-person box: present is green, explicit missing is red, and unknown is labeled neutrally.
- Removed legacy safety-shirt labels and rule text from the monitoring UI; the operator now sees the saved helmet/glasses/gloves requirement state instead.
- Moved the canonical US-07 implementation specification to `specs/done/US-07-SPEC.md` and documented the returned rule context plus person-box PPE badges.

## Completed

### Backend
- [x] Established the FastAPI modular monolith, typed settings, SQLAlchemy database layer, REST APIs, and test scaffolding.
- [x] Added safety-event lifecycle, reviewed snapshot persistence, statistics, and Safety Agent endpoints.
- [x] Added YOLO person detection, foot-point polygon evaluation, safety-shirt baseline rule, and REST frame inference.
- [x] Added binary WebSocket inference with configuration, correlation metadata, one-frame processing, validation, and structured errors.
- [x] Documented frontend/backend interaction and the recommended confirmed-warning persistence lifecycle.
- [x] Added rules-owned PPE requirement persistence, strict GET/PUT contracts, migration, rollback behavior, and the ON/OFF missing-PPE truth table.
- [x] Refactored PPE configuration from capability submodules into the flat backend layers while preserving runtime contracts.

### Vision
- [x] Moved root `.pt` model files (`ppe_yolov8n.pt`, `yolo11n.pt`) to dedicated `models/` directory, added `models/README.md`, updated `docs/PROJECT_STRUCTURE.md`, and updated backend configuration and service model resolution.

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

## In Progress
- [ ] Replace the controlled-demo safety-shirt color heuristic with trained PPE model weights.
- [ ] Establish ground truth, explicit-missing evidence and benchmark targets for the PPE model before production alerting.

## Known Issues
- The safety-shirt classifier is a color heuristic and is not production PPE detection.
- The PPE checkpoint is present with recorded provenance and class mapping, but it detects PPE presence only. It cannot alone produce an explicit `missing` observation, so ground truth and benchmark validation remain US-07 blockers for real alerts.
- Review snapshots are not face-blurred yet and currently record `privacy_blurred=false`.
- The pytest suite collects successfully but stalls in the shared `TestClient` flow on the current Python 3.14 environment; focused non-`TestClient` checks and live smoke tests pass.
- For the US-07 slice, `make setup` and `make run` startup succeed; full `make check` reaches the legacy Python suite and then stalls under Python 3.14. Chrome DevTools MCP is not configured, so browser visual/runtime verification remains pending.

## Next Steps
1. Replace the safety-shirt heuristic while preserving the inference response contract.
2. Blur faces before any confirmed snapshot is persisted.
3. Implement the PostgreSQL Alembic migration and authenticated Safety Officer identity.
