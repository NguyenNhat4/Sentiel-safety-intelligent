# Project Design Decisions

## 2026-08-15: [Cross-cutting] One violation log per tracked person and video session
- **Choice:** Confirmed warnings use `(monitoring_session_id, track_id)` as the per-video person-log key. Missing hat, missing vest, restricted-camera presence, and zone intrusion occurrences are accumulated into that one event while the same track remains in the session.
- **Boundary:** `track_id` remains a temporary ByteTrack association, not a person's identity and not a cross-video or cross-camera identifier. A new video session may create a new log for the same physical person.

This is the single decision log for the repository. Prefix each entry with its owning area, such as `[Backend]`, `[Frontend]`, `[Vision]`, or `[Cross-cutting]`.

## 2026-08-16: [Vision/Backend] Use YuNet-first snapshot redaction with a per-person fallback
- **Choice:** Run pinned OpenCV YuNet once when a reviewed snapshot is persisted, blur every expanded face region, and apply the existing upper-40% blur only to canonical people without an associated face. Unassociated YuNet faces are still blurred.
- **Boundary:** YOLO11m Safety remains the sole source of canonical person/hat/vest observations and does not perform face detection. YuNet is reachable only through the privacy facade/adapter and cannot affect safety decisions.
- **Failure semantics:** A valid no-face result or per-frame YuNet error degrades to the existing person-head fallback; the latter emits only a stable privacy-safe operational error kind. A missing/corrupt YuNet artifact fails startup, and a snapshot without any valid canonical person remains fail-closed.
- **Artifact:** Pin OpenCV Zoo revision `41c69c8506f4ddb038aad0f5da660cbc2a83f58e`; the ONNX artifact is 232,589 bytes with SHA-256 `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` and is managed through Git LFS.

## 2026-08-16: [Cross-cutting] Gate Railway production image deploys on GitHub CI
- **Choice:** `main` accepts protected pull requests only. GitHub Actions runs Python 3.11 locked dependency checks, isolated frontend/backend/vision suites, and a Docker build. Successful `main` CI pushes `DOCKERHUB_IMAGE:latest`; a `workflow_run` then calls Railway CLI `redeploy` and requires `/health` to return `ready: true`.
- **Secrets and rollback:** Repository Actions secrets own Docker Hub credentials, Railway token/service/environment and public base URL; Railway Variables retain database, S3, model and optional provider configuration. Because only the moving `:latest` tag is published, rollback uses Railway Deployment History rather than a misleading SHA workflow.
- **Initial release constraint:** The optional repository variable `INITIAL_RELEASE_SOURCE_BRANCH=develop2` makes the required `Release source` check reject all other source branches. Remove the variable after the first release.

## 2026-08-16: [Cross-cutting] Make machine state camera-wide, not zone-owned
- **Reason:** The UI disabled machine control until a zone was selected, while zone intrusion no longer depends on machine state. This made the control unavailable and tied PPE behavior to unrelated zone configuration.
- **Choice:** Multi-zone WebSocket configuration carries its own `machine_state`, defaulting to `running` for compatibility. The frontend switch is always available and pushes an updated configuration immediately. Zone geometry and persisted zone rows remain unchanged; the camera-wide state gates PPE evaluation only.
- **Compatibility:** The change is additive for multi-zone WebSocket clients. Existing clients that omit `machine_state` retain the `running` default; legacy one-zone messages continue unchanged.

## 2026-08-15: [Cross-cutting] Area managers close only their own routed logs
- **Choice:** The area workspace presents its scoped events as selectable logs with snapshot and event context. An area manager may set only an event in their assigned area to `resolved` or `false_alarm`.
- **Reason:** This supports local follow-up without allowing a manager to see or alter another area's incidents, or to change the safety officer's original confirmation flow.

## 2026-08-15: [Cross-cutting] Confirmed violations route by assigned area
- **Choice:** A notification to an area manager is queued only after a safety manager confirms an event as `acknowledged`. The event's `zone_id` is matched to the manager's `managed_area_id`; the area workspace and statistics API enforce the same scope server-side.
- **Reason:** An AI candidate is not an official violation. This prevents unverified alerts and information from another area appearing in the manager's workspace.
- **Reliability:** Idempotent event/batch retries do not queue a second notification.

