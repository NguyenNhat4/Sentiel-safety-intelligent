# Project Design Decisions

This is the single decision log for the repository. Prefix each entry with its owning area, such as `[Backend]`, `[Frontend]`, `[Vision]`, or `[Cross-cutting]`.

## 2026-08-01: [Backend] FastAPI + SQLAlchemy modular monolith
- **Reason:** Fast development speed, native WebSocket support, and direct integration with YOLO, OpenCV, LangChain, and PostgreSQL.
- **Rejected alternative:** Microservices, because their operational overhead is not justified during MVP.
- **Constraint:** Maintain clear boundaries between `backend`, `vision`, and `frontend`.

## 2026-08-01: [Backend] Dual database support
- **Reason:** PostgreSQL serves production while SQLite keeps local and test setup lightweight.
- **Constraint:** Use SQLAlchemy constructs compatible with both databases.

## 2026-08-01: [Backend] Realtime alerts and Safety Agent fallback
- **Reason:** Safety Officers need immediate danger-zone alerts and actionable escalation guidance.
- **Constraint:** Provide rule-based recommendations when an OpenAI API key is unavailable.

## 2026-08-01: [Backend] Browser-driven frame inference baseline
- **Reason:** Sampled browser frames provide the shortest path from local video playback to zone overlays and human review.
- **Choice:** YOLO detects people; an HSV torso heuristic detects a high-visibility shirt for the controlled demo.
- **Constraint:** Replace the heuristic with trained PPE weights before field evaluation.

## 2026-08-01: [Frontend] Vanilla browser baseline
- **Reason:** The single MVP flow does not require a framework or build step.
- **Choice:** Keep the Sentinel monitor in static HTML, CSS, and JavaScript served by FastAPI.
- **Constraint:** Support one local video, one four-point zone, one machine toggle, and one pending review.

## 2026-08-02: [Frontend] Inference follows playback
- **Reason:** Playback and inference represent one monitoring action; a separate inference button adds unnecessary state.
- **Choice:** Play starts sampled inference only when four zone points exist. Stop pauses both operations; zone entry pauses playback for review.
- **Constraint:** Playback with fewer than four points is preview-only.

## 2026-08-02: [Cross-cutting] Binary WebSocket inference transport
- **Reason:** Persistent transport avoids repeated HTTP setup and binary JPEG avoids Base64 transfer overhead.
- **Choice:** `/api/v1/ws/inference` accepts per-connection configuration, frame metadata, and binary JPEG frames, then returns correlated JSON results.
- **Frontend behavior:** Send at most one frame every 0.5 seconds with only one frame in flight; try same-origin first and `<hostname>:8000` as a development fallback.
- **Backend behavior:** Run inference outside the async event loop and retain the REST frame endpoint for compatibility.
- **Zone-entry rule:** Keep detecting and drawing people in all machine states, but pause for review only when the detected person's bottom-center foot point enters the polygon while the machine is running.

## 2026-08-02: [Frontend] Build-free ES module structure
- **Reason:** The working `app.js` reached 686 lines and mixed video, zone, transport, rendering, review, and UI responsibilities.
- **Choice:** Split the monitor into native ES modules with a small `app.js` composition root and explicit controller callbacks.
- **Constraint:** Preserve DOM behavior, WebSocket/REST contracts, 2 FPS backpressure, foot-point evaluation, and operator review without introducing a build step.

## 2026-08-02: [Cross-cutting] Central project tracking
- **Reason:** Per-module decision and progress files duplicate navigation and make the current project state harder to discover.
- **Choice:** Keep exactly one root `DECISIONS.md` and one root `PROGRESS.md`, organized by owning area.
- **Constraint:** Modules retain their own `README.md` documentation but must not create additional decision or progress logs.

## 2026-08-02: [Cross-cutting] Confirmed violations are available in event history
- **Reason:** Safety Officers need immediate evidence that an acknowledged warning and its snapshot were saved successfully.
- **Choice:** After `POST /events` returns an acknowledged event, reset the review panel and remain on the monitor. The operator can open the log backed by `GET /events?status=acknowledged`; false alarms do not appear as official warnings.
- **Safety rule:** A person's foot point entering the polygon requires review only while `machine_state` is `running`; detections and bounding boxes remain visible while the machine is stopped.
- **Development constraint:** Permit browser REST calls from any localhost/127.0.0.1 port outside production, while snapshot URLs resolve against the backend origin selected by WebSocket connection.

