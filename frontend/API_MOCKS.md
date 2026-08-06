# Frontend API mocks and integration contracts

This is the handoff contract for the current login-only frontend.

## Mocked API: login

`src/api/auth.ts` uses an in-browser mock; it does not send requests, persist a token, or protect routes.

| Role | Email | Password |
| --- | --- | --- |
| Quản lý an toàn | `antoan@sentinel.local` | `Sentinel123!` |
| Quản lý khu vực | `khuvuc@sentinel.local` | `Sentinel123!` |
| Vận hành mô phỏng | `mophong@sentinel.local` | `Sentinel123!` |

### Required backend endpoint

`POST /api/v1/auth/login`

Request: `{"email":"antoan@sentinel.local","password":"Sentinel123!"}`

Successful `200` response:

```json
{"access_token":"jwt-or-session-token","token_type":"bearer","user":{"id":"user-uuid","full_name":"Nguyễn Anh Tuấn","email":"antoan@sentinel.local","role":"safety_manager","role_label":"Quản lý an toàn"}}
```

Required fields: `access_token`, `token_type` (`bearer`), `user.id`, `user.full_name`, `user.email`, `user.role`, and `user.role_label`. Roles are `safety_manager`, `area_manager`, or `simulation_operator`. Invalid credentials should return `401`; invalid fields should return `422`.

The endpoint is now implemented by the backend. Replace only the body of `login()` with `fetch`; the UI already consumes this contract. A `safety_manager` response opens the existing Live Monitor baseline immediately.

## Mocked API: logout

`src/api/auth.ts` exposes `logout()` as a local resolved Promise. It clears React login state only; no token currently exists in browser storage and no server request is made.

When authentication is implemented, use `POST /api/v1/auth/logout` with the current Bearer token or authenticated session cookie. Return `204 No Content`, revoke the server session/refresh token, then clear local user state. The UI must return to login even if a best-effort server revocation request fails.

## Mocked landing pages and authorization

The success screen currently confirms the role only. The following pages will be added next and require a Bearer token:

| Role | Destination | Extra required fields |
| --- | --- | --- |
| `safety_manager` | Live Monitor and event review | Safety-manager permission |
| `area_manager` | Area dashboard and assigned events | `area_ids: string[]` scope |
| `simulation_operator` | Video-upload streaming simulation | Simulation permission |

`GET /api/v1/auth/me` should return the same `user` object; add `area_ids` for area managers.

## Browser-only streaming simulation

### Current MVP behavior — no request is made

`features/streaming` has no API mock and makes no network call. It previews an operator-selected `File` through a browser object URL and keeps the video on the device. File name/MIME type, duration, playback position, Start/Pause/Stop state, frame rate, and connection state are presentation-only values: none are persisted or sent to a server.

The existing **Live Monitor**, not this page, owns the current backend inference contract: it samples JPEG frames and sends them to `/api/v1/ws/inference` after the operator configures four zone points.

### Proposed backend contract — not implemented

When server-side stream sessions are approved, use an explicit upload/session lifecycle. Do not reuse the inference WebSocket for video-file upload.

#### Create upload-backed stream

`POST /api/v1/streams` with `multipart/form-data`:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `stream_name` | string | Yes | Operator-facing label, 1–120 characters. |
| `source_type` | `uploaded_video` | Yes | Extensible later for `rtsp` and `webrtc`. |
| `video` | video file | Yes | Apply configured size, MIME-type, and duration limits. |
| `zone_id` | string | No | Required only if the backend starts analysis immediately. |

Successful `201` response:

```json
{"id":"stream-uuid","stream_name":"Ca sáng - Máy A","source_type":"uploaded_video","status":"ready","duration_seconds":125.4,"created_at":"2026-08-05T09:00:00Z"}
```

#### Control a stream session

`POST /api/v1/streams/{stream_id}/control`

```json
{"action":"start"}
```

Required request field `action` accepts `start`, `pause`, or `stop`. Return the stream `id`, `status` (`ready`, `streaming`, `paused`, `stopped`, or `failed`), `current_time_seconds`, and `updated_at`. Require an authenticated role with `simulation_operator` or `safety_manager` permission.

Actual camera inputs need a separate security review: an RTSP URL, credentials, and network location must never be returned to an unprivileged browser or recorded in frontend logs.
