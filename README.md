# P-047 — AI Agent Giám Sát An Toàn PPE và Khu Vực Nguy Hiểm

P-047 là ứng dụng web dùng Computer Vision để hỗ trợ giám sát an toàn trong nhà máy. Hệ thống phân tích video hoặc ảnh mô phỏng, phát hiện người, kiểm tra PPE, xác định xâm nhập vùng nguy hiểm theo trạng thái máy, đưa cảnh báo cho con người xác minh và lưu bằng chứng đã bảo vệ danh tính.

README này là **điểm bắt đầu và master index của repository**. Nếu chưa biết đọc tài liệu nào, bắt đầu từ phần [Bản đồ tài liệu](#bản-đồ-tài-liệu).

## Bài toán

Nhân sự an toàn khó theo dõi liên tục nhiều khu vực có máy dập, xe nâng hoặc hóa chất. Vi phạm PPE và xâm nhập vùng cấm có thể bị bỏ sót hoặc cảnh báo chậm.

Hệ thống hướng tới:

- Phát hiện người và PPE bắt buộc: mũ, kính và găng bảo hộ.
- Xác định người đi vào polygon vùng nguy hiểm.
- Chỉ đánh giá xâm nhập là critical khi máy đang chạy.
- Hiển thị cảnh báo gần realtime và chuyển trường hợp mơ hồ cho con người.
- Chống tạo nhiều event cho cùng một vi phạm liên tục.
- Lưu quyết định review, audit context và snapshot đã làm mờ danh tính.
- Thống kê tuân thủ theo thời gian, khu vực và ca làm việc.
- Escalate sự cố nghiêm trọng và tạo báo cáo định kỳ trong giai đoạn nâng cao.

## Người dùng

| Vai trò | Nhu cầu chính |
|---|---|
| Cán bộ an toàn (`safety_officer`) | Theo dõi, nhận cảnh báo, review, xác nhận vi phạm hoặc false alarm |
| Quản lý khu vực (`zone_manager`) | Quản lý khu vực/ca, xem dashboard, escalation và báo cáo |

## Phạm vi và giới hạn

Dự án đang phát triển theo hai giai đoạn:

1. Đóng MVP với video/ảnh mô phỏng, PPE, vùng nguy hiểm, HITL, privacy, event log, authentication và dashboard cơ bản.
2. Giao bản nâng cao trong 5 tuần với khu vực/ca, confidence triage, escalation, dashboard quản trị, báo cáo và cloud operations.

Camera nhà máy thật, PLC, tự động dừng máy và xử lý đồng thời nhiều stream không thuộc phạm vi đã cam kết. Xem [Problem Statement](docs/project-problem-statement.md), [PRD](specs/PRD.md) và [User Story Backlog](specs/USER_STORIES_LIST.md) để biết phạm vi chính xác.

## Trạng thái hiện tại

Baseline đang hoạt động gồm:

- React 19 + TypeScript + Vite cho giao diện monitor.
- FastAPI phục vụ REST, WebSocket và production frontend build.
- Upload video local, vẽ vùng bốn điểm và trạng thái máy chạy/dừng.
- YOLO person detection, foot-point polygon evaluation và frame inference gần realtime.
- ByteTrack gán track ID theo phiên video và backend chống review/event lặp cho cùng occurrence.
- HITL review, lưu event đã xác nhận với snapshot đã che danh tính, nhật ký snapshot và thống kê baseline.
- SQLite cho local/test; PostgreSQL là database production đích.

Các khoảng trống quan trọng gồm PPE model mũ/kính/găng production-ready, face detector đã benchmark cho production, authentication/RBAC, migration PostgreSQL, dedup hoàn chỉnh, zone/shift, escalation và reporting. Trạng thái mới nhất luôn nằm trong [PROGRESS.md](PROGRESS.md).

## Kiến trúc tóm tắt

```text
React frontend
    ↓ REST / WebSocket contract
FastAPI modular monolith
    ↓ public facade
Vision pipeline (YOLO + tracking + zone + privacy)
    ↓
PostgreSQL / blurred object storage
```

| Thành phần | Công nghệ |
|---|---|
| Vision | Python, Ultralytics YOLO, OpenCV; ByteTrack theo cấu trúc đích |
| Backend | FastAPI, SQLAlchemy, Alembic |
| Frontend | React 19, TypeScript, Vite |
| Database | SQLite local/test; PostgreSQL production |
| Deployment | Docker Compose; cloud là giai đoạn nâng cao |

Chi tiết boundary, data flow và dependency direction: [ARCHITECTURE.md](ARCHITECTURE.md) và [Future Project Structure](docs/FUTURE_PROJECT_STRUCTURE.md).

## Bản đồ tài liệu

### Bắt đầu công việc

| Khi cần | Đọc tài liệu |
|---|---|
| Hiểu vấn đề và đầu ra | [Problem Statement](docs/project-problem-statement.md) |
| Hiểu phạm vi MVP | [PRD](specs/PRD.md) |
| Chọn story và xem acceptance criteria | [User Story Backlog](specs/USER_STORIES_LIST.md) |
| Đặc tả triển khai US-07 PPE | [US-07 PPE Specification](specs/done/US-07-SPEC.md) |
| Đặc tả US-08 tracking và chống event trùng | [US-08 Tracking/Dedup Specification](specs/done/US-08-SPEC.md) |
| Kế hoạch và task đang hoạt động | [Implementation Plan](tasks/plan.md) và [Task List](tasks/todo.md) |
| Xem công việc đã làm và bước tiếp theo | [PROGRESS.md](PROGRESS.md) |
| Xem quyết định đã chốt | [DECISIONS.md](DECISIONS.md) |
| Tuân thủ workflow của AI/contributor | [AGENTS.md](AGENTS.md) |

### Kiến trúc và vị trí code

| Khi cần | Đọc tài liệu |
|---|---|
| Hiểu kiến trúc hệ thống | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Biết filesystem hiện đang có | [Current Project Structure](docs/PROJECT_STRUCTURE.md) |
| Biết cấu trúc đích đã phê duyệt | [Future Project Structure](docs/FUTURE_PROJECT_STRUCTURE.md) |
| Chọn đúng module owner và dependency | [Future Project Structure](docs/FUTURE_PROJECT_STRUCTURE.md) |

### Contract đang chạy

| Khi cần | Điểm vào |
|---|---|
| REST/WebSocket endpoint và payload | FastAPI routes/Pydantic schemas trong `backend/app/`, wire types trong `frontend/src/types/`, và [backend README](backend/README.md) |
| Bảng, constraint, query và migration | SQLAlchemy models trong `backend/app/models/`, Alembic trong `backend/migrations/`, và test backend liên quan |

Các executable definition trên là nguồn sự thật hiện hành. Thay đổi breaking phải được người dùng cho phép, ghi vào `DECISIONS.md` và có test tương thích hoặc migration phù hợp.

### Hướng dẫn phát triển

| Khi cần | Đọc tài liệu |
|---|---|
| Cài đặt môi trường Python bằng `uv` | [uv Setup Guide](docs/guide/setup/uv-setup.md) |
| Quy trình phối hợp AI | [AI Team Workflow](docs/AI_TEAM_WORKFLOW.md) |

## Quick start

Yêu cầu Python 3.11–3.13. Python 3.14 hiện có thể làm bộ test FastAPI `TestClient` bị treo.

```bash
git clone https://github.com/AI20K-Build-Cohort-2/P-047.git
cd P-047
make setup
make run
```

Sau khi chạy:

- Monitor UI: <http://localhost:8000/>
- Swagger: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>
- OpenAPI JSON: <http://localhost:8000/openapi.json>
- Health check: <http://localhost:8000/health>
- WebSocket inference: `ws://localhost:8000/api/v1/ws/inference`

WebSocket không xuất hiện trong Swagger vì OpenAPI chỉ mô tả HTTP API. Message sequence và field semantics của WebSocket được mô tả trong [backend README](backend/README.md#frame-inference-contract) và kiểm chứng bởi test transport hai phía.

## Kiểm tra repository

```bash
make check
```

Có thể chạy từng nhóm:

```bash
make lint
make format
make test
npm --prefix frontend run lint
npm --prefix frontend run type-check
npm --prefix frontend run test
npm --prefix frontend run build
```

## Luồng smoke test baseline

1. Mở <http://localhost:8000/> và upload video mô phỏng.
2. Vẽ đúng bốn điểm của vùng nguy hiểm.
3. Chuyển máy sang trạng thái chạy và phát video.
4. Xác nhận bounding box người và foot point được hiển thị.
5. Xác nhận video chỉ dừng để review khi foot point vào vùng trong lúc máy chạy.
6. Chọn **Vi phạm thực tế**, mở **Nhật ký vi phạm** và kiểm tra event đã lưu.

## Quy tắc đóng góp quan trọng

- Chọn đúng production owner và technical layer cho mỗi task.
- Đọc README của production owner trước khi đọc hoặc sửa implementation bên trong.
- Không đọc `src/` nếu người dùng không yêu cầu trực tiếp.
- Không tạo top-level directory hoặc module boundary mới khi chưa có quyết định kiến trúc.
- Cập nhật `docs/PROJECT_STRUCTURE.md` khi filesystem thay đổi.
- Chỉ commit khi người dùng yêu cầu trực tiếp.

Quy định đầy đủ và có tính bắt buộc nằm trong [AGENTS.md](AGENTS.md).

## License

MIT