## 2026-08-13: [Frontend] Upload video per selected monitoring area
- **Choice:** A browser-local uploaded video belongs only to the selected danger area (`zone_id`). Switching areas swaps to that area's own video or an empty video state, and inference uses the existing legacy single-zone WebSocket configuration for that selected area only.
- **Reason:** The operator requires each displayed Vùng/Khu vực to have an independent video workflow rather than evaluating one uploaded video against every configured area.
- **Compatibility:** Stored zone collections and the multi-zone WebSocket contract remain supported for existing clients. Uploaded browser videos remain transient and are not persisted or shared between areas.

## 2026-08-11: [Backend] Keep SQLite as the current MVP default
- **Choice:** The two-command local workflow and default settings use `sqlite:///./data/safety_events.db`. PostgreSQL support from `develop2` remains available through an explicit `DATABASE_URL` override and is still the deployment direction after environment validation.
- **Reason:** The Product Owner explicitly deferred database expansion and chose to continue with SQLite for now. This also lets a new team member run `make setup` and `make run` without provisioning PostgreSQL first.
- **Constraint:** Keep Alembic revisions portable across SQLite and PostgreSQL; do not introduce a second persistence implementation or remove the PostgreSQL runtime path.

## 2026-08-11: [Cross-cutting] Expand one monitoring video to multiple danger zones
- **Context:** The running baseline has one fixed `zone_01`, one polygon and one machine toggle, so it cannot represent multiple machines or danger areas visible in the same frame.
- **Choice:** Add US-27 for multiple four-point zones on one `uploaded_video` monitoring session. Each zone has a stable `zone_id`, display name, enabled state and independent simulated `running`/`stopped` state. Detection/tracking runs once per frame; backend evaluates every active polygon afterward.
- **Safety semantics:** Zone intrusion occurrences use `zone_intrusion:{zone_id}` and are deduplicated independently. Active polygons must be spatially disjoint: intersection, boundary/vertex contact and containment are rejected atomically because the current boundary-inclusive foot-point rule would otherwise make zone ownership ambiguous. One grouped HITL review may cover multiple distinct zones, while persistence keeps one event per zone in an atomic batch so audit/statistics remain attributable.
- **Compatibility:** Extend REST/WebSocket responses with zone collections, memberships and zone results. Preserve the scalar one-zone contract and `POST /api/v1/events` during a documented compatibility period; new clients must not infer multi-zone safety decisions from scalar summary fields.
- **MVP boundary:** One video/stream at a time, no fixed product-level zone-count limit, simulated machine state only. Generic HTTP/WebSocket payload-size and runtime safety controls still apply, but they must not encode a business rule such as `max_zones`. PLC and multi-stream are not part of US-27.
- **PPE boundary:** US-27 does not modify PPE. The installed SH17 checkpoint, whole-frame `uploaded_video/zone_01` requirements, qualified-absence rule, alerts, UI and persistence retain their current behavior. Per-zone PPE requires a separate story and decision.
- **Creation workflow:** The monitor exposes one explicit **Tạo vùng** button. It creates and selects one draft, then enables four-point Canvas drawing; ordinary Canvas clicks never create a zone. A second draft cannot start until the current draft is completed or cancelled.
- **Implementation:** The saved collection is an optimistic-revision REST resource; WebSocket/REST multi-zone inference accepts only the saved revision. Grouped review uses `event-batches`, one shared redacted snapshot and one event per zone in a single transaction. The legacy scalar inference and single-event routes remain available.
- **Gate:** Product Owner approved Phase 1 and requested implementation. The US-27 code slice is complete; release/browser UAT remains part of final MVP verification. No PPE behavior was changed.

## 2026-08-11: [Frontend] Separate read-only operations view
- **Choice:** Add a dedicated “Quan sát hệ thống” navigation view for operational JSONL aggregates, separate from the safety monitor and violation history.
- **Reason:** Operational health needs an at-a-glance interface without exposing raw logs or distracting the Safety Officer's active monitoring workflow.
- **Constraint:** The view only consumes aggregate data from `GET /api/v1/operational-metrics`; it has no write actions and does not expose raw events or sensitive payloads.

## 2026-08-11: [Backend] Run database migrations in the two-command workflow
- **Choice:** `make setup` and `make run` invoke `alembic upgrade head` through the idempotent `make db-upgrade` target before the backend starts.
- **Reason:** A new developer or deployment must receive the current schema automatically, including new tables and migration-managed columns.
- **Constraint:** This applies migrations that are already versioned and reviewed. A legacy database created outside Alembic and missing `alembic_version` still needs a safe one-time bootstrap migration; runtime model inspection must not silently mutate production schema.

