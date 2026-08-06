# API Contract — Danh Mục Endpoint

> Chỉ mục: [`README.md`](README.md) · Quy ước nền: [`01-foundations.md`](01-foundations.md)

## 4. Danh mục endpoint

| Capability / owner | Method và path | Role | Trạng thái | Mục đích |
|---|---|---|---|---|
| Core | `GET /health` | Public | Hiện có | Liveness; không lộ secret |
| Auth | `POST /api/v1/auth/login` | Public | Kế hoạch | Đăng nhập |
| Auth | `POST /api/v1/auth/refresh` | Authenticated | Kế hoạch | Đổi refresh token |
| Auth | `POST /api/v1/auth/logout` | Authenticated | Kế hoạch | Thu hồi session |
| Auth | `GET /api/v1/auth/me` | Authenticated | Kế hoạch | Actor, role và zone scope |
| Monitoring | `POST /api/v1/monitoring/sessions` | Safety Officer | Kế hoạch | Tạo phiên video/ảnh |
| Monitoring | `PATCH /api/v1/monitoring/sessions/{id}` | Safety Officer | Kế hoạch | Cập nhật zone/machine/rule |
| Monitoring | `POST /api/v1/analysis/frame` | Safety Officer | Hiện có | REST inference tương thích |
| Monitoring | `POST /api/v1/analysis/image` | Safety Officer | Kế hoạch | Phân tích ảnh mô phỏng |
| Monitoring | `WS /api/v1/ws/inference` | Safety Officer | Hiện có | Inference gần realtime |
| Rules | `POST /api/v1/rules/preview` | Safety Officer | Kế hoạch | Mô tả → rule preview |
| Rules | `POST /api/v1/rules` | Safety Officer | Kế hoạch | Xác nhận/version rule |
| Rules | `GET /api/v1/rules/{id}` | Scoped user | Kế hoạch | Đọc rule version |
| Events | `POST /api/v1/events` | Safety Officer | Hiện có | Lưu event/review baseline |
| Events | `GET /api/v1/events` | Scoped user | Hiện có | Nhật ký có filter |
| Events | `GET /api/v1/events/{id}` | Scoped user | Hiện có | Event + audit context |
| Events | `POST /api/v1/events/{id}/transitions` | Safety Officer | Kế hoạch | State transition idempotent |
| Events | `GET /api/v1/events/{id}/snapshot` | Scoped user | Kế hoạch | Ảnh đã blur qua access check |
| Analytics | `GET /api/v1/statistics/summary` | Scoped user | Hiện có | Thống kê baseline |
| Analytics | `GET /api/v1/analytics/compliance` | Zone Manager | Kế hoạch | KPI theo zone/shift |
| Analytics | `GET /api/v1/analytics/compliance.csv` | Zone Manager | Kế hoạch | Export cùng filter/KPI |
| Organization | `GET/POST /api/v1/zones` | Zone Manager | Kế hoạch | List/create zone |
| Organization | `GET/PATCH/DELETE /api/v1/zones/{id}` | Zone Manager | Kế hoạch | Detail/update/soft-delete |
| Organization | `GET/POST /api/v1/shifts` | Zone Manager | Kế hoạch | List/create shift |
| Organization | `GET/PATCH/DELETE /api/v1/shifts/{id}` | Zone Manager | Kế hoạch | Detail/update/soft-delete |
| Organization | `GET/POST /api/v1/assignments` | Zone Manager | Kế hoạch | Gán phụ trách zone |
| Escalation | `GET /api/v1/escalations` | Scoped user | Kế hoạch | Delivery queue/history |
| Escalation | `POST /api/v1/escalations/{id}/acknowledge` | Assigned user | Kế hoạch | Xác nhận tiếp nhận |
| Escalation | `POST /api/v1/escalations/{id}/retry` | Safety Officer | Kế hoạch | Retry có giới hạn |
| Reporting | `GET/POST /api/v1/report-schedules` | Zone Manager | Kế hoạch | Lịch báo cáo |
| Reporting | `PATCH/DELETE /api/v1/report-schedules/{id}` | Zone Manager | Kế hoạch | Update/soft-disable |
| Reporting | `GET /api/v1/reports` | Zone Manager | Kế hoạch | Lịch sử report |
| Reporting | `GET /api/v1/reports/{id}/download` | Zone Manager | Kế hoạch | Tải artifact được phép |
