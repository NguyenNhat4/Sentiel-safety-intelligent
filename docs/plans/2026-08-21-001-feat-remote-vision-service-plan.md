# Remote Vision Service — Specification and Implementation Plan

## Objective

Extract YOLO11m Safety inference from the main FastAPI deployment behind a versioned HTTP provider contract. The first deliverable must run locally with CPU dependencies, deploy as a separate RunPod load-balancing worker image, and let the existing backend select the remote provider without changing browser REST/WebSocket payloads.

Success means one JPEG sent through the shared `FrameInferenceService`—from the server-side RTSP camera loop or the compatibility REST/WebSocket path—is evaluated by the remote worker, the backend receives validated person/hat/vest observations, and existing backend rule/occurrence plus camera-metadata responses remain compatible.

## Capability Boundary

| Capability | Owner and layer | Responsibility |
|---|---|---|
| Remote worker API | `backend` API/composition | Validate JPEG input, call the public vision facade, return a versioned observation response |
| Remote provider client | `backend` integration | Authenticate, send binary JPEG, validate the untrusted remote response, adapt it to `SafetyVisionResult` |
| Detection and tracking | `vision` facade | Run YOLO11m Safety and session-scoped ByteTrack; never decide safety rules |
| Safety decisions | `backend` services | Preserve PPE/zone evaluation, debounce, occurrence lifecycle, HITL and persistence |

Dependency direction remains `backend service -> backend integration -> remote worker -> vision facade`. The remote worker has no database, user, event, zone-requirement, snapshot-storage or notification responsibility.

## Public Contract

`GET /ping` returns worker readiness, contract version and model version.

`POST /v1/infer` accepts `multipart/form-data`:

- `request_id`: caller-generated UUID used to correlate the response.
- `monitoring_session_id`: optional UUID/string preserving current session-scoped ByteTrack behavior.
- `image`: one JPEG file.

The response uses contract `safety_vision_v1` and contains:

- echoed `request_id`;
- immutable `model_version`;
- canonical people with `[x, y, width, height]`, confidence and `track_id`;
- per-person `hat`/`vest` observations;
- typed person/hat/vest detection boxes.

Invalid or undecodable JPEG input returns `400`; payloads above 8 MiB return `413`. Missing multipart fields use FastAPI validation. Provider timeouts, non-success responses, malformed JSON, invalid bounding boxes, contract mismatch and request-ID mismatch fail closed as remote-inference errors; the backend never converts them to `normal`.

## Tech Stack and Commands

- Python 3.11, FastAPI, Pydantic v2, HTTPX, OpenCV, Ultralytics and PyTorch.
- Focused tests: run backend files and root `tests/test_settings.py` in separate pytest commands because both test roots define `tests.conftest`.
- Full verification: `make check`.
- Local worker: `make vision-worker-run`.
- Worker image: `make vision-worker-image`.

## Project Structure

- `backend/app/vision_worker.py`: separate FastAPI composition root.
- `backend/app/schemas/remote_vision.py`: versioned remote wire schemas.
- `backend/app/integrations/remote_vision.py`: outbound HTTP adapter.
- `backend/tests/test_vision_worker.py`: inbound worker contract tests.
- `backend/tests/test_remote_vision.py`: outbound adapter tests.
- `Dockerfile.ai` and `requirements.ai.txt`: independently deployable CPU proof image.
- `docs/RUNPOD_VISION_DEPLOYMENT.md`: build, smoke, deploy, configure and rollback runbook.

No new top-level directory, database migration or frontend contract is introduced.

## Code Style

Use typed Pydantic models at both HTTP boundaries and adapt them to the existing `SafetyVisionResult` dictionary only after validation. Provider errors expose stable messages without response bodies, tokens, image bytes or internal exceptions.

## Testing Strategy

1. Worker API contract tests use a fake analyzer and real FastAPI multipart parsing.
2. Remote adapter tests use HTTPX `MockTransport`, real JPEG encoding and Pydantic response validation.
3. Settings tests prove local is the safe default and production remote mode requires URL/token.
4. Existing frame-inference tests prove browser response compatibility.
5. A local Docker smoke sends a generated JPEG through the worker before RunPod deployment.

## Boundaries

- Always preserve current REST/WebSocket and server-camera metadata fields plus backend-owned rule semantics.
- Always keep RunPod credentials server-side and exclude frames/tokens from logs.
- Ask before moving tracker state or enabling multi-worker inference without affinity.
- Never persist raw inference frames in the worker.
- Never make the remote worker read PostgreSQL, S3, users, zones or PPE requirements.

## Tasks

### Task 1 — Remote worker contract

Acceptance:
- Worker exposes `/ping` and `/v1/infer` with typed stable responses.
- One fake-analyzer request round-trips a JPEG and session ID.
- Invalid JPEG fails with `400`.

Verification: focused worker tests pass.

### Task 2 — Backend remote provider adapter

Acceptance:
- Typed settings select `local` by default or `remote` explicitly.
- Adapter sends binary JPEG with bearer authentication and validates all response fields.
- Timeout, provider error and correlation mismatch fail closed.

Verification: focused adapter/settings tests pass.

### Task 3 — Composition and compatibility

Acceptance:
- `FrameInferenceService` selects the configured provider without changing injected-test behavior.
- Existing frame REST/WebSocket output and server-side RTSP camera metadata remain unchanged.
- Local two-command workflow remains on the local provider by default.

Verification: backend frame/WebSocket tests pass.

### Task 4 — Packaging and operations

Acceptance:
- CPU proof worker image builds independently and exposes port 8000.
- Make targets support local run and image build.
- Deployment runbook covers Docker Hub, RunPod Load Balancer, Railway variables, health, smoke and rollback.

Verification: Docker build/smoke when Docker is available; otherwise record the exact environmental blocker.

### Final checkpoint

- Focused tests, lint and formatting pass.
- Full `make check` is run and any pre-existing failure is distinguished from feature failures.
- `DECISIONS.md`, `PROGRESS.md`, `context-map.md` and `docs/PROJECT_STRUCTURE.md` reflect the completed boundary.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| RunPod cold start | First inference is slow or unavailable | Use a load-balancing endpoint and one active worker for realtime operation |
| Worker-local ByteTrack state disappears | Track continuity resets after worker replacement | One worker for the first slice; later use affinity or relocate tracking explicitly |
| Remote API drift/malformed response | Incorrect safety decisions | Strict Pydantic validation, contract version and request correlation |
| Extra JPEG encode/network hop | Increased latency | Binary multipart, one frame in flight; optimize transport only after measurement |
| Remote outage | Monitoring blind spot | Fail closed with inference error; never emit a fabricated `normal` result |

## Not Included

- Browser UI changes.
- Direct RTSP/HLS ingestion inside the remote worker.
- Multi-worker horizontal scaling or affinity.
- CUDA-specific image optimization.
- Moving privacy redaction, business rules, database or events to RunPod.
