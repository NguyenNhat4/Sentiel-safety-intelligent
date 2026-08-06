# Database Schema — Monitoring, Events và Snapshots

> Chỉ mục: [`README.md`](README.md) · ERD/ownership: [`01-foundations-and-ownership.md`](01-foundations-and-ownership.md)

## 4. Chi tiết bảng — phần tiếp theo

### 4.8 `monitoring_sessions` — owner: monitoring

| Cột | Kiểu / ràng buộc | Ý nghĩa |
|---|---|---|
| `id` | uuid PK | Phiên xuyên reconnect |
| `source_type` | enum NN | `video`, `image` |
| `status` | enum NN | `active`, `completed`, `failed` |
| `created_by` | uuid FK users NN | Safety Officer |
| `zone_id` | uuid FK zones nullable | Context nâng cao |
| `shift_id` | uuid FK shifts nullable | Context nâng cao |
| `rule_version_id` | uuid FK safety_rule_versions nullable | Rule chạy trong phiên |
| `machine_state` | enum NN | `running`, `stopped` |
| `polygon_snapshot` | jsonb NN | Tọa độ normalized tại phiên |
| `timezone` | varchar(64) NN | Hiển thị và phân ca |
| `started_at`, `ended_at` | timestamptz | Lifecycle |
| `created_at`, `updated_at` | timestamptz | Audit |

Không lưu đường dẫn raw video upload dài hạn. Với phân tích ảnh, input thô chỉ tồn tại in-memory/temp trong lúc xử lý.

### 4.9 `safety_events` — owner: events

| Cột | Kiểu / ràng buộc | Ý nghĩa |
|---|---|---|
| `id` | uuid PK | Event public ID |
| `session_id` | uuid FK monitoring_sessions NN | Phiên nguồn |
| `zone_id`, `shift_id` | uuid FK nullable | Denormalized immutable context cho audit/query |
| `rule_version_id` | uuid FK safety_rule_versions NN | Giải thích quyết định |
| `track_id` | varchar(128) NN | Track trong phiên |
| `occurrence_no` | integer NN default 1 | Lần tái diễn sau kết thúc/cooldown |
| `violation_type` | enum NN | `zone_intrusion`, `missing_ppe` |
| `ppe_item` | enum nullable | helmet/glasses/gloves với missing PPE |
| `severity` | enum NN | low/medium/high/critical |
| `status` | enum NN | pending/acknowledged/confirmed/false_alarm |
| `confidence` | numeric(5,4) NN | `[0,1]` |
| `machine_state` | enum NN | State lúc quyết định |
| `detected_at`, `ended_at` | timestamptz | Occurrence interval |
| `correlation_id` | varchar(128) NN | Trace xuyên hệ thống |
| `decision_context` | jsonb NN | Reason codes, observation/PPE snapshot, threshold |
| `summary_text` | text nullable | LLM/fallback summary dẫn xuất |
| `summary_generator` | enum nullable | `llm`, `deterministic` |
| `created_by` | uuid FK users nullable | System/null hoặc actor tạo compatibility event |
| `created_at`, `updated_at` | timestamptz | Lifecycle |

Unique dedup `(session_id, track_id, rule_version_id, violation_type, coalesce(ppe_item,''), occurrence_no)`. Check: `ppe_item` bắt buộc khi `missing_ppe`, null khi `zone_intrusion`. Event core context không được update sau tạo; chỉ `status`, `ended_at`, summary và timestamps thay đổi qua service có audit.

### 4.10 `event_transitions` — owner: events

| Cột | Kiểu / ràng buộc | Ý nghĩa |
|---|---|---|
| `id` | uuid PK | Transition audit ID |
| `event_id` | uuid FK safety_events NN | Event |
| `from_status`, `to_status` | enum NN | State edge |
| `actor_user_id` | uuid FK users NN | HITL actor |
| `reason_code` | varchar(64) NN | Machine-readable reason |
| `note` | text nullable | Ghi chú giới hạn độ dài |
| `idempotency_key` | varchar(128) NN | Chống replay |
| `occurred_at`, `created_at` | timestamptz NN | Client/business và server timestamp |

Unique `(actor_user_id, idempotency_key)`. Append-only; không update/delete trong retention audit.

### 4.11 `snapshots` — owner: events

| Cột | Kiểu / ràng buộc | Ý nghĩa |
|---|---|---|
| `id` | uuid PK | Snapshot ID |
| `event_id` | uuid FK safety_events NN UQ | Tối đa một evidence snapshot/event trong scope |
| `storage_key` | varchar(512) NN UQ | Opaque object key, không phải path client cung cấp |
| `content_type` | varchar(64) NN | Allowlist JPEG/PNG |
| `byte_size` | bigint NN | >0 và dưới limit |
| `sha256` | char(64) NN | Integrity/dedup evidence |
| `width`, `height` | integer NN | Kích thước pixel |
| `privacy_blurred` | boolean NN, check true | Chỉ row hợp lệ khi true |
| `privacy_method`, `privacy_version` | varchar NN | Audit processor |
| `retention_until` | timestamptz NN | Chính sách xóa |
| `created_at`, `deleted_at` | timestamptz | Lifecycle/object cleanup |

Transaction policy: xử lý blur in-memory → ghi object tạm → verify → commit DB/object; lỗi ở bất kỳ bước nào phải cleanup object và không confirm event.