## 2026-08-03: [Frontend] React + TypeScript feature architecture
- **Reason:** The validated monitor flow now benefits from typed backend contracts, component tests, and explicit feature boundaries as event history and dashboard surfaces grow.
- **Choice:** Replace the build-free ES modules with React 19, TypeScript, and Vite organized into `api`, shared `components`, feature modules, and contract `types`.
- **Compatibility:** Preserve the Sentinel UI, four-point zone behavior, 2 FPS one-frame backpressure, REST payloads, and binary WebSocket protocol.
- **Deployment:** Use Vite during development; FastAPI serves `frontend/dist` in production. Docker builds the frontend in a Node stage and keeps one Python runtime service.

## 2026-08-03: [Cross-cutting] Separate MVP closure from the five-week advanced delivery
- **Reason:** The MVP defined by `specs/PRD.md` must be completed in the current week, while the following five weeks are reserved for the advanced outputs in `docs/project-problem-statement.md`.
- **Choice:** Keep MVP closure and regression in US-01 to US-13 plus US-16 to US-19; plan advanced HITL/escalation and US-20 to US-26 across the subsequent five weeks.
- **Constraint:** Camera factory integration, PLC control, automatic machine stop, and concurrent multi-stream scale require a separate scope decision.
- **Documentation:** Every incomplete story has a canonical `specs/backlog/US-XX.md` whose story content must remain identical to the corresponding section in `specs/USER_STORIES_LIST.md`.

## 2026-08-04: [Vision] Dedicated `models/` directory for ML model weights
- **Reason:** Model files (`.pt`) located at the repository root cluttered the project root directory.
- **Choice:** Move `.pt` weights into a dedicated `models/` folder, documented with `models/README.md`.
- **Backend update:** Update `backend/app/core/config.py` default model paths to `models/yolo11n.pt` and `models/ppe_yolov8n.pt`, with fallback checks in `FrameInferenceService`.

## 2026-08-04: [Cross-cutting] Unified developer onboarding via `make setup` and `uv`
- **Reason:** New team members need a fast, single-command setup for Python virtual environments, package management, and frontend dependencies.
- **Choice:** Added `make setup` target combining `uv sync`, `npm --prefix frontend ci`, and `.env` initialization. Created technical guide `docs/guide/setup/uv-setup.md` and updated developer onboarding docs.

## 2026-08-06: [Cross-cutting] Capability-owned target repository structure
- **Reason:** The original future layout grouped backend code mainly by technical layer, which would blur ownership as authentication, rule authoring, event lifecycle, organization, escalation, analytics, and reporting grow.
- **Choice:** Keep a modular monolith, split backend business code into capability-owned modules, keep `vision/` framework- and persistence-independent behind one facade, and make contracts, CODEOWNERS, module READMEs, mirrored tests, and dependency checks explicit architectural boundaries.
- **Constraint:** A new top-level directory or module-boundary change requires a root decision entry. Cross-module work uses public services/contracts rather than importing another module's repository or model. Generated contracts are not edited manually.
- **Migration:** Adopt the structure incrementally per user story; preserve current REST/WebSocket behavior until a versioned migration is documented and tested.

## 2026-08-06: [Cross-cutting] Shared API and database design contracts
- **Reason:** Frontend, backend, vision, QA, analytics, and operations need one reviewable vocabulary for resources, lifecycle, ownership, privacy, and compatibility across MVP closure and the five-week advanced plan.
- **Choice:** Use task-routed chapters under `docs/API_CONTRACT/` as the human-readable REST/WebSocket design contract and capability-routed chapters under `docs/DATABASE_SCHEMA/` as the logical data/ERD contract. Each directory has a `README.md` reading map; current versus planned routes remain explicit.
- **Source-of-truth constraint:** Runtime REST truth remains module-owned Pydantic/FastAPI definitions; WebSocket and backend–vision truth remains versioned JSON Schema under `contracts/`; Alembic migrations remain database history. Generated artifacts are never edited manually.
- **Privacy constraint:** Raw video/images are not persisted; snapshot records require verified redaction and immutable event/audit context.
- **Governance:** Everything under `docs/API_CONTRACT/` and `docs/DATABASE_SCHEMA/` is read-only for agents and contributors. A conflict requires stopping the implementation and requesting an explicit contract decision; the contract must not be edited as part of ordinary feature work.

## 2026-08-06: [Cross-cutting] One compact target-structure guide
- **Reason:** The 327-line baseline plus a 253-line interpretation guide duplicated context and made human/AI routing harder than the current MVP needs.
- **Choice:** Keep `docs/FUTURE_PROJECT_STRUCTURE.md` under 150 lines as the single source for the minimal target tree, ownership, dependency rules, module template, migration path, and pre-change checklist; remove the separate guide.
- **Current-code alignment:** Treat `backend/`, `frontend/`, and `vision/` as production owners. Treat the existing `src/` LangGraph scaffold as legacy and migrate or remove it incrementally rather than adding new production code there.
- **Constraint:** Create capability folders only when a story has real behavior; new top-level directories or changed boundaries still require an explicit root decision.

