# Database Schema — Identity, Organization và Rules

> Chỉ mục: [`README.md`](README.md) · ERD/ownership: [`01-foundations-and-ownership.md`](01-foundations-and-ownership.md)

## 4. Chi tiết bảng

Ký hiệu: `PK` khóa chính, `FK` khóa ngoại, `UQ` unique, `NN` not null.

### 4.1 `users` — owner: auth

| Cột | Kiểu / ràng buộc | Ý nghĩa |
|---|---|---|
| `id` | uuid PK | Actor opaque ID |
| `email` | varchar(320) NN, unique theo lowercase | Login identity |
| `password_hash` | varchar NN | Hash mạnh; không bao giờ trả qua API |
| `display_name` | varchar(160) NN | Tên hiển thị |
| `role` | enum NN | `safety_officer`, `zone_manager` |
| `is_active` | boolean NN default true | Chặn đăng nhập mà vẫn giữ audit |
| `last_login_at` | timestamptz nullable | Audit đăng nhập gần nhất |
| `created_at`, `updated_at`, `deleted_at` | timestamptz | Lifecycle/soft-delete |

Index: unique functional `lower(email)` với user chưa xóa. Không lưu password plaintext hoặc token plaintext.

### 4.2 `auth_sessions` — owner: auth

| Cột | Kiểu / ràng buộc | Ý nghĩa |
|---|---|---|
| `id` | uuid PK | Session ID |
| `user_id` | uuid FK users NN | Chủ session |
| `refresh_token_hash` | varchar NN UQ | Hash token |
| `expires_at` | timestamptz NN | Hạn sử dụng |
| `revoked_at` | timestamptz nullable | Logout/revoke |
| `created_at`, `last_used_at` | timestamptz NN | Audit |

Index `(user_id, expires_at)`; job cleanup có thể xóa session hết hạn sau retention vì event chỉ giữ `actor_user_id`.

### 4.3 `zones` — owner: organization

| Cột | Kiểu / ràng buộc | Ý nghĩa |
|---|---|---|
| `id` | uuid PK | Zone ID |
| `code` | varchar(64) NN UQ | Mã ổn định cho vận hành |
| `name` | varchar(160) NN | Tên khu vực |
| `timezone` | varchar(64) NN | IANA timezone |
| `default_polygon` | jsonb nullable | Mảng ≥3 normalized points, schema validated |
| `is_active` | boolean NN default true | Có cho phiên mới dùng không |
| `created_at`, `updated_at`, `deleted_at` | timestamptz | Soft-delete |

Polygon trong event/session phải lưu snapshot context; đổi polygon mặc định không được viết lại lịch sử.

### 4.4 `shifts` — owner: organization

| Cột | Kiểu / ràng buộc | Ý nghĩa |
|---|---|---|
| `id` | uuid PK | Shift ID |
| `zone_id` | uuid FK zones NN | Zone áp dụng |
| `name` | varchar(120) NN | Ví dụ Ca 1 |
| `start_local_time`, `end_local_time` | time NN | Cho phép ca qua nửa đêm |
| `days_of_week` | smallint[]/json NN | ISO weekday 1–7 |
| `timezone` | varchar(64) NN | IANA timezone tại thời điểm cấu hình |
| `effective_from`, `effective_to` | date | Khoảng hiệu lực |
| `created_at`, `updated_at`, `deleted_at` | timestamptz | Lifecycle |

Service từ chối ca giao nhau trong cùng zone/ngày hiệu lực; validation này cần transaction/locking, không chỉ kiểm tra frontend.

### 4.5 `zone_assignments` — owner: organization

| Cột | Kiểu / ràng buộc | Ý nghĩa |
|---|---|---|
| `id` | uuid PK | Assignment ID |
| `zone_id` | uuid FK zones NN | Scope |
| `user_id` | uuid FK users NN | Người phụ trách |
| `responsibility` | enum NN | `monitor`, `manage`, `escalation_recipient` |
| `valid_from`, `valid_to` | timestamptz | Hiệu lực |
| `created_at`, `updated_at`, `deleted_at` | timestamptz | Lifecycle |

Unique active assignment `(zone_id, user_id, responsibility, valid_from)`; `valid_to > valid_from`.

### 4.6 `safety_rules` — owner: rules

| Cột | Kiểu / ràng buộc | Ý nghĩa |
|---|---|---|
| `id` | uuid PK | Logical rule ID |
| `name` | varchar(160) NN | Tên dễ đọc |
| `scope_zone_id` | uuid FK zones nullable | Null = rule dùng chung theo authorization |
| `active_version_id` | uuid nullable | Trỏ version được confirm; thêm FK deferred sau tạo bảng version |
| `created_by` | uuid FK users NN | Owner |
| `created_at`, `updated_at`, `deleted_at` | timestamptz | Lifecycle |

### 4.7 `safety_rule_versions` — owner: rules

| Cột | Kiểu / ràng buộc | Ý nghĩa |
|---|---|---|
| `id` | uuid PK | Version ID được event tham chiếu |
| `rule_id` | uuid FK safety_rules NN | Logical rule |
| `version` | integer NN | Tăng đơn điệu trong mỗi rule |
| `schema_version` | varchar(16) NN | Version wire schema |
| `definition` | jsonb NN | Conditions, PPE, machine, zone, severity |
| `low_confidence_threshold` | numeric(5,4) NN | `[0,1]` |
| `high_confidence_threshold` | numeric(5,4) NN | `[0,1]`, ≥ low |
| `source_description` | text nullable | Mô tả người dùng; không là source of truth để chạy |
| `generator` | enum NN | `manual`, `llm`, `deterministic` |
| `validation_status` | enum NN | `draft`, `valid`, `rejected` |
| `confirmed_by`, `confirmed_at` | uuid FK users, timestamptz | Người xác nhận |
| `created_at` | timestamptz NN | Version bất biến |

Unique `(rule_id, version)`. Version đã được session/event dùng là immutable; chỉnh sửa tạo row mới.
