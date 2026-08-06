# Hợp Đồng API Chung — Chỉ Mục Đọc Theo Ngữ Cảnh

> **Phiên bản:** 1.0 — 2026-08-06  
> **Phạm vi:** REST API và WebSocket cho MVP cùng giai đoạn nâng cao 5 tuần  
> **Trạng thái:** **READ-ONLY — KHÔNG ĐƯỢC CHỈNH SỬA.** Đây là contract đã được phê duyệt cho team. Route ghi **Hiện có** phải tiếp tục tương thích; route ghi **Kế hoạch** chỉ trở thành contract runtime sau khi có schema và contract test. Nếu implementation cần thay đổi contract, agent phải dừng và xin quyết định rõ ràng từ người dùng, không tự sửa file trong thư mục này.

Thư mục này thay cho một file API lớn. AI và contributor chỉ đọc `README.md` cùng chương liên quan đến task; không cần nạp toàn bộ contract.

## Bản đồ đọc

| File | Nội dung | Đọc khi nào |
|---|---|---|
| [`01-foundations.md`](01-foundations.md) | Nguồn sự thật, versioning, quy ước HTTP, auth, lỗi và kiểu chung | Mọi thay đổi API; đây là chương nền bắt buộc |
| [`02-endpoint-catalog.md`](02-endpoint-catalog.md) | Danh mục route, owner, role và trạng thái hiện có/kế hoạch | Tìm endpoint hoặc xác định module owner |
| [`03-auth-monitoring-inference.md`](03-auth-monitoring-inference.md) | Auth, monitoring session, REST image/frame và WebSocket inference | US-01–US-04, US-07, US-08, US-13, US-20, US-24 |
| [`04-rules-events-analytics.md`](04-rules-events-analytics.md) | Rule, HITL event, analytics, organization, escalation và reporting | US-05, US-06, US-09–US-12, US-14–US-16, US-21–US-23 |
| [`05-quality-and-traceability.md`](05-quality-and-traceability.md) | Compatibility, Definition of Done và story mapping | Review contract, test, release hoặc thay đổi breaking |

## Quy tắc đọc tối thiểu

1. Luôn đọc `01-foundations.md` trước khi thay đổi wire contract.
2. Đọc đúng một chương nghiệp vụ liên quan; chỉ mở chương khác nếu task thật sự chạm boundary đó.
3. Trước khi hoàn tất, đọc `05-quality-and-traceability.md` để kiểm compatibility và test.
4. REST runtime lấy Pydantic/FastAPI làm nguồn sự thật; WebSocket/backend–vision lấy JSON Schema version hóa trong `contracts/`. Không sửa generated artifact bằng tay.
5. Không edit, rename, delete, move, regenerate, overwrite hoặc thêm file trong thư mục `docs/API_CONTRACT/`.

## Điều hướng liên quan

- Data model và ERD: [`../DATABASE_SCHEMA/README.md`](../DATABASE_SCHEMA/README.md)
- Target ownership: [`../FUTURE_PROJECT_STRUCTURE.md`](../FUTURE_PROJECT_STRUCTURE.md)
- Backlog: [`../../specs/USER_STORIES_LIST.md`](../../specs/USER_STORIES_LIST.md)
