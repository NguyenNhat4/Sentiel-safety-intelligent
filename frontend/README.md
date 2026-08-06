# Sentinel React Frontend

React 19 + TypeScript + Vite dashboard for the Safety Officer baseline flow. The application owns local video playback, normalized four-point zone editing, sampled binary WebSocket inference, Canvas overlays, Human-in-the-Loop review, and acknowledged-event history. Detection and polygon evaluation remain backend responsibilities.

Project-wide decisions and progress live only in root [`DECISIONS.md`](../DECISIONS.md) and [`PROGRESS.md`](../PROGRESS.md).

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

1. Select a local video; it remains in the browser.
2. Select exactly four normalized zone points. Points can be dragged, deleted, or reset while paused.
3. Play with four points to open `/api/v1/ws/inference` and send configuration.
4. Send at most one JPEG every 0.5 seconds, with only one frame in flight.
5. Draw returned person boxes and foot points in source-video coordinates.
6. Pause only when `review_required=true`, which means a foot point is inside the zone while the machine is running.
7. Keep the candidate in memory until the Safety Officer confirms it or marks it as a false alarm.
8. Save the review through `POST /api/v1/events`; show only acknowledged events in the violation log.

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
    │   ├── monitor/  # Video, zone, Canvas and inference orchestration
    │   ├── alerts/   # Rule result and Human-in-the-Loop review UI
    │   ├── events/   # Acknowledged violation history
    │   └── dashboard/# Reserved MVP dashboard boundary
    ├── styles/       # React CSS entrypoint
    └── types/        # Typed backend contracts
```

Transport code does not render UI. Canvas utilities do not call the network. Feature state crosses boundaries only through typed props and callbacks.

## Login mock and backend handoff

The current frontend entry point is the login screen for Safety Manager, Area Manager, and Simulation Operator. Its temporary authentication transport and the backend contracts needed to connect it are documented in [API_MOCKS.md](API_MOCKS.md).

## Streaming simulation

The **Mô phỏng streaming** page is frontend-only: it previews a local video and simulates Start, Pause, and Stop. It does not upload a video, create a database record, or open a WebSocket. The current behavior and proposed backend handoff fields are documented in [API_MOCKS.md](API_MOCKS.md#browser-only-streaming-simulation).
