# Master Documentation Index (`docs/README.md`)

Tài liệu này đóng vai trò là **Master Index** hướng dẫn vị trí, nội dung và thời điểm cần đọc hoặc cập nhật từng tài liệu trong dự án **P-047**.

---

## 📚 Danh Mục Tài Liệu & Hướng Dẫn Sử Dụng (What & When to Read)

| Tài liệu | Loại / Mục đích | Nội dung chính | Khi nào cần đọc? (When to read) | Khi nào cần cập nhật? (When to update) |
|---|---|---|---|---|
| **[`docs/README.md`](README.md)** | **Master Index** | Chỉ mục toàn bộ tài liệu dự án, vị trí và thời điểm sử dụng | Khi bắt đầu làm việc hoặc tìm kiếm thông tin tài liệu liên quan | Khi tạo mới, xóa hoặc tái cấu trúc các file tài liệu |
| **[`AGENTS.md`](../AGENTS.md)** | **Agent Workflow Rules** | Quy tắc làm việc của Agent, quy trình Clock In/Clock Out, kiểm thử và theo dõi tiến độ | Trước khi khởi chạy session mới hoặc thực hiện quy trình phát triển | Khi thay đổi quy trình làm việc, tiêu chuẩn kiểm thử hoặc lệnh `make check` |
| **[`README.md`](../README.md)** | **Project Overview** | Tổng quan dự án, vấn đề, giải pháp, tech stack và hướng dẫn chạy nhanh (Quick Start) | Khi cần cái nhìn tổng quan ban đầu về dự án hoặc cách chạy ứng dụng | Khi thay đổi hướng dẫn cài đặt, tech stack chính, hoặc lệnh khởi chạy |
| **[`docs/PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md)** | **Project Structure Layout** | Sơ đồ cấu trúc thư mục chi tiết (hiện tại & tương lai) và giải thích trách nhiệm từng phân hệ | Khi cần tìm vị trí lưu file, hiểu mối quan hệ các phân hệ, hoặc tạo file/folder mới | **Mỗi khi tạo/xóa/di chuyển file hoặc tái cấu trúc folder trong dự án** |
| **[`ARCHITECTURE.md`](../ARCHITECTURE.md)** | **System Architecture** | Kiến trúc tổng quan hệ thống, Mermaid diagram kết nối giữa CV, Backend, Frontend và DB | Khi thiết kế tính năng mới, kết nối các service hoặc làm việc với data flow | Khi thay đổi kiến trúc tổng thể, giao thức kết nối hoặc luồng dữ liệu |
| **[`docs/architecture_diagram.md`](architecture_diagram.md)** | **Detailed Architecture** | Sơ đồ luồng xử lý chi tiết (CV Pipeline, Decision Engine, WebSocket Gateway, Docker Compose) | Khi cần xem chi tiết luồng xử lý Computer Vision hoặc cấu hình Docker | Khi thay đổi chi tiết luồng xử lý CV, rule evaluation hoặc môi trường Docker |
| **[`docs/PRD.md`](PRD.md)** | **Product Requirements** | Yêu cầu sản phẩm MVP, phạm vi tính năng, core flow và tiêu chí thành công | Khi bắt đầu phát triển tính năng mới để đảm bảo đúng scope MVP | Khi có sự thay đổi hoặc làm rõ về yêu cầu/phạm vi MVP |
| **[`docs/project-problem-statement.md`](project-problem-statement.md)** | **Problem Statement** | Mô tả thực trạng, bài toán chi tiết, ràng buộc an toàn & bảo mật, và yêu cầu đầu ra | Khi cần nắm rõ ngữ cảnh bài toán nhà máy, ràng buộc privacy và tiêu chuẩn báo cáo | Khi bài toán hoặc các ràng buộc nghiệp vụ an toàn thay đổi |
| **`docs/guide/`** | **Technical Guides** | Bộ hướng dẫn chi tiết về setup, devops, testing, anti-patterns, v.v. | Khi cần tham khảo bài viết kỹ thuật chuyên sâu về từng chủ đề cụ thể | Khi đóng góp hoặc cập nhật hướng dẫn kỹ thuật |
| **`PROGRESS.md` & `DECISIONS.md`** *(trong từng module)* | **Module Tracking** | Ghi chép quyết định thiết kế và tiến độ công việc theo từng phân hệ (`backend/`, `frontend/`, `vision/`) | Khi "Clock In" (bắt đầu session) để xem công việc đang làm dở | Khi đưa ra quyết định thiết kế quan trọng hoặc trước khi "Clock Out" |

---

## 🎯 Nguyên Tắc Độc Lập Tài Liệu (Decoupling Principles)

1. **Phân tách trách nhiệm**:
   - `README.md` (root): Chỉ chứa thông tin tổng quan dự án, bài toán & Quick Start.
   - `docs/PROJECT_STRUCTURE.md`: Lưu trữ cấu trúc thư mục chi tiết. Không nhồi nhét cấu trúc chi tiết vào `README.md`.
   - `AGENTS.md`: Định nghĩa quy định và trỏ tới `docs/README.md` làm bản đồ tài liệu duy nhất.
2. **Cập nhật đúng nơi**: Khi thay đổi cấu trúc dự án, cập nhật trực tiếp tại `docs/PROJECT_STRUCTURE.md` thay vì `README.md`.
