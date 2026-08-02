# Frontend Project Progress

## Current State
- The upload → four-point zone → binary WebSocket inference → violation review → save flow is implemented.
- The page is served by FastAPI at `/` and requires no frontend build step.

## Completed
- [x] Reused the existing Sentinel visual language.
- [x] Added local video playback and normalized four-point zone selection.
- [x] Added sampled-frame inference and Canvas detection overlays.
- [x] Added actual-violation and false-alarm review actions.
- [x] Removed the separate inference button; Play automatically runs realtime inference when the zone has four points.
- [x] Added point selection, drag-to-move, and individual deletion.
- [x] Restricted automatic playback pauses to detections with a person inside the configured zone.
- [x] Replaced per-frame HTTP requests with a configured binary WebSocket running at up to 2 FPS with one frame in flight.
- [x] Added same-origin/port-8000 WebSocket fallback and visualized each detection foot point used for polygon entry.
- [x] Documented the frontend/backend WebSocket protocol and reviewed-event submission flow.
- [x] Refactored the 686-line `app.js` into build-free ES modules with a 29-line composition root.

## Next Steps
1. Replace the demo safety-shirt heuristic with trained PPE detection.
2. Add face blurring before snapshots are persisted.
3. Add an event-history view only after the baseline flow is validated.
