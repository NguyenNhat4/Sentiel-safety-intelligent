# Database Schema — Constraints, Privacy và Vận Hành

> Chỉ mục: [`README.md`](README.md) · ERD/ownership: [`01-foundations-and-ownership.md`](01-foundations-and-ownership.md)

## 5. Enum và state transition chuẩn

| Nhóm | Giá trị |
|---|---|
| User role | `safety_officer`, `zone_manager` |
| Machine state | `running`, `stopped` |
| Violation | `zone_intrusion`, `missing_ppe` |
| PPE item | `helmet`, `glasses`, `gloves` |
| Severity | `low`, `medium`, `high`, `critical` |
| Event status | `pending`, `acknowledged`, `confirmed`, `false_alarm` |
| Escalation status | `pending`, `delivering`, `delivered`, `acknowledged`, `failed` |

Event transition hợp lệ: `pending→acknowledged|confirmed|false_alarm`, `acknowledged→confirmed|false_alarm`. `confirmed` và `false_alarm` là terminal. Mọi transition phải ghi `event_transitions` trong cùng transaction với update event.

## 6. Index, query và analytics

Index tối thiểu:

- `safety_events (zone_id, detected_at desc)`, `(shift_id, detected_at desc)`, `(status, detected_at desc)`, `(violation_type, severity, detected_at desc)`.
- Partial index pending review: `safety_events (detected_at) WHERE status IN ('pending','acknowledged')`.
- Dedup unique index như mục 4.9.
- `event_transitions (event_id, occurred_at)`.
- `escalations (status, next_retry_at)` cho worker.
- `reports (schedule_id, period_start, period_end)` và `report_schedules (is_active, next_run_at)`.

Analytics phải định nghĩa rõ mẫu số:

- `false_alarm_rate = false_alarm / reviewed_alerts`, trong đó reviewed là confirmed + false_alarm (và acknowledged chỉ tính nếu nghiệp vụ chốt là review hoàn tất).
- `compliance_rate = compliant_observations / eligible_observations`; nếu chưa persistence/aggregate eligible observations thì API phải trả `null`, không tự suy từ event count.
- Time bucket được tính theo timezone query rồi trả timestamp có offset/UTC rõ ràng.

Không tạo bảng observation từng frame trong MVP vì trái ràng buộc privacy/storage và chưa cần cho business flow. Nếu US-22 cần mẫu số bền vững, thiết kế aggregate table riêng phải có quyết định retention và owner analytics trước khi migration.

## 7. Retention, privacy và bảo mật

| Dữ liệu | Policy contract |
|---|---|
| Raw video/frame/image | Không persistence; temp phải cleanup sau request |
| Blurred snapshot | Chỉ cho confirmed/review event theo policy; xóa theo `retention_until` |
| Event/audit | Giữ theo chính sách an toàn đã được Product/Legal chốt; append-only transition |
| Auth session | Xóa sau expiry + operational grace period |
| Report artifact | Chỉ chứa dữ liệu được phép và ảnh đã blur; retention theo schedule/policy |
| Logs | Không raw image, token, password, PII chưa redact; dùng IDs/correlation ID |

Snapshot download luôn qua authorization/service hoặc signed URL ngắn hạn; client không được truyền filesystem path. Backup phải mã hóa và tuân cùng retention; restore test phải kiểm tra object–DB consistency.

## 8. Migration và compatibility

1. Alembic migration đã apply là immutable; sửa schema bằng migration mới.
2. Migration thêm cột cho dữ liệu hiện hữu phải theo expand → backfill → enforce constraint → contract switch → cleanup.
3. PostgreSQL là chuẩn production; SQLAlchemy behavior cần tương thích SQLite cho local/test, nhưng PostgreSQL constraint/index quan trọng phải có integration test riêng.
4. Enum database khó rollback; ưu tiên varchar + check constraint hoặc quy trình enum migration có rollback được tài liệu hóa.
5. FK delete mặc định `RESTRICT`; chỉ cascade cho dữ liệu thuần phụ thuộc như auth session/delivery khi retention cho phép. Audit/event không cascade.
6. Mỗi migration kèm upgrade/downgrade strategy, data backfill, lock/risk note và contract test.

## 9. Transaction boundaries quan trọng

- Event transition: validate state + insert transition + update event trong một transaction.
- Confirm snapshot: redact in-memory + object staging + DB event/snapshot commit + finalize object; lỗi phải cleanup, không được đánh dấu blur giả.
- Dedup: unique constraint là lớp bảo vệ cuối; service xử lý conflict thành event hiện hữu thay vì `500`.
- Escalation/report: outbox/job claim hoặc transaction-safe scheduling để DB commit không dẫn tới gửi trùng/mất gửi.
- Shift overlap và active assignment: validate dưới transaction phù hợp để tránh race.

## 10. Traceability và Definition of Done

| Nhóm bảng | Story |
|---|---|
| Monitoring/rules/events/snapshot | US-01–US-13, US-16, US-24 |
| Auth | US-17, US-20 |
| Organization | US-21 |
| Escalation | US-14, US-15 |
| Analytics queries | US-10, US-22 |
| Reporting | US-23 |
| Migration/backup/operations | US-18, US-19, US-25, US-26 |

Một thay đổi database chỉ Done khi migration, ORM/domain mapping, repository query, API contract, authorization, fixture và rollback/cleanup test đồng bộ; `docs/PROJECT_STRUCTURE.md` và root tracking được cập nhật nếu filesystem/trạng thái dự án thay đổi.
