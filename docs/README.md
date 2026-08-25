# Phạm vi tài liệu `docs`

Thư mục này chứa kiến trúc, hướng dẫn vận hành, chuẩn bị dữ liệu, kế hoạch triển khai và mô tả cấu trúc dự án. Mỗi tài liệu phải tự cung cấp đủ ngữ cảnh để đọc độc lập.

Structure subdirectories:
- `docs/architecture/`: Problem statement, architecture diagrams, và alert rule contracts.
- `docs/ops/`: Operations, CI/CD, direct-file media deployment, operational metrics, local Postgres, Vision worker và AI team workflow.
- `docs/data/`: Hướng dẫn chuẩn bị dữ liệu và dataset evaluation.
- `docs/plans/`: Kế hoạch thực thi chi tiết (implementation plans).
- `docs/guide/`: Hướng dẫn cài đặt, tài nguyên tham khảo và Hướng dẫn Onboarding (`docs/guide/ONBOARDING.md`).

Quy tắc tài liệu:

- Không dùng file này hoặc file con làm chỉ mục điều hướng.
- Không tạo liên kết từ một tài liệu sang tài liệu khác.
- Root `context-map.md` là chỉ mục duy nhất của repository.
- Khi tạo, xóa hoặc di chuyển tài liệu, cập nhật chỉ mục root `context-map.md` và `docs/PROJECT_STRUCTURE.md`.
- Quy tắc workflow bắt buộc dành cho agent có thể chứa liên kết để nạp đúng ngữ cảnh.