## 2026-08-11: [Backend] Lightweight operational metrics use rotated JSONL
- **Choice:** Persist a finite, privacy-safe operational event schema to `data/operational-metrics.jsonl` and expose bounded aggregates through `GET /api/v1/operational-metrics`; do not add Prometheus, Grafana, a database table, or an external monitoring service in this MVP slice.
- **Reason:** The Product Owner selected log-derived monitoring with restart persistence and minimal operational overhead.
- **Constraints:** Only one writer process is supported. Events exclude frames, snapshot data, IDs, raw paths/query strings, client addresses, credentials, and exception text. Rotation is size-based; readers tolerate corrupt/partial records and report partial scans.

## 2026-08-11: [Backend] Reuse warm PostgreSQL connections
- PostgreSQL uses a bounded LIFO pool, TCP keepalive and connection recycling. Per-checkout pre-ping is disabled by default because it adds a remote round-trip to every CRUD request; deployments with unstable idle connections may opt in through configuration.
- ORM sessions retain loaded values after commit, and write services do not immediately refresh objects whose response fields are already generated client-side.

## 2026-08-11: [Frontend] Role workspaces and system administration
- Safety officers use Live Monitor and event history; area managers use the dedicated compliance dashboard; system administrators retain safety operations and receive the additional account-management entry.

## 2026-08-11: [Cross-cutting] Temporary-password recovery flow
- New and administrator-reset accounts must replace their temporary password after login. Further self-service changes are disabled; forgotten-password recovery returns to System Admin.

## 2026-08-11: [Backend] PostgreSQL-first runtime with SQLite startup fallback
- Runtime prefers `DATABASE_URL`, optionally selects local SQLite once at startup, and reports the selected backend through `/health`. Alembic never follows the fallback.

## 2026-08-11: [Cross-cutting] Persisted browser authentication and exactly three roles
- Server-side hashed sessions back login/me/logout. Supported roles are `system_admin`, `safety_manager`, and `area_manager`; only system administrators may call account-management APIs.

## 2026-08-11: [Vision/Backend] Preserve occurrences across nearby track-ID handoffs
- **Choice:** When a new track with the same rule appears near the last normalized foot-point of an active track that just disappeared, transfer the active occurrence during the lost-track grace window.
- **Reason:** This prevents a ByteTrack ID switch at the zone boundary from opening a second review while the same person exits.
- **Boundary:** A distant track, a different rule, or a replacement after the grace window still opens an independent occurrence.

## 2026-08-07: [Cross-cutting] Session-scoped tracking and occurrence-based event deduplication
- **Reason:** Frame-independent detections and the current WebSocket reconnect after review can assign a new identity to the same person and create repeated review/event candidates for one continuous violation.
- **Choice:** Frontend owns a UUID `monitoring_session_id` for one selected video; vision owns session-isolated ByteTrack IDs; backend services own deterministic violation occurrences keyed by session, track, and rule. A new `occurrence_id` is emitted only after a violation clears and re-arms.
- **Defaults:** Lost-track grace is 3 sampled frames, exit confirmation is 2 frames, cooldown is 2 seconds, and in-memory session TTL is 300 seconds.
- **Review semantics:** Multiple new occurrences in one frame use one grouped HITL review. False alarm does not re-open the same occurrence before it clears.
- **Persistence:** Session/tracker state remains bounded in memory for MVP. Reviewed event creation persists occurrence IDs and enforces database idempotency; REST/WebSocket contract changes are additive.
- **Privacy:** `track_id` is session-local technical association only and must never become biometric identity or cross-session/cross-camera recognition.

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

## 2026-08-08: [Cross-cutting] Expose SH17 detections and use qualified PPE absence for alerts
- **Supersedes:** Alert-semantics portions of the 2026-08-06 PPE requirements decision and the 2026-08-06 vision-observation decision; both entries remain as history.
- **Reason:** Safety Officers need the full visual evidence from the installed 17-class SH17 checkpoint and explicitly require a missing helmet to alert when the helmet rule is ON.
- **Choice:** Add an additive `detections` collection to REST/WebSocket inference results, containing every SH17 class with its ID, name, bbox, confidence and optional person association. Keep the existing three PPE requirements; the backend derives `missing` when a person passes the evaluation-confidence and association guards but has no associated helmet, glasses or gloves detection.
- **Constraint:** Only helmet, safety glasses and gloves can alert in US-07. Vision supplies observations; backend remains the sole owner of absence evaluation and alert rules. `missing` has no fabricated detector confidence, and its false-negative rate must be benchmarked before production use.

