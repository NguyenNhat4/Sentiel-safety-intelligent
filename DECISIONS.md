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

