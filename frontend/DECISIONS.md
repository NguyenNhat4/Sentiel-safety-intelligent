# Frontend Design Decisions

## 2026-08-01: Vanilla browser baseline
- **Reason:** The requested single flow does not need a frontend framework or build step.
- **Choice:** The Sentinel monitor HTML and CSS from `src/ui/` live directly in `frontend/`, with a small `baseline.css` layer for video and Canvas behavior.
- **Constraint:** One local video, one four-point zone, one machine toggle, and one pending violation review are supported.

## 2026-08-02: Realtime inference follows video playback
- **Reason:** Playback and inference represent one monitoring action; a separate inference button adds unnecessary state and user steps.
- **Choice:** When four zone points exist, pressing Play starts sampled-frame inference automatically. Stop pauses both playback and inference; zone entry pauses playback and opens human review.
- **Constraint:** Playback without four points is preview-only and does not call the inference API.

## 2026-08-02: Binary WebSocket frame transport
- **Reason:** A persistent connection avoids repeated HTTP setup and binary JPEG avoids Base64 transfer overhead.
- **Choice:** Play opens `/api/v1/ws/inference`, sends four-point configuration once, then sends at most one JPEG frame every 0.5 seconds with only one frame in flight.
- **Constraint:** A socket failure pauses monitored playback; the operator explicitly presses Play to reconnect.
- **Development fallback:** The client tries the page origin first and then `<hostname>:8000`, allowing the static page to run from a local file or development server while FastAPI runs on its documented port.