## 2026-08-08: [Cross-cutting] Detection is independent of danger-zone configuration
- **Reason:** Safety Officers need to see model detections while defining or omitting a zone.
- **Choice:** Start inference whenever playback starts. A zone is active only with exactly four points; zero or partial points are sent as an empty zone and produce no zone-intrusion result. PPE evaluation remains active in both cases.

## 2026-08-08: [Vision] Use SH17 as the single inference checkpoint
- **Reason:** One detector must provide both person and PPE/object boxes so associations share one class vocabulary and model artifact.
- **Choice:** Use SH17 class `0` for person boxes and its remaining class IDs for PPE/object detections in US-07. The legacy YOLO11 person checkpoint is not used by this flow.

## 2026-08-08: [Backend] Deterministic rule engine owns normal versus violate
- **Reason:** Model observations and UI configuration must converge in one auditable decision before a human review is requested.
- **Choice:** A backend service consumes observations, persisted PPE requirements, machine state and zone context, then returns only `normal` or `violate`; every `violate` requires HITL review. Vision and frontend do not decide violations.

## 2026-08-08: [Frontend] Consolidated detection list in AlertPanel and ReviewModal pop-up
- **Reason:** Drawing heavy text labels directly over bounding boxes on video/canvas causes text overlap and visual clutter when multiple objects are detected.
- **Choice:**
  1. Map detection classes to a consistent color palette shared between Canvas bounding boxes and the AlertPanel summary list.
  2. Display all detected objects (shoes, clothing, helmet, gloves, etc.) in the AlertPanel with matching color indicator dots and confidence badges.
  3. Transform human review into a pop-up dialog (`ReviewModal`) that automatically opens on alert or can be opened via a prominent alert trigger card, allowing the operator to select `VIOLATE` (Vi phạm thực tế) or `NORMAL` (Bình thường / báo sai).

## 2026-08-08: [Frontend] Allow WebSocket configure message with empty zone_points
- **Reason:** Users playing video before configuring 4 zone points experienced WebSocket connection timeouts because `InferenceClient.updateConfiguration()` incorrectly blocked sending `{type: "configure"}` when `zone_points.length !== 4`.
- **Choice:** Remove the `zone_points.length !== 4` guard in `InferenceClient.updateConfiguration()`, allowing 0 to 4 zone points to be sent to backend WebSocket inference so detection streams immediately upon playback start.

## 2026-08-08: [Frontend] Person-grouped detection list and centered 70% snapshot ReviewModal
- **Reason:** Operators need detected objects organized hierarchically per detected individual, and a large centered snapshot dialog when inspecting violations.
- **Choice:**
  1. Group model detections in `AlertPanel` under individual Person cards (`PERSON #1`, `PERSON #2`, ...) and standalone `SCENE OBJECTS` cards with bounding box color dots, omitting rule-based required PPE badges from the list.
  2. Center `ReviewModal` in the middle of the screen with a 16:9 widescreen snapshot container taking ~70% of screen height, with confirmation buttons directly below. Pop-up triggers strictly when `result === "violate"`.

## 2026-08-08: [Backend] Observations index bounds safety and vision loop optimization
- **Reason:** If a custom vision provider or mock returns fewer observations than detected people, accessing `observations[index]` causes an `IndexError`.
- **Choice:**
  1. Safely fetch `observations[index]` with fallback to default unknown observations when `index >= len(observations)`.
  2. Reuse computed `confidence` in `PpeVisionFacade.observe()` loop to eliminate redundant calls.

## 2026-08-09: [Cross-cutting] US-13 uses a project-owned custom evaluation dataset
- **Reason:** Public workplace-video datasets do not provide the combined per-person helmet/glasses/gloves state, project-specific zone polygon, machine-state timeline, track/occurrence ground truth and expected HITL outcome required to evaluate the P-047 runtime contract.
- **Choice:** Create a consented custom simulation dataset as the primary US-13 acceptance source. Public datasets may supplement regression or robustness checks but cannot replace the locked final evaluation set.
- **Dataset contract:** Version a manifest and checksums for scenario/video identity, person/track annotations, per-person PPE state, zone, machine state, violation occurrences and expected review outcome. Split by video/scenario into calibration and final evaluation, and never tune against the final split.
- **Privacy/storage constraint:** Use consenting participants and controlled simulated scenes. Do not commit raw media directly until an approved storage/access mechanism exists; version annotations, provenance and immutable media checksums instead.

