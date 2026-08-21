# Implementation plan: RTSP-first CCTV media gateway

## Outcome

FFmpeg publishes four simulated CCTV sources to MediaMTX. Backend/vision can read
RTSP while React uses HLS by default. MJPEG remains a rollback path until
compatibility and capacity gates pass.

## Locked decisions

- RTSP/TCP + H.264 is the source contract.
- Use exact-version-pinned MediaMTX.
- HLS goes directly from MediaMTX to browser, never through FastAPI.
- WebRTC/WHEP is deferred unless product requires lower latency.
- Preserve backend mapping/RBAC and camera IDs.
- Poll mapping every 15 seconds with jitter for the initial multi-client sync.
- Capacity target is 200 users × up to four players.

## Required context

Read the root context map, progress, decisions, target/current structure,
architecture, streamer/frontend READMEs, executable mapping contracts and tests.
Do not read or modify legacy `src/`. Re-check current official MediaMTX, Hls.js,
Docker and FFmpeg documentation before code. Preserve unrelated dirty changes.

## Slice 0 — baseline and RED tests

1. Record git status and current focused test results.
2. Add RED tests for deterministic RTSP paths and invalid IDs.
3. Add RED publisher tests: reuse, exit, replace, delete and shutdown.
4. Add RED player tests: native/MSE, cleanup, visibility and retry.
5. Add RED mapping test: only the changed camera restarts.

Gate: tests fail for missing behavior, not fixture/setup errors.

## Slice 1 — one real MediaMTX path

1. Add exact-version MediaMTX service/configuration.
2. Publish one approved fixture to `rtsp://mediamtx:8554/cameras/cam_1`.
3. Keep streamer/frontend contracts unchanged.
4. Add smoke proof for readable RTSP, HLS manifest and playable segment.
5. Add meaningful health/readiness without assuming utilities in the base image.

Gate: one real source is readable through RTSP and HLS.

## Slice 2 — four managed publishers

1. Add one managed publisher process per registered camera.
2. Normalize incompatible sources to the locked H.264 profile.
3. Stop/restart safely on replace, delete and shutdown.
4. Add bounded backoff for unexpected exit.
5. Add additive inventory readiness/transport metadata without breaking strings.

Gate: four paths ready; publisher count equals active sources; lifecycle tests and
real process smoke pass.

## Slice 3 — React HLS canary

1. Add npm-pinned `hls.js`.
2. Build focused `HlsVideo` under the monitor feature.
3. Implement native HLS and Hls.js/MSE branches.
4. Implement connection state, destroy/cleanup, retry/backoff/jitter and visibility.
5. Add `VITE_STREAM_TRANSPORT=mjpeg|hls`, rollback-safe during canary.
6. Route only `cam_1` through HLS for the first browser smoke.

Gate: browser inspection proves old requests stop after unmount/source change;
no failed stream remains labelled LIVE.

## Slice 4 — mapping sync and four-camera rollout

1. Poll mapping every 15 seconds with ±20% jitter.
2. Pause while hidden; cancel request/timers on unmount.
3. Recreate only players whose mapping changed.
4. Move all four slots to HLS behind the feature flag.
5. Do not mix unrelated admin/UI refactors into this slice.

Gate: two browser sessions converge within one interval and unaffected players
remain connected.

## Slice 5 — real RTSP inference proof

1. Add a server-side adapter/smoke path reading internal RTSP.
2. Decode/sample outside the async event loop.
3. Preserve current inference/rule/event payloads.
4. Prove one real RTSP source produces real model/rule/alert behavior.

Gate: RTSP → inference → deterministic rule → alert/event passes. HLS playback
does not satisfy this gate.

## Slice 6 — capacity and soak

Run identical scenarios at 1, 10, 25, 50, 100 and 200 users. Test one and four
players/user separately. Capture MediaMTX/FFmpeg/control CPU and RSS, publisher
and session counts, file descriptors, manifest/segment errors, first-frame time,
recovery and egress. Soak ≥30 minutes at 200 × 4, then disconnect everything and
verify resource return.

Gate: publish measured results. Throttled egress or clients that do not actually
download/decode media are failures, not capacity proof.

## Verification categories

Use repository Make targets where present:

```text
focused streamer pytest
focused frontend Vitest
frontend lint, type-check and build
Docker Compose config validation
real RTSP/HLS smoke
browser network/lifecycle verification
git diff --check
make check
```

Backend pytest requires `PYTHONPATH=.`. Keep root/backend suites separate if
fixtures conflict. Do not use unsupported Vitest flags.

## Rollback

1. Set transport to `mjpeg`.
2. Keep mapping rows and IDs unchanged.
3. Stop MediaMTX/new publishers.
4. Run legacy MJPEG smoke.
5. Do not delete new files/data until rollback is verified.

## Definition of done

- All acceptance gates listed in this plan have evidence.
- Four real RTSP paths and four real HLS players work.
- Lifecycle covers publisher and browser cleanup/error paths.
- RTSP inference proof is separate from playback proof.
- 200 × 4 report includes CPU, RSS, egress, errors and latency.
- Architecture, decisions, structure and progress are current.
- `make setup` and `make run` remain sufficient for a new teammate.
- No secrets, floating image tags, fake alerts or fallback videos are added.
