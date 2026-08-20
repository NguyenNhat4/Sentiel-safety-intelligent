# Implementation Plan: US-29 Demo Day multi-camera streams

## Overview

Replace the current single active-camera contract with a persisted mapping for
up to four named display cameras. Sys Admin selects registered streamer sources,
Live Monitor renders a 2×2 grid, and disconnect removes only the selected
mapping. The existing real stream transport remains the source of frames; this
change does not invent alerts or claim inference integration before it exists.

## Architecture decisions

- Backend owns the persisted mapping and RBAC; streamer owns media files and
  transport only.
- A mapping is `{camera_id, stream_camera_id}`. `stream_camera_id` must be
  unique across the saved mapping and at most four display cameras are allowed.
- Keep the existing `stream_configuration` table name and migrate its singleton
  row from `active_camera_id` to a JSON mapping column for a minimal reversible
  transition. The API exposes only the new mapping contract. The pre-existing
  duplicate Alembic revision is repaired before the new migration is added.
- Streamer camera IDs are selectable sources; display camera IDs are stable
  `cam_1` through `cam_4` with friendly labels in the frontend.
- A missing mapping is an explicit empty state. There is no fallback video.

## Dependency graph

```text
migration/model → schemas/service/API → frontend API/types → admin + monitor UI
                                      ↘ focused backend/frontend tests
```

## Task list

### Phase 1: Contract and persistence

- [x] T1. Add migration/model support for four persisted mappings, including
  legacy singleton migration and downgrade.
- [x] T2. Implement GET/PUT/DELETE contracts, max-four validation, unique
  source validation, admin-only mutation and backward-compatible empty state.
- [ ] T3. Add backend regression coverage for persistence, duplicate source,
  max count, role enforcement, partial disconnect and legacy data.

### Checkpoint 1

- [ ] Focused backend stream tests pass.
- [ ] Alembic upgrade/downgrade and SQLite test metadata remain valid.

### Phase 2: Demo UI

- [x] T4. Replace single-camera frontend types/API with the mapping contract.
- [x] T5. Build the admin configuration tab with four display-camera cards,
  source selectors, connect/disconnect, loading/error/status states.
- [x] T6. Build Live Monitor's 2×2 camera grid with disconnected/error states;
  preserve existing monitor controls and alert surfaces.
- [x] T7. Add focused frontend tests for mapping, duplicate source display,
  disconnect and four-card rendering.

### Checkpoint 2

- [ ] Frontend test, type-check, lint and production build pass.
- [ ] Manual local flow: admin maps four sources, Safety Officer reloads Live
  Monitor, then admin disconnects one source without affecting the other three.

### Phase 3: Runtime and release readiness

- [x] T8. Update streamer/backend/frontend runtime docs and deployment
  configuration for public streamer URL and four-source assets.
- [ ] T9. Run the repository's full checks and local runtime smoke test.
- [ ] T10. Deploy/redeploy the separate streamer service, configure its media
  and public URL, redeploy app/backend, then prove health, persistence and the
  four-camera smoke flow in the deployed environment.

## Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Existing single-camera data | High | Explicit migration and legacy regression test |
| MJPEG is not yet connected to inference | High | Do not claim end-to-end detection until a frame adapter exists; track as a separate gate |
| Four FFmpeg readers consume too much CPU | Medium | Use prepared low-resolution assets and measure local/staging resource usage |
| Streamer public CORS/URL mismatch | High | Configure `VITE_STREAMER_URL`, verify `/health` and `/api/cameras` from deployed frontend origin |
| Stream disappears while mapped | Medium | Render `ERROR`, stop stale frame use, retain mapping until explicit disconnect unless product changes it |

## Deployment answer

Yes. Local Compose is needed for implementation verification, but Demo Day
requires a separate deployed streamer service containing the prepared media,
plus a public `VITE_STREAMER_URL` in the frontend build. The application/backend
must be redeployed with the multi-camera migration and API. Deployment is not
proof until `/health`, mapping persistence, access control, four streams and
disconnect are smoke-tested against the deployed services.