## 2026-08-08: [Cross-cutting] SH17 in-memory snapshot redaction with person-head fallback
- **Reason:** US-12 requires that a raw review snapshot never reaches storage, while the MVP already includes a SH17 checkpoint that detects identity-adjacent classes and persons.
- **Choice:** Reuse the cached SH17 facade to blur `face`, `face-guard`, `face-mask`, and `head` detections. For every person without one of those detections, blur the upper 40% of that person's box. If there is no usable identity or person region, fail closed: do not create a reviewed event or snapshot. The backend alone sets `privacy_blurred=true` after successful redaction; request values for it and `snapshot_path` are ignored.
- **Constraint:** Decode, inference, blur, and encoding occur in memory before persistence. A database failure removes the newly written redacted file. SH17 privacy behavior is MVP-only; a dedicated face detector with benchmarked false-negative rate and approved license/provenance is required before pilot/production use.

## 2026-08-08: [Cross-cutting] Review and persisted-snapshot boxes are annotated after redaction
- **Reason:** Safety Officers need the reviewed person/PPE-object evidence to remain visible in both the confirmation popup and the JPEG later viewed from event history, without making visual annotation a safety or privacy input.
- **Choice:** The frontend pauses and seeks to the violating inference timestamp, waits for that native video frame to render, captures it at its full source size, then overlays typed `people` and SH17 `detections` with the same aspect-ratio geometry. It sends the stopped-frame JPEG and additive, transient `snapshot_people` and `snapshot_detections` fields when the officer saves. The backend redacts the raw JPEG first, then draws person boxes and non-person SH17 boxes into the redacted JPEG before it is encoded and stored. These fields are excluded from the event row/response; older clients that omit them still save a redacted but unannotated snapshot.
- **Constraint:** Box data never determines violation, redaction candidates, or `privacy_blurred`. SH17 `person` detections are skipped during annotation because rule/inference person boxes are the canonical person box source.
## 2026-08-10: [Vision] Use the dedicated person checkpoint for person detection
- **Supersedes:** The 2026-08-08 choice to use SH17 as the single inference checkpoint for person boxes in the browser frame-inference flow; SH17 remains the PPE/object observation checkpoint and is still used for snapshot privacy redaction.
- **Reason:** The frame-inference service had a dedicated `person_model_path` configuration (`models/yolo11n.pt`) but accidentally defaulted it to the SH17 PPE model path. PPE/object checkpoints can produce false person detections on background objects, so person localization and PPE observation use separate model responsibilities.
- **Choice:** `FrameInferenceService` uses `settings.person_model_path` for `_detect_people()` unless an explicit constructor override is supplied. `PpeVisionFacade` continues to use `settings.ppe_model_path` for SH17 detections and PPE association.
- **Constraint:** This fixes model routing, not model quality. Thresholds and NMS must be benchmarked against labeled factory footage before production alerting.

## 2026-08-13: [Cross-cutting] Cut over PPE to the versioned YOLO11m hat/vest profile
- **Supersedes:** Runtime portions of the 2026-08-06/08 SH17 PPE, three-requirement, all-class display and SH17 privacy decisions. Historical events and those decision entries remain unchanged as audit history.
- **Authorization:** The Product Owner explicitly requested completion of US-28 with `wesjos/Yolo-hard-hat-safety-vest/yolo11m_safety.pt`, authorizing the breaking PPE boundary change.
- **Model choice:** Pin revision `95ffeeb1e0897d60564c811ace5935bcd43d982b` and SHA-256 `f53324f39d76da6017d41038e74f95b3dceb33524738721e03f69f3ea58a1ece`. Validate the checkpoint's five source labels exactly, run only IDs `0`, `3`, `4`, and publish only canonical `person`, `hat`, `vest`. YOLO11n remains the sole canonical person/tracking/zone source; the PPE model's person output only supports association.
- **Contract choice:** Require profile `hat_vest_v1`; replace helmet/glasses/gloves and heuristic shirt fields with `hat_required`, `vest_required`, per-person `hat`/`vest`, and rule keys `missing_ppe:hat`/`missing_ppe:vest`. Reject missing, legacy, unknown-profile and extra PUT fields rather than silently translating a current client.
- **Migration:** Add `hat_required` and `vest_required`, map historical `helmet_required` to `hat_required`, default vest OFF, and retain the legacy columns plus all event/occurrence rows for audit. Old event details are never rewritten.
- **Privacy:** Remove SH17 from privacy. A separate adapter deterministically blurs the upper 40% of every canonical person box in memory, then annotates and persists. Missing candidates or processing errors fail closed. This is a prototype safeguard; a benchmarked dedicated face provider remains a pilot/production gate.
- **Constraint:** Qualified absence remains a deterministic backend inference and requires US-13 calibration/final evaluation before non-demo use. CUDA/device latency and face-redaction recall are not claimed by this cutover.

