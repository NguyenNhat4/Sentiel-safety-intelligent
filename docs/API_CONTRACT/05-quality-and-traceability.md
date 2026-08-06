# API Contract — Chất Lượng và Truy Vết

> Chỉ mục: [`README.md`](README.md) · Nền tảng versioning: [`01-foundations.md`](01-foundations.md)

## 6. Compatibility, test và Definition of Done

Một thay đổi contract chỉ Done khi:

1. Owner capability và consumer review schema; story → module → contract → test được ghi rõ.
2. OpenAPI/JSON Schema, fixture và generated frontend types đồng bộ.
3. Có happy path, validation, auth matrix, idempotency, conflict và privacy failure tests.
4. Timestamp/correlation ID được giữ xuyên luồng; không log token/raw image/PII chưa blur.
5. Route hiện có không bị breaking; nếu buộc breaking, phát hành version mới và ghi migration/deprecation window.
6. WebSocket test bao phủ message order, binary size/type, reconnect và một-frame-in-flight.
7. Event test bao phủ dedup, mọi transition hợp lệ/không hợp lệ, false alarm và snapshot cleanup.

## 7. Traceability

| Contract | Story |
|---|---|
| Monitoring + inference | US-01–US-04, US-07, US-08, US-13, US-24 |
| Rules | US-11, US-15 |
| Event/HITL/privacy/audit | US-05, US-06, US-09, US-12, US-16, US-17 |
| Auth/RBAC | US-20 |
| Organization | US-21 |
| Analytics | US-10, US-22 |
| Escalation | US-14 |
| Reporting | US-23 |
| Operations/release | US-18, US-19, US-25, US-26 |
