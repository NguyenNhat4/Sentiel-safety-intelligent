# Backend Project Progress

## Current State
- Latest status: Backend repo structure & core services fully set up and verified.
- Test status: WebSocket live smoke test and static checks pass; pytest execution currently stalls in the shared `TestClient` fixture on Python 3.14.
- Lint & Format: Passing.

## Completed
- [x] Set up backend directory structure (`app/`, `core/`, `models/`, `schemas/`, `services/`, `api/`, `migrations/`, `tests/`)
- [x] Configured Pydantic typed settings and database session (`config.py`, `database.py`)
- [x] Defined `SafetyEvent` SQLAlchemy model and event status lifecycle
- [x] Built REST API endpoints (`/analysis`, `/events`, `/statistics`)
- [x] Built Realtime Alert WebSocket (`/ws/alerts`)
- [x] Built AI Safety Agent endpoint & recommendation service (`/agent/chat`, `llm_service.py`)
- [x] Created test suite for backend API endpoints
- [x] Updated project `README.md` structure and created `backend/README.md`, `DECISIONS.md`, `PROGRESS.md`
- [x] Added frame inference API, YOLO person detection, safety-shirt baseline rule, and reviewed event persistence
- [x] Added binary WebSocket frame inference with correlated bounding-box and zone-entry results

## In Progress
- [ ] Replace the baseline safety-shirt color heuristic with trained PPE model weights

## Known Issues
- Safety-shirt classification is a color heuristic intended only for a controlled demo.
- Baseline review snapshots are not face-blurred yet; the event records `privacy_blurred=false`.
- The backend pytest suite collects successfully but currently stalls before completing its first `TestClient`-based test in this environment.

## Next Steps
1. Replace the safety-shirt heuristic with a trained PPE model while preserving the frame API contract
2. Implement Alembic initial migration scripts for PostgreSQL production schema
3. Add authentication/authorization middleware for Safety Officers