## 2026-08-13: [Vision] Use YOLO11m Safety as the single runtime detector
- **Supersedes:** The 2026-08-10 dedicated-person-checkpoint decision and the YOLO11n canonical-person constraint in the US-28 cutover decision; both remain as history.
- **Authorization:** The Product Owner explicitly requested removal of YOLO11n from runtime and selected `models/yolo11m_safety.pt` as the sole detector.
- **Choice:** Run source classes `[0, 3, 4]` exactly once per frame. Class `3` supplies canonical person boxes for foot points, zone evaluation, privacy candidates and ByteTrack; classes `0`/`4` supply hat/vest observations associated to those same people.
- **Compatibility:** Preserve current REST/WebSocket/Pydantic/TypeScript fields, class IDs, tracking IDs, occurrence lifecycle, multi-zone behavior, rule semantics and `redact → annotate → persist` ordering. The change is internal model routing, not a wire-contract change.
- **Runtime:** Remove `person_model_path` and do not preload or call `models/yolo11n.pt`. Per-session model instances may exist to isolate ByteTrack state, but every instance uses the same pinned YOLO11m Safety artifact and each frame has one model call.
- **Constraint:** This cutover does not claim improved accuracy. Person/hat/vest precision, recall, association, tracking stability and target-device latency must be re-evaluated through US-13 before pilot/production use.

## 2026-08-14: [Cross-cutting] Confirm missing PPE over time before creating a HITL occurrence
- **Reason:** A single frame can miss a hat or vest because of blur, occlusion, pose, or weak confidence. Creating a candidate for every such frame overwhelms the operator with false/duplicate HITL logs.
- **Choice:** Keep zone intrusion immediate. For `missing_ppe:hat` and `missing_ppe:vest`, the backend waits for continuous absence for `ppe_alert_confirm_seconds` (default `2.0`) on the same session track before opening an occurrence. A later present or unknown observation cancels an unconfirmed candidate. Candidate state follows a nearby track handoff, expires with the monitoring session, and never crosses sessions.
- **Compatibility:** No REST/WebSocket field changes. Responses remain `normal` and have no active PPE violation until confirmation; the frontend logs only backend-confirmed active occurrences.
- **Calibration:** The default is a conservative MVP starting point, not a production accuracy claim. Tune it against the held-out US-13 footage, balancing false alarms against detection delay.

## 2026-08-15: [Cross-cutting] Area-scoped manager accounts and Telegram alert delivery
- **Reason:** An `area_manager` account must identify the monitoring area it owns, and newly confirmed safety occurrences must reach the responsible manager outside the browser.
- **Account contract:** Add nullable `managed_area_id`, `telegram_username` and `telegram_chat_id` fields for backward-compatible historical accounts. New assignments to `area_manager` require an existing saved monitoring area. Telegram username is display identity only; private delivery uses the numeric chat ID.
- **Delivery:** On a newly opened occurrence, backend routing selects active area managers assigned to that area and queues one consolidated Telegram message per recipient/frame. The provider adapter uses Bot API `sendMessage`; an absent token, unlinked recipient or provider failure never interrupts WebSocket inference or removes the in-app alert.
- **Operational constraint:** Configure `TELEGRAM_BOT_TOKEN` outside source control. A private recipient must start the bot first and have the resulting chat ID stored on the account.

## 2026-08-15: [Cross-cutting] Per-zone whole-camera restricted-area alert
- **Reason:** Safety Officers need a simple mode that treats any detected person in a selected camera-zone configuration as an immediate danger alert, without relying on polygon placement or simulated machine state.
- **Choice:** Add the persisted `restricted_area_detection_enabled` switch to the existing camera-zone safety requirement resource, default OFF. When ON, each detected canonical person opens a deduplicated `restricted_area_person` critical occurrence immediately; the frontend presents it as a red Human-in-the-Loop log.
- **Compatibility:** The REST/WebSocket additions are additive. Existing configuration writes may omit the new field and save it as OFF. PPE hat/vest rules and polygon intrusion behavior are unchanged.
