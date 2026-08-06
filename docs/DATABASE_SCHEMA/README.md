# Hợp Đồng Dữ Liệu và Sơ Đồ Cơ Sở Dữ Liệu — Chỉ Mục

> **Phiên bản:** 1.0 — 2026-08-06  
> **Database:** PostgreSQL production; SQLite chỉ cho local/test baseline  
> **Trạng thái:** **READ-ONLY — KHÔNG ĐƯỢC CHỈNH SỬA.** Đây là logical target schema đã được phê duyệt cho team. Alembic migration mới là lịch sử schema runtime; migration đã apply không được sửa lại. Nếu implementation cần thay đổi contract dữ liệu, agent phải dừng và xin quyết định rõ ràng từ người dùng, không tự sửa file trong thư mục này.

Thư mục này chia schema theo capability để AI chỉ nạp đúng phần liên quan. Mọi task database đọc chương nền/ownership và chương chứa bảng do module đó sở hữu.

## Bản đồ đọc

| File | Nội dung | Owner/task phù hợp |
|---|---|---|
| [`01-foundations-and-ownership.md`](01-foundations-and-ownership.md) | Nguyên tắc, ERD tổng thể, ownership bảng | Bắt buộc cho mọi migration/schema task |
| [`02-identity-organization-rules.md`](02-identity-organization-rules.md) | `users`, auth session, zone, shift, assignment và rule versions | `auth`, `organization`, `rules` |
| [`03-monitoring-events-and-snapshots.md`](03-monitoring-events-and-snapshots.md) | Monitoring session, safety event, HITL transition và blurred snapshot | `monitoring`, `events` |
| [`04-escalation-and-reporting.md`](04-escalation-and-reporting.md) | Escalation attempts, report schedule/artifact/delivery | `escalation`, `reporting` |
| [`05-constraints-and-operations.md`](05-constraints-and-operations.md) | Enum, index, metric, privacy, retention, migration và transaction | Migration review, analytics, security, operations |

## Quy tắc đọc tối thiểu

1. Luôn đọc `01-foundations-and-ownership.md` để xác định owner và quan hệ.
2. Chỉ đọc file chứa bảng được task chạm tới.
3. Đọc `05-constraints-and-operations.md` trước khi tạo hoặc review migration.
4. Không tạo một `models.py` dùng chung cho toàn hệ thống: ORM model nằm trong capability owner; migration tập trung tại `backend/migrations/versions/`.
5. Không edit, rename, delete, move, regenerate, overwrite hoặc thêm file trong thư mục `docs/DATABASE_SCHEMA/`.

## Điều hướng liên quan

- REST/WebSocket contract: [`../API_CONTRACT/README.md`](../API_CONTRACT/README.md)
- Target ownership: [`../FUTURE_PROJECT_STRUCTURE.md`](../FUTURE_PROJECT_STRUCTURE.md)
- Backlog: [`../../specs/USER_STORIES_LIST.md`](../../specs/USER_STORIES_LIST.md)
