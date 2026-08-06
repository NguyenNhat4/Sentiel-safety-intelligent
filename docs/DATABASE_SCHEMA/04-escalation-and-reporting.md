# Database Schema — Escalation và Reporting

> Chỉ mục: [`README.md`](README.md) · ERD/ownership: [`01-foundations-and-ownership.md`](01-foundations-and-ownership.md)

## 4. Chi tiết bảng — phần tiếp theo

### 4.12 `escalations` — owner: escalation

| Cột | Kiểu / ràng buộc | Ý nghĩa |
|---|---|---|
| `id` | uuid PK | Escalation logic ID |
| `event_id` | uuid FK safety_events NN UQ | Một escalation/event |
| `recipient_user_id` | uuid FK users NN | Người phụ trách tại thời điểm route |
| `channel` | enum NN | `in_app`, `email`, hoặc provider đã chốt |
| `status` | enum NN | pending/delivering/delivered/acknowledged/failed |
| `attempt_count`, `max_attempts` | integer NN | Retry giới hạn |
| `next_retry_at` | timestamptz nullable | Scheduler |
| `acknowledged_by`, `acknowledged_at` | uuid FK users, timestamptz | Tiếp nhận |
| `created_at`, `updated_at` | timestamptz | Lifecycle |

Chỉ event `critical` được auto-create escalation trong scope; rule này do service enforce.

### 4.13 `escalation_deliveries` — owner: escalation

| Cột | Kiểu / ràng buộc | Ý nghĩa |
|---|---|---|
| `id` | uuid PK | Một provider attempt |
| `escalation_id` | uuid FK escalations NN | Parent |
| `attempt_no` | integer NN | Tăng đơn điệu |
| `idempotency_key` | varchar(128) NN UQ | Không gửi trùng |
| `provider` | varchar(64) NN | Adapter name |
| `provider_message_id` | varchar(256) nullable | External opaque ID |
| `status` | enum NN | queued/sent/failed |
| `error_code` | varchar(128) nullable | Sanitize, không secret |
| `started_at`, `completed_at` | timestamptz | Timing |

Unique `(escalation_id, attempt_no)`.

### 4.14 `report_schedules` và `reports` — owner: reporting

`report_schedules`:

| Cột | Kiểu / ràng buộc | Ý nghĩa |
|---|---|---|
| `id` | uuid PK | Schedule |
| `created_by` | uuid FK users NN | Zone Manager |
| `frequency` | enum NN | daily/weekly |
| `timezone` | varchar(64) NN | IANA timezone |
| `zone_scope`, `shift_scope` | jsonb NN | Mảng UUID validated; snapshot cấu hình |
| `recipients` | jsonb NN | Validated recipient objects |
| `format` | enum NN | html/pdf/csv |
| `next_run_at` | timestamptz NN | Scheduler cursor |
| `is_active` | boolean NN | Soft-disable |
| `created_at`, `updated_at`, `deleted_at` | timestamptz | Lifecycle |

`reports`:

| Cột | Kiểu / ràng buộc | Ý nghĩa |
|---|---|---|
| `id` | uuid PK | Report instance |
| `schedule_id` | uuid FK report_schedules NN | Source schedule |
| `period_start`, `period_end` | timestamptz NN | Kỳ báo cáo |
| `status` | enum NN | pending/rendered/failed |
| `aggregation_snapshot` | jsonb NN | KPI + source references bất biến |
| `narrative_text`, `narrative_generator` | text/enum nullable | LLM/fallback dẫn xuất |
| `artifact_storage_key` | varchar(512) nullable | Object đã render |
| `artifact_sha256` | char(64) nullable | Integrity |
| `generated_at`, `created_at` | timestamptz | Timing |

Unique `(schedule_id, period_start, period_end)` để job idempotent.

### 4.15 `report_deliveries` — owner: reporting

| Cột | Kiểu / ràng buộc | Ý nghĩa |
|---|---|---|
| `id` | uuid PK | Delivery attempt |
| `report_id` | uuid FK reports NN | Report |
| `recipient` | varchar(320) NN | Email/user opaque recipient |
| `channel` | enum NN | Provider channel |
| `attempt_no` | integer NN | Retry number |
| `idempotency_key` | varchar(128) NN UQ | Chống gửi trùng |
| `status`, `error_code` | enum/varchar | Delivery result |
| `created_at`, `completed_at` | timestamptz | Timing |
