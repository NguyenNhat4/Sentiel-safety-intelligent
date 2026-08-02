# Project Progress

This is the single progress tracker for the repository. Completed work is grouped by area; current state, known issues, and next steps are project-wide.

## Current State
- The baseline upload → four-point zone → binary WebSocket inference → foot-point zone review → event save flow is implemented.
- FastAPI serves the build-free frontend at `/` and provides REST plus WebSocket APIs.
- Frontend logic is split into native ES modules with a 29-line composition root.
- Static checks, formatting, WebSocket live smoke tests, ES module linking, and headless-browser loading pass.

## Completed

### Backend
- [x] Established the FastAPI modular monolith, typed settings, SQLAlchemy database layer, REST APIs, and test scaffolding.
- [x] Added safety-event lifecycle, reviewed snapshot persistence, statistics, and Safety Agent endpoints.
- [x] Added YOLO person detection, foot-point polygon evaluation, safety-shirt baseline rule, and REST frame inference.
- [x] Added binary WebSocket inference with configuration, correlation metadata, one-frame processing, validation, and structured errors.
- [x] Documented frontend/backend interaction and the recommended confirmed-warning persistence lifecycle.

### Frontend
- [x] Added local video playback, normalized four-point zone editing, Canvas overlays, and foot-point visualization.
- [x] Added 2 FPS WebSocket inference with one frame in flight and same-origin/port-8000 fallback.
- [x] Pause playback only when a returned person foot point is inside the configured polygon.
- [x] Added actual-violation and false-alarm review actions with REST event persistence.
- [x] Refactored the 686-line `app.js` into build-free ES modules with a 29-line composition root.
- [x] Restored Play-button activation immediately after video metadata loads.

### Documentation
- [x] Documented current/future project structure, WebSocket contracts, runtime diagrams, and review persistence recommendations.
- [x] Consolidated module tracking into central root `DECISIONS.md` and `PROGRESS.md` files.

## In Progress
- [ ] Replace the controlled-demo safety-shirt color heuristic with trained PPE model weights.

## Known Issues
- The safety-shirt classifier is a color heuristic and is not production PPE detection.
- Review snapshots are not face-blurred yet and currently record `privacy_blurred=false`.
- The pytest suite collects successfully but stalls in the shared `TestClient` flow on the current Python 3.14 environment; focused non-`TestClient` checks and live smoke tests pass.

## Next Steps
1. Replace the safety-shirt heuristic while preserving the inference response contract.
2. Blur faces before any confirmed snapshot is persisted.
3. Implement the PostgreSQL Alembic migration and authenticated Safety Officer identity.
4. Add event history only after the baseline monitoring flow is validated.
