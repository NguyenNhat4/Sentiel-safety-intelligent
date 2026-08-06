# Documentation Catalog (`docs/README.md`)

[`README.md`](../README.md) tại root là điểm bắt đầu và master index của repository. Tài liệu này là catalog chi tiết cấp hai, giải thích vị trí, nội dung và thời điểm cần đọc từng tài liệu trong dự án **P-047**.

---

## 📚 Danh Mục Tài Liệu & Hướng Dẫn Sử Dụng (What & When to Read)

| Tài liệu | Loại / Mục đích | Nội dung chính | Khi nào cần đọc? (When to read) | Khi nào cần cập nhật? (When to update) |
|---|---|---|---|---|
| **[`README.md`](../README.md)** | **Repository Introduction & Master Index** | Giới thiệu dự án, trạng thái, quick start và điều hướng tới toàn bộ nhóm tài liệu | Điểm bắt đầu cho thành viên mới hoặc khi chưa biết cần đọc tài liệu nào | Khi tổng quan, trạng thái cấp cao, quick start hoặc cấu trúc điều hướng thay đổi |
| **[`docs/README.md`](README.md)** | **Detailed Documentation Catalog** | Catalog chi tiết vị trí và thời điểm sử dụng tài liệu | Khi cần tra cứu sâu sau khi đi từ master index | Khi tạo mới, xóa hoặc tái cấu trúc các file tài liệu |
| **[`AGENTS.md`](../AGENTS.md)** | **Agent Workflow Rules** | Quy tắc làm việc của Agent, quy trình Clock In/Clock Out, kiểm thử và theo dõi tiến độ | Trước khi khởi chạy session mới hoặc thực hiện quy trình phát triển | Khi thay đổi quy trình làm việc, tiêu chuẩn kiểm thử hoặc lệnh `make check` |
| **[`README.md`](../README.md)** | **Project Overview** | Tổng quan dự án, vấn đề, giải pháp, tech stack và hướng dẫn chạy nhanh (Quick Start) | Khi cần cái nhìn tổng quan ban đầu về dự án hoặc cách chạy ứng dụng | Khi thay đổi hướng dẫn cài đặt, tech stack chính, hoặc lệnh khởi chạy |
| **[`docs/PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md)** | **Current Project Structure** | Sơ đồ filesystem hiện tại và trách nhiệm của các phân hệ đang tồn tại | Khi cần tìm vị trí lưu file hoặc hiểu layout đang chạy | **Mỗi khi tạo/xóa/di chuyển file hoặc tái cấu trúc folder trong dự án** |
| **[`docs/FUTURE_PROJECT_STRUCTURE.md`](FUTURE_PROJECT_STRUCTURE.md)** | **Approved Target Structure** | Nguồn duy nhất cho cấu trúc đích tối thiểu, ownership, dependency, guardrail và lộ trình migration | Trước khi tạo module, đổi ranh giới hoặc triển khai story sang cấu trúc đích | Chỉ khi có quyết định kiến trúc mới trong root `DECISIONS.md`; cập nhật cùng thay đổi boundary |
| **[`ARCHITECTURE.md`](../ARCHITECTURE.md)** | **System Architecture** | Kiến trúc tổng quan hệ thống, Mermaid diagram kết nối giữa CV, Backend, Frontend và DB | Khi thiết kế tính năng mới, kết nối các service hoặc làm việc với data flow | Khi thay đổi kiến trúc tổng thể, giao thức kết nối hoặc luồng dữ liệu |
| **[`docs/architecture_diagram.md`](architecture_diagram.md)** | **Detailed Architecture** | Sơ đồ luồng xử lý chi tiết (CV Pipeline, Decision Engine, WebSocket Gateway, Docker Compose) | Khi cần xem chi tiết luồng xử lý Computer Vision hoặc cấu hình Docker | Khi thay đổi chi tiết luồng xử lý CV, rule evaluation hoặc môi trường Docker |
| **[`specs/README.md`](../specs/README.md)** | **Product Specifications Index** | Chỉ mục yêu cầu sản phẩm và backlog triển khai trong thư mục `specs/` | Khi cần tìm tài liệu yêu cầu hoặc user story | Khi thêm, xóa hoặc tái cấu trúc tài liệu đặc tả |
| **[`specs/PRD.md`](../specs/PRD.md)** | **Product Requirements** | Yêu cầu sản phẩm MVP, phạm vi tính năng, core flow và tiêu chí thành công | Khi bắt đầu phát triển tính năng mới để đảm bảo đúng scope MVP | Khi có sự thay đổi hoặc làm rõ về yêu cầu/phạm vi MVP |
| **[`specs/USER_STORIES_LIST.md`](../specs/USER_STORIES_LIST.md)** | **User Story Backlog** | Các user story và task cho giai đoạn đóng MVP trong tuần hiện tại và delivery nâng cao 5 tuần theo problem statement | Khi chọn story tiếp theo hoặc rà soát độ bao phủ toàn dự án | Khi trạng thái story, kế hoạch delivery, PRD hoặc problem statement thay đổi |
| **[`docs/project-problem-statement.md`](project-problem-statement.md)** | **Problem Statement** | Mô tả thực trạng, bài toán chi tiết, ràng buộc an toàn & bảo mật, và yêu cầu đầu ra | Khi cần nắm rõ ngữ cảnh bài toán nhà máy, ràng buộc privacy và tiêu chuẩn báo cáo | Khi bài toán hoặc các ràng buộc nghiệp vụ an toàn thay đổi |
| **[`docs/API_CONTRACT/README.md`](API_CONTRACT/README.md)** | **Shared API Contract Index — Read-only** | Chỉ mục các chương REST/WebSocket nhỏ theo task: nền tảng, endpoint, inference, event và quality | Trước khi backend/frontend/vision thay đổi wire contract; chỉ đọc chương liên quan theo routing table | **Không cập nhật.** Nếu implementation xung đột, dừng và xin quyết định contract từ người dùng |
| **[`docs/DATABASE_SCHEMA/README.md`](DATABASE_SCHEMA/README.md)** | **Shared Data Contract & ERD Index — Read-only** | Chỉ mục schema theo capability: ERD/ownership, bảng nghiệp vụ và migration/operations | Trước khi tạo migration, ORM model, repository/query analytics hoặc thiết kế backup; chỉ đọc capability liên quan | **Không cập nhật.** Nếu implementation xung đột, dừng và xin quyết định contract từ người dùng |
| **`docs/guide/`** | **Technical Guides** | Bộ hướng dẫn chi tiết về setup (`docs/guide/setup/uv-setup.md`), devops, testing, anti-patterns, v.v. | Khi cần tham khảo bài viết kỹ thuật chuyên sâu về từng chủ đề cụ thể | Khi đóng góp hoặc cập nhật hướng dẫn kỹ thuật |
| **[`docs/guide/setup/uv-setup.md`](guide/setup/uv-setup.md)** | **uv Setup & Usage Guide** | Hướng dẫn cài đặt môi trường, `make setup` và quản lý Python dependencies bằng `uv` | Khi thiết lập môi trường phát triển mới hoặc quản lý thư viện Python | Khi thay đổi công cụ quản lý package Python hoặc quy trình setup môi trường |
| **[`PROGRESS.md`](../PROGRESS.md) & [`DECISIONS.md`](../DECISIONS.md)** *(root only)* | **Central Project Tracking** | Trạng thái và quyết định của mọi phân hệ, phân loại bằng nhãn `[Backend]`, `[Frontend]`, `[Vision]`, `[Cross-cutting]` | Khi "Clock In" để xem trạng thái toàn dự án | Khi hoàn thành công việc hoặc đưa ra quyết định thiết kế; không tạo bản tracking trong module |

---

## 🎯 Nguyên Tắc Độc Lập Tài Liệu (Decoupling Principles)

1. **Phân tách trách nhiệm**:
   - `README.md` (root): Giới thiệu dự án, trạng thái cấp cao, Quick Start và master index điều hướng.
   - `docs/PROJECT_STRUCTURE.md`: Lưu trữ cấu trúc thư mục chi tiết. Không nhồi nhét cấu trúc chi tiết vào `README.md`.
   - `AGENTS.md`: Định nghĩa quy định và trỏ tới `docs/README.md` làm bản đồ tài liệu duy nhất.
2. **Cập nhật đúng nơi**: Khi thay đổi cấu trúc dự án, cập nhật trực tiếp tại `docs/PROJECT_STRUCTURE.md` thay vì `README.md`.
3. **Phân biệt hiện tại và đích**: `PROJECT_STRUCTURE.md` mô tả filesystem đang tồn tại; `FUTURE_PROJECT_STRUCTURE.md` là baseline đã chốt để định hướng migration và review.
4. **Một nguồn cấu trúc đích**: Ownership, dependency, cách đặt code và migration đều nằm trong `FUTURE_PROJECT_STRUCTURE.md`; không duy trì guide trùng lặp.
