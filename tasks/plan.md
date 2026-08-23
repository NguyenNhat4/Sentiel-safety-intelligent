# Implementation Plan: US-29 Direct Media Sessions

## Goal

Replace streaming simulation with backend-owned uploaded image/video assets and
explicit inference sessions for four fixed camera slots.

## Delivered Design

- System Admin owns the media library and may delete only unassigned, unreferenced assets.
- Safety Manager opens camera configuration only by selecting a Live Monitor slot.
- Asset, machine state, zones and PPE save atomically without starting inference.
- Run starts all valid cameras independently; Replay starts one completed video.
- Images infer once without frame debounce; videos stop at EOF and report rolling FPS.
- PostgreSQL stores configuration/session evidence; Railway volume stores media files.
- Streamer, MediaMTX, HLS/RTSP, mappings and Connect/Disconnect are removed.

## Verification Gates

- Repository `make check`.
- Alembic current-head and PostgreSQL migration verification.
- Frontend role/navigation/configuration/Run/Replay tests.
- Railway app deployment reaches `SUCCESS` with media volume mounted.
- Browser smoke proves upload, preview, configuration, inference and HITL event persistence.
