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

When the endpoint exists, replace only the body of `login()` with `fetch`; the UI already consumes this contract. A `safety_manager` response now opens the existing Live Monitor baseline immediately. Token persistence/refresh, logout, password reset, and route authorization are not mocked.

## Mocked landing pages and authorization

The success screen currently confirms the role only. The following pages will be added next and require a Bearer token:

| Role | Destination | Extra required fields |
| --- | --- | --- |
| `safety_manager` | Live Monitor and event review | Safety-manager permission |
| `area_manager` | Area dashboard and assigned events | `area_ids: string[]` scope |
| `simulation_operator` | Video-upload streaming simulation | Simulation permission |

`GET /api/v1/auth/me` should return the same `user` object; add `area_ids` for area managers.
