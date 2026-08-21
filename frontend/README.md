# Sentinel React Frontend

React 19 + TypeScript + Vite dashboard for the Safety Officer baseline flow. The application owns the admin-selected HLS camera viewer with MJPEG rollback, normalized four-point zone editing, sampled binary WebSocket inference compatibility, Canvas overlays, Human-in-the-Loop review, and acknowledged-event history. Local video upload is removed; RTSP server-side inference remains a separate runtime gate from HLS playback.

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

1. Load the versioned `hat_vest_v1` default-OFF requirements for `uploaded_video` and `zone_01`; edits remain draft until **Lưu cấu hình** succeeds.
2. Select a local video; it remains in the browser.
3. Select up to four normalized zone points. Points can be dragged, deleted, or reset while paused; only four points activate zone evaluation.
4. Play to open `/api/v1/ws/inference` and receive detections regardless of zone state.
5. Send at most one JPEG every 0.5 seconds, with only one frame in flight.
6. Draw returned canonical person boxes, foot points, and YOLO11m Safety detections `hat`/`vest` in source-video coordinates; only `person`, `hat`, `vest` exist in the new detection contract.
7. Pause only when `review_required=true`, seek back to that inference result's `video_time`, wait for the browser to render it, then capture the full native video frame for review.
8. Keep that stopped-frame candidate and its detection coordinates in memory until the Safety Officer confirms it or marks it as a false alarm.
9. Save the review through `POST /api/v1/events`; show only acknowledged events in the violation log.

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
