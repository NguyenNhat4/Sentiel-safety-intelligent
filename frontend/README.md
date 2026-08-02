# Frontend baseline

This module contains the single-page HTML/CSS/JavaScript safety review demo. FastAPI serves it at `/`; no frontend build step is required. The main monitor HTML and `styles.css` were brought over from `src/ui/`; `baseline.css` adds only the functional video and Canvas states.

The page selects a local video, captures four movable normalized zone points, and sends binary JPEG samples over `/api/v1/ws/inference` while video playback is running. There is no separate inference button. Only one frame is in flight at a time, and zone entry pauses playback for operator review and event persistence.
