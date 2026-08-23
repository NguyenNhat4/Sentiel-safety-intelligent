# Sentinel React Frontend

React 19 + TypeScript + Vite dashboard for the safety workflow. Live Monitor always renders four logical cameras with backend-owned image/video assets, session-correlated overlays, inference FPS and Replay at video EOF. **Cấu hình camera** is not a sidebar tab: Safety Manager opens the exact camera only by selecting a Live Monitor slot. System Admin owns the separate media library.

Project-wide decisions and progress are maintained centrally at repository root.

## Development

Run FastAPI in one terminal and Vite in another:

```bash
make frontend-install
.venv/bin/uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
make frontend-dev
```

Open <http://localhost:5173>. Vite proxies `/api` and `/snapshots` to port 8000, including the inference WebSocket. Set `VITE_BACKEND_URL` only when the backend is hosted at another origin.

For the integrated production-style runtime:

```bash
make run
```

`make run` builds `frontend/dist` and FastAPI serves it at <http://localhost:8000>. The Docker image uses the same single-service model with a Node build stage and a Python runtime stage.

## Checks

```bash
npm --prefix frontend run lint
npm --prefix frontend run type-check
npm --prefix frontend run test
npm --prefix frontend run build
```

The tests cover URL resolution, WebSocket configuration/backpressure, Canvas coordinates, review payloads, navigation, machine state, and review actions.

## Runtime Flow

1. System Admin uploads a named image/video directly to the configured Railway Bucket
   through a presigned request; only backend-validated `READY` assets are selectable.
2. Safety Manager selects a Live Monitor slot, previews its asset, edits normalized zones and PPE, then saves one atomic draft.
3. Save returns to Live Monitor and does not start inference.
4. **Chạy mô phỏng** starts fresh server-owned sessions for valid cameras; Replay starts one completed video again.
5. `/api/v1/ws/camera-detections` carries lifecycle, session ID, source time, rolling inference FPS and detections.
6. The UI ignores stale session output and draws canonical person/hat/vest observations in source coordinates.
7. Run creates fresh sessions for every valid configured camera. Replay creates one
   fresh session for only the selected camera and remounts playback at the beginning.

## Source Boundaries

```text
frontend/
├── index.html
├── package.json
├── vite.config.ts
├── styles.css
├── baseline.css
├── event-log.css
└── src/
    ├── api/          # REST and WebSocket transport only
    ├── components/   # Shared application shell
    ├── features/
    │   ├── auth/     # Login and system-admin account/role/security tabs
    │   ├── area/     # Area-manager dashboard using statistics and event APIs
    │   ├── monitor/  # Video, zone, Canvas and inference orchestration
    │   ├── alerts/   # Rule result and Human-in-the-Loop review UI
    │   ├── events/   # Acknowledged violation history
    │   ├── rules/    # Persisted PPE requirement controls and draft/save state
    │   └── dashboard/# Reserved legacy boundary; active dashboard is owned by area/
    ├── styles/       # React CSS entrypoint
    └── types/        # Typed backend contracts
```

Transport code does not render UI. Canvas utilities do not call the network. Feature state crosses boundaries only through typed props and callbacks.

## Authentication

The login screen calls `POST /api/v1/auth/login`, stores the returned bearer token only in browser `sessionStorage`, restores a tab session through `GET /api/v1/auth/me`, and revokes it through `POST /api/v1/auth/logout`. Local/demo builds show the three seeded demo accounts with copy and one-click fill shortcuts; these credentials must not be used outside local/demo environments. A `system_admin` retains the safety monitor/event workspace, sees account-management navigation, and has a separate **Camera stream** sidebar entry directly below **Quản trị hệ thống**. An `area_manager` lands on the dedicated area dashboard. New and administrator-reset accounts must replace their temporary password before entering a role workspace.
