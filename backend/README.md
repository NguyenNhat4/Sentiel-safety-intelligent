# Backend Module - PPE & Zone Safety Monitoring System

## Overview
Phân hệ `backend` là FastAPI web application theo kiến trúc Modular Monolith. Phân hệ đảm nhận vai trò API Gateway, quản lý trạng thái phiên phân tích video, ghi nhận và xử lý các sự kiện vi phạm quy định an toàn (PPE & xâm nhập vùng nguy hiểm), đẩy cảnh báo thời gian thực qua WebSocket, và cung cấp AI Safety Agent tư vấn xử lý sự cố.


## Setup & Running
```bash
# From the repository root
make run

# Run backend test suite
PYTHONPATH=. .venv/bin/pytest backend/tests -v
```

REST routes are interactive at <http://localhost:8000/docs>. The inference WebSocket at `ws://localhost:8000/api/v1/ws/inference` is intentionally absent from Swagger because WebSocket operations are not part of the generated OpenAPI schema.

Operational monitoring is deliberately lightweight: one process writes rotated, privacy-safe JSONL events to `data/operational-metrics.jsonl`; `GET /api/v1/operational-metrics?window_minutes=60` returns bounded request latency, inference outcomes, and stable error-kind aggregates. The stream never contains frames, snapshots, IDs, raw URLs/query strings, credentials, addresses, or exception text. This file-backed writer is single-process only; use a centralized sink before enabling multiple backend workers.

PostgreSQL from `DATABASE_URL` is the primary database. If it is unreachable during process startup and `DATABASE_FALLBACK_ENABLED=true`, the backend uses `DATABASE_FALLBACK_URL` (local SQLite by default), creates the schema, and seeds development accounts when the database is empty. The selected database remains fixed until restart and is exposed by `/health`. SQLite fallback data is local and is not automatically synchronized back to PostgreSQL, so production deployments that require strict consistency should disable fallback. Supabase is optional; any standard managed PostgreSQL service is sufficient. Snapshots are redacted in memory before writing; if privacy processing or database persistence fails, the backend does not create the event and removes any unreferenced redacted snapshot.

PostgreSQL uses a bounded LIFO connection pool with TCP keepalive and five-minute connection recycling. `DATABASE_POOL_PRE_PING` defaults to `false` so a warm connection checkout does not add a database round-trip to every request. Enable it only for a provider that repeatedly drops idle sessions. ORM sessions keep loaded values after commit, avoiding an automatic response-time reload; explicit queries remain the source of truth for subsequent requests.

## Frontend–Backend Interaction

The baseline uses two transports with separate responsibilities:

- WebSocket `/api/v1/ws/inference` carries either the legacy one-zone configuration or a saved multi-zone collection, sampled JPEG frames, and additive per-zone inference results.
- REST `/api/v1/events` persists a legacy reviewed outcome; `/api/v1/event-batches` atomically persists grouped zone reviews.

Reviewed-event and statistics endpoints require a logged-in user. Safety officers and system administrators can record reviews; an area manager receives only events and statistics for their assigned `managed_area_id`. A Telegram alert is queued for that matching manager only when a review is saved as `acknowledged`, never when the AI merely opens a candidate.

US-27 persists the operator's zone collection through `GET/PUT /api/v1/cameras/{camera_id}/monitoring-zones`. Saves use `expected_revision`, reject stale writes, and atomically reject intersecting, touching or containing active polygons. Multi-zone configure must echo that saved revision; PPE requirements continue to use the unchanged `uploaded_video/zone_01` resource.

The versioned `hat_vest_v1` profile uses a shared persisted PPE requirement resource for the fixed MVP camera–zone pair:

```http
GET /api/v1/ppe-requirements/{camera_id}/{zone_id}
PUT /api/v1/ppe-requirements/{camera_id}/{zone_id}
```