## 2026-08-06: [Cross-cutting] Executable definitions replace separate contract docs
- **Supersedes:** The documentation/governance parts of “Shared API and database design contracts”; that entry remains as history.
- **Reason:** The separate `docs/API_CONTRACT/` and `docs/DATABASE_SCHEMA/` trees were removed to reduce duplicated and stale context.
- **Choice:** FastAPI routes, Pydantic schemas, frontend wire types, SQLAlchemy models, Alembic migrations, and their tests are the current contract sources of truth. `backend/README.md` explains the non-OpenAPI WebSocket flow.
- **Constraint:** Breaking changes still require explicit authorization, a root decision entry, and focused compatibility tests or a migration path.

## 2026-08-06: [Cross-cutting] One canonical architecture document
- **Reason:** Root `ARCHITECTURE.md` and `docs/architecture_diagram.md` duplicated diagrams, mixed implemented and planned behavior, and drifted from the approved capability ownership.
- **Choice:** Keep the single root `ARCHITECTURE.md` required by the target structure; merge into it only the useful system and runtime views, explicitly separate current state from target state, and remove the duplicate diagram file.
- **Constraints:** The modular-monolith ownership and dependency direction in `docs/FUTURE_PROJECT_STRUCTURE.md` remain authoritative. Executable definitions remain runtime contract truth; architecture prose cannot silently change them.
- **Safety consequences:** Vision emits observations, deterministic backend rules own severity/event lifecycle, LLM output is advisory, and unredacted evidence must never be persisted.

## 2026-08-06: [Cross-cutting] Root README is the only documentation index
- **Reason:** Layered catalogs and cross-document links create competing navigation paths and make documentation depend on file placement outside its own scope.
- **Choice:** Only the root repository README indexes documentation. All other documents are standalone and do not link to one another; the agent workflow file is the sole exception because it must load mandatory context.
- **Constraint:** Moving or adding documentation requires updating the root index. The approved read-only structure baseline is not rewritten solely to remove its existing historical links.

## 2026-08-06: [Cross-cutting] Persist PPE requirements as a rules-owned resource
- **Reason:** Safety Officers configure required helmet, safety glasses, and gloves once for a camera–zone pair, and every browser/device must use the same saved rule.
- **Choice:** Backend `rules` owns an idempotent GET/PUT resource keyed by `camera_id` and `zone_id`; absent configuration materializes as three OFF values. The frontend keeps edits as draft until an explicit save succeeds.
- **Alert semantics:** OFF suppresses alerts only and does not disable model observation. ON creates a PPE alert only for an explicit `missing` observation meeting the configured confidence threshold; `present` and `unknown` do not alert.
- **MVP constraint:** The current UI uses fixed identifiers `uploaded_video` and `zone_01`. The API and unique database key preserve a future per-camera/per-zone boundary without implementing multi-camera management now.
- **Compatibility:** REST/WebSocket inference changes remain additive. Model integration cannot be completed until approved weights, class mapping, license, ground truth, and benchmark targets are available.

## 2026-08-06: [Vision] PPE observations cross the backend through an integration adapter
- **Reason:** US-07 needs per-person PPE observations while the approved structure keeps provider/model code out of backend services and safety decisions out of vision.
- **Choice:** `vision.api.PpeVisionFacade` emits only present/unknown helmet, glasses and gloves observations. `backend.app.integrations.ppe_vision.PpeVisionAdapter` is the sole backend adapter to that public facade; `rules` applies saved requirements and determines alerts.
- **Constraint:** The SH17 checkpoint has no explicit missing-PPE classes, so absence is represented as `unknown`, never `missing`.

## 2026-08-06: [Backend] Layered backend replaces capability submodules
- **Supersedes:** The backend-folder choice in “Capability-owned target repository structure”; that entry remains as history.
- **Reason:** The current codebase and legacy `src` scaffold already use a small, familiar API/model/schema/service layout. Capability subfolders add navigation and boilerplate without enough MVP complexity to justify them.
- **Choice:** Keep production backend code under `backend/app/api`, `core`, `integrations`, `models`, `schemas` and `services`; do not create `backend/app/modules/<capability>` or a repository layer for small resources.
- **Migration:** Move US-07 PPE route, ORM, schemas and logic into their matching layers while preserving endpoint paths, payloads, database table and tests.
