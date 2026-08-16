# P-047 — AI Agent Giám Sát An Toàn PPE và Khu Vực Nguy Hiểm

P-047 là ứng dụng web dùng Computer Vision để hỗ trợ giám sát an toàn trong nhà máy. Hệ thống phân tích video hoặc ảnh mô phỏng, phát hiện người, kiểm tra PPE, xác định xâm nhập vùng nguy hiểm theo trạng thái máy, đưa cảnh báo cho con người xác minh và lưu bằng chứng đã bảo vệ danh tính.

README này là **điểm bắt đầu và master index của repository**. Nếu chưa biết đọc tài liệu nào, bắt đầu từ phần [Bản đồ tài liệu](#bản-đồ-tài-liệu).

## Bài toán

Nhân sự an toàn khó theo dõi liên tục nhiều khu vực có máy dập, xe nâng hoặc hóa chất. Vi phạm PPE và xâm nhập vùng cấm có thể bị bỏ sót hoặc cảnh báo chậm.

Hệ thống hướng tới:

- Phát hiện người và PPE bắt buộc theo profile `hat_vest_v1`: mũ bảo hộ và áo phản quang.
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
| Quản trị hệ thống (`system_admin`) | Giám sát an toàn và quản trị tài khoản, vai trò, mật khẩu tạm |
| Cán bộ an toàn (`safety_manager`) | Theo dõi, nhận cảnh báo, review, xác nhận vi phạm hoặc false alarm |
| Quản lý khu vực (`area_manager`) | Xem dashboard tuân thủ và sự kiện theo khu vực phụ trách |

## Phạm vi và giới hạn

Dự án đang phát triển theo hai giai đoạn:

1. Đóng MVP với video/ảnh mô phỏng, nhiều vùng nguy hiểm trên một stream, PPE, HITL, privacy, event log, authentication và dashboard cơ bản.
2. Giao bản nâng cao trong 5 tuần với khu vực/ca, confidence triage, escalation, dashboard quản trị, báo cáo và cloud operations.

Camera nhà máy thật, PLC, tự động dừng máy và xử lý đồng thời nhiều stream không thuộc phạm vi đã cam kết. Xem [Problem Statement](docs/project-problem-statement.md), [PRD](specs/PRD.md) và [User Story Backlog](specs/USER_STORIES_LIST.md) để biết phạm vi chính xác.

## Trạng thái hiện tại

Baseline đang hoạt động gồm:

- React 19 + TypeScript + Vite cho giao diện monitor.
- FastAPI phục vụ REST, WebSocket và production frontend build.
- Upload video local, tạo/lưu nhiều vùng bốn điểm không chồng nhau và trạng thái máy riêng cho từng vùng.
- YOLO person detection, foot-point polygon evaluation và frame inference gần realtime.
- Một YOLO11m Safety checkpoint đã pin chạy `person`, `hat`, `vest` đúng một lần mỗi frame; `person` là nguồn canonical cho tracking/zone, còn rule PPE công khai chỉ dùng `hat`/`vest`.
- ByteTrack gán track ID theo phiên video và backend chống review/event lặp cho cùng occurrence.
- HITL review, lưu event đã xác nhận với snapshot đã che danh tính, nhật ký snapshot và thống kê baseline.
- SQLite là mặc định hiện tại cho MVP/local/test; PostgreSQL vẫn được hỗ trợ qua cấu hình `DATABASE_URL` cho môi trường triển khai sau khi được xác thực.
- Đăng nhập bằng session lưu phía server với đúng ba role và workspace phù hợp.

Các khoảng trống quan trọng gồm benchmark/calibration production-ready cho model hat/vest, face detector đã benchmark cho production, authorization đầy đủ trên API nghiệp vụ, zone/shift CRUD, escalation và reporting. Tracking/dedup US-08, authentication persistence và PostgreSQL migration baseline đã được tích hợp. Trạng thái mới nhất luôn nằm trong [PROGRESS.md](PROGRESS.md).

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
| Chuẩn bị và khóa custom dataset cho US-13 | [US-13 Task 2 Dataset Guide](docs/US-13-task2-datapreparation.md) |
| Dùng template và kiểm tra manifest US-13 | [US-13 evaluation workspace](data/evaluation/README.md) |
| Hiểu JSONL metrics, API và UI quan sát hệ thống | [Operational Metrics](docs/operational-metrics.md) |
| Xem implementation plan đã được phê duyệt | [Implementation plans](docs/plans/README.md) |
| Đọc contract rule alert và sơ đồ luồng frame | [Frame Alert Rule Contract](docs/alert-rule-contract.md) |
| Đặc tả triển khai US-07 PPE | [US-07 PPE Specification](specs/done/US-07-SPEC.md) |
| Đặc tả US-08 tracking và chống event trùng | [US-08 Tracking/Dedup Specification](specs/done/US-08-SPEC.md) |
| Đặc tả US-27 đa vùng trên một video | [US-27 Multi-zone Specification](specs/done/US-27-MULTI-ZONE-SPEC.md) |
| Đặc tả US-28 YOLO11m Safety hat/vest | [US-28 YOLO11m Safety Specification](specs/done/US-28.md) |
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

`make setup` creates `.env.development` from `.env.development.example` when it is
missing. Docker Compose separately reads `.env.production`; start from
`.env.production.example` and supply deployment-specific values there.

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

## Docker Compose smoke

```bash
make setup
make docker-up
make docker-smoke
```

Docker Compose nạp `.env.development`, nhưng luôn override `DATABASE_URL` sang PostgreSQL disposable `db` nội bộ để kiểm tra không chạm database developer cấu hình trong file. Sau khi `db` healthy, entrypoint chạy Alembic migration rồi FastAPI khởi động ở development mode và seed demo users idempotent. Các biến còn lại, gồm CORS và S3, lấy từ `.env.development`; dùng credentials development/staging, không dùng credentials production. Khi rollback code, checkout release/source tag trước đó rồi chạy `make docker-up`; chỉ rollback dữ liệu bằng backup đã tạo trước migration nếu schema cũ không tương thích.

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