GET returns `profile`, `hat_required`, `vest_required`, and additive `restricted_area_detection_enabled`; a missing record materializes as all OFF values with `is_configured=false`. PUT accepts the same additive boolean (omitting it keeps compatibility and saves OFF). When the per-zone restricted-area switch is ON, every detected canonical person anywhere in the camera frame opens an immediate critical `restricted_area_person` occurrence, independent of polygon geometry and machine state. The PPE adapter invokes `yolo11m_safety.pt` once per frame and the public detection contract accepts only `person`, `hat`, `vest`. Backend derives `missing` only when a canonical person meets the confidence/association guard and has no associated required PPE detection.

US-08 adds a client-generated `monitoring_session_id` that remains stable for one selected video across pause, review, and reconnect. Each person has a session-local `track_id` and `active_violations`; only a newly opened occurrence sets `review_required=true`. Reviewed event requests carry the new occurrence IDs, and the database unique constraint makes retries idempotent while conflicting reuse returns `409`.

```mermaid
sequenceDiagram
    actor Officer as Safety Officer
    participant UI as Browser Frontend
    participant WS as /api/v1/ws/inference
    participant CV as FrameInferenceService
    participant Events as /api/v1/events
    participant DB as PostgreSQL

    Officer->>UI: Draw 4-point zone and press Play
    UI->>WS: configure(zone_points, machine_state)
    WS-->>UI: configured
    loop At most 2 sampled frames/second
        UI->>WS: frame_meta(frame_id, video_time)
        UI->>WS: binary JPEG
        WS->>CV: infer(frame, zone, machine state)
        CV-->>WS: boxes, foot points, inside_zone
        WS-->>UI: inference_result
    end
    alt Person foot point enters zone
        UI->>UI: Pause at result.video_time
        Officer->>UI: Confirm actual violation
        UI->>Events: POST reviewed event + snapshot
        Events->>DB: Save warning
        Events-->>UI: 201 + event ID
    else No person or person outside zone
        UI->>UI: Continue playback
    end
```

## Frame Inference Contract

This section is the canonical protocol specification. It includes the message sequence, complete input/output examples, field semantics, decision formula, common outcomes, and error behavior.

### WebSocket endpoint

```text
ws://localhost:8000/api/v1/ws/inference
```

This endpoint answers: **where are the people/hat/vest objects in this frame, and is any person's foot inside the configured danger zone while the machine is running?** One YOLO11m Safety call selects source classes `[0, 3, 4]`: class `3` supplies canonical people for foot points and ByteTrack, while `hat`/`vest` feed PPE observations. It uses a stateful WebSocket protocol rather than one HTTP request, so it does not appear in Swagger/OpenAPI.

### Input sequence

#### 1. Configure once per connection

Send four normalized points to activate zone evaluation, or an empty list to run detection without a zone, together with the current machine state:

```json
{
  "type": "configure",
  "monitoring_session_id": "3cddfe85-9428-44d7-afbf-0cd9e5fc0640",
  "zone_points": [
    {"x": 0.12, "y": 0.30},
    {"x": 0.72, "y": 0.28},
    {"x": 0.81, "y": 0.88},
    {"x": 0.09, "y": 0.91}
  ],
  "machine_state": "running"
}
```

`x` and `y` are normalized to the source frame and must be between `0` and `1`. The backend responds with:

```json
{"type": "configured", "monitoring_session_id": "3cddfe85-9428-44d7-afbf-0cd9e5fc0640"}
```

Send `configure` again when the machine state or zone changes.

#### 2. Send metadata for one frame

```json
{
  "type": "frame_meta",
  "frame_id": 15,
  "video_time": 7.5
}
```

- `frame_id` is a non-negative client sequence number used to correlate and reject stale results.
- `video_time` is the frame position in the source video, in seconds.

#### 3. Send the frame

Immediately after `frame_meta`, send the corresponding JPEG as a **binary WebSocket message**. It is not JSON or Base64 during transfer. Only one frame may be pending on a connection.

### Output: `inference_result`

The backend returns one correlated JSON result for each accepted JPEG:

```json
{
  "type": "inference_result",
  "frame_id": 15,
  "video_time": 7.5,
  "result": "violate",
  "review_required": true,
  "people": [
    {
      "track_id": 7,
      "bbox": [420, 115, 535, 610],
      "confidence": 0.91,
      "foot_point": [477, 610],
      "inside_zone": true,
      "ppe": {
        "hat": {"status": "missing", "confidence": null},
        "vest": {"status": "present", "confidence": 0.88}
      },
      "missing_required_ppe": ["hat"]
    }
  ],
  "detections": [
    {"class_id": 3, "class_name": "person", "bbox": [420, 115, 535, 610], "confidence": 0.91, "person_index": 0},
    {"class_id": 4, "class_name": "vest", "bbox": [438, 250, 520, 510], "confidence": 0.88, "person_index": 0}
  ],
  "snapshot_data": "data:image/jpeg;base64,...",
  "rule": {
    "person_inside_zone": true,
    "machine_state": "running",
    "ppe_profile": "hat_vest_v1",
    "camera_id": "uploaded_video",
    "zone_id": "zone_01",
    "ppe_requirements": {
      "profile": "hat_vest_v1",
      "hat_required": true,
      "vest_required": true
    },
    "ppe_alert": false
  }
}
```

| Field | Meaning |
|---|---|
| `frame_id`, `video_time` | Copied from `frame_meta` so the frontend can match the result to the analyzed frame. |
| `people` | Every person detected by YOLO; an empty array means no person was detected. |
| `detections` | Typed list limited to canonical `person` plus YOLO11m Safety `hat`/`vest`: class ID/name, original-frame `bbox`, confidence and nullable `person_index`. It can contain unassociated PPE when `people` is empty. |
| `track_id` | ByteTrack association ID scoped to one monitoring session; it is not a personal identity. |
| `active_violations` | Per-track rule occurrences. Only `is_new=true` opens a new review candidate. |
| `bbox` | Person rectangle in original-frame pixels as `[x1, y1, x2, y2]`. |
| `confidence` | YOLO's confidence that the detection is a person. |
| `foot_point` | Bottom-center of `bbox`, in original-frame pixels; this is the point used for polygon evaluation. |
| `inside_zone` | `true` when `foot_point` is inside or on the polygon boundary. |
| `ppe`, `missing_required_ppe` | Per-person `hat`/`vest` observations and only the currently required items that passed qualified-absence guards. |
| `review_required` | `true` when the machine is running and at least one foot point is inside, or when a required PPE is `missing` for a qualified person. The frontend pauses only for this value. |
| `result` | `violate` when `review_required=true`; otherwise `normal`. |
| `snapshot_data` | The analyzed JPEG as a Base64 data URL, included only when review is required. It is not persisted until officer confirmation. |
| `rule` | Decision inputs included for debugging and audit context, including the persisted PPE requirements active for this frame and whether an explicit missing-PPE alert fired. |

The current decision is:

```text
person_inside_zone = any(person.inside_zone for person in people)
ppe_alert = any(person.missing_required_ppe for person in people)
review_required = (person_inside_zone AND machine_state == "running") OR ppe_alert
result = "violate" if review_required else "normal"
```

Common outcomes:

| Detection | Machine | `inside_zone` | `result` | `review_required` | Snapshot |
|---|---|---:|---|---:|---:|
| No person | Running or stopped | — | `normal` | `false` | No |
| Person outside zone | Running or stopped | `false` | `normal` | `false` | No |
| Person inside zone | Stopped | `true` | `normal` | `false` | No |
| Person inside zone | Running | `true` | `violate` | `true` | Yes |

Bounding boxes and `inside_zone` remain available when the machine is stopped; zone-driven review, video pause, and snapshot generation are suppressed. A qualified required-PPE absence still requests review.

### Protocol errors

Invalid ordering, validation, JPEG, or inference failures return:

```json
{
  "type": "error",
  "code": "invalid_frame",
  "message": "image_data could not be decoded as an image"
}
```

The server processes messages sequentially. The frontend additionally enforces one frame in flight, which prevents model overload and stale queues.

### Detection and zone evaluation

YOLO returns a person bounding box `[x1, y1, x2, y2]`. The service represents the person's ground position as the bottom-center point:

```text
foot_x = (x1 + x2) / 2
foot_y = y2
```

The four normalized zone points are converted to frame pixels. OpenCV `pointPolygonTest` sets `inside_zone=true` when the foot point is on or inside the polygon. Zone review is based on this foot point, not bounding-box overlap. A review, snapshot, and violation are produced only when the foot point is inside while `machine_state` is `running`; bounding boxes remain available while the machine is stopped.

The REST fallback `POST /api/v1/analysis/frame` remains available and returns the same core `FrameInferenceResponse` without WebSocket correlation fields.

## Reviewed Warning Persistence

### Current baseline

The browser holds an unpersisted `pendingViolation` after zone entry. Only after the officer chooses a review action does it call:

```http
POST /api/v1/events
Content-Type: application/json
```

Example confirmed violation:

```json
{
  "zone_id": "zone_01",
  "camera_id": "uploaded_video",
  "event_type": "missing_ppe_and_intrusion",
  "severity": "high",
  "status": "acknowledged",
  "acknowledged_by": "Safety Officer",
  "snapshot_data": "data:image/jpeg;base64,...",
  "details": {
    "inference_result": "violate",
    "review_result": "actual_violation",
    "machine_state": "running",
    "video_timestamp_seconds": 12.5,
    "people": [],
    "zone_points": []
  }
}
```

`EventService` validates and decodes `snapshot_data`, then calls the privacy adapter independently from PPE inference. It accepts transient `snapshot_people` and `snapshot_detections` from the reviewed frame, redacts first, and only then draws canonical person plus `hat`/`vest` boxes before JPEG encoding; these fields are excluded from event persistence/response. It writes only the processed JPEG under `data/snapshots`, sets `privacy_blurred=true` itself, then commits the event. Client-provided privacy/path values cannot bypass this gate.

The prototype privacy policy blurs the top 40% of every canonical person box. If no valid person region exists or any redaction/annotation/encoding step fails, processing is fail-closed: no snapshot and no reviewed event are created. This policy does not load the retired SH17 checkpoint or add privacy classes to the PPE contract.

The baseline also persists `false_alarm` using the same endpoint so model quality can be evaluated.

For current per-person reviews, `POST /api/v1/events` includes the session-local `track_id` and uses `(monitoring_session_id, track_id)` as the log identity. A person's missing-hat, missing-vest, restricted-area and zone-intrusion occurrences are accumulated into that single `person_safety_violation` event for the video session; this is tracking, not biometric identity.

### Recommended production design

Use a two-level record model:

1. Keep detections transient until review, identified by a generated `detection_id`. Do not create an official warning merely because the model fired.
2. On `acknowledged`, create the immutable safety warning, derive `acknowledged_by` from the authenticated officer, blur faces before storage, and persist the snapshot plus inference metadata in one controlled operation.
3. On `false_alarm`, write a lightweight review-audit/feedback record for model metrics, but do not create a safety warning or retain the unblurred snapshot unless policy explicitly requires it.
4. Require `detection_id` as an idempotency key so reconnects or repeated clicks cannot create duplicate warnings.
5. Store production snapshots in protected object storage and keep only the object key, checksum, privacy status, and retention deadline in PostgreSQL.

Recommended confirmed-warning lifecycle:

```text
detected in memory
    → officer acknowledged
    → validate detection_id
    → privacy blur snapshot
    → persist snapshot
    → insert immutable warning + review audit
    → return event ID
```

```mermaid
stateDiagram-v2
    [*] --> Candidate: foot point enters polygon
    Candidate --> Confirmed: officer acknowledges
    Candidate --> FalseAlarm: officer rejects
    Confirmed --> PrivacyProcessing: blur and validate snapshot
    PrivacyProcessing --> WarningPersisted: snapshot and DB record durable
    PrivacyProcessing --> Candidate: persistence failed, allow retry
    FalseAlarm --> ReviewAudit: save feedback without official warning
    WarningPersisted --> [*]
    ReviewAudit --> [*]
```

If snapshot persistence or the database transaction fails, return an error and keep the frontend review pending so the officer can retry. Do not report a saved warning until both the event metadata and protected snapshot reference are durable.
