# P-047 — Context Map

P-047 là ứng dụng web dùng Computer Vision để hỗ trợ giám sát an toàn trong nhà máy. Hệ thống phân tích video hoặc ảnh mô phỏng, phát hiện người, kiểm tra PPE, xác định xâm nhập vùng nguy hiểm, đưa cảnh báo cho con người xác minh và lưu bằng chứng đã bảo vệ danh tính.

Đây là **điểm bắt đầu và context map duy nhất của repository**. Đọc nó trước khi thực hiện task để chọn đúng lượng tài liệu tối thiểu; các tài liệu con phải độc lập, không tạo catalog/link map mới.

## Bài toán

Nhân sự an toàn khó theo dõi liên tục nhiều khu vực có máy dập, xe nâng hoặc hóa chất. Vi phạm PPE và xâm nhập vùng cấm có thể bị bỏ sót hoặc cảnh báo chậm.

Hệ thống hướng tới phát hiện người cùng PPE theo profile `hat_vest_v1` (mũ và áo phản quang), kiểm tra polygon vùng nguy hiểm, cảnh báo realtime có Human-in-the-Loop, chống event trùng, lưu snapshot đã bảo vệ danh tính và thống kê tuân thủ. Xâm nhập vùng nguy hiểm đang bật là vi phạm bất kể trạng thái máy; trạng thái máy là ngữ cảnh vận hành và chỉ gate cảnh báo PPE.

## Người dùng và phạm vi

| Vai trò | Nhu cầu chính |
|---|---|
| `system_admin` | Giám sát an toàn và quản trị tài khoản, vai trò, mật khẩu tạm |
| `safety_manager` | Theo dõi, review và xác nhận vi phạm/false alarm |
| `area_manager` | Xem dashboard tuân thủ và sự kiện khu vực phụ trách |

Dự án có hai giai đoạn:

1. Đóng MVP với video/ảnh mô phỏng, nhiều vùng nguy hiểm trên một stream, PPE, HITL, privacy, event log, authentication và dashboard cơ bản.
2. Giao bản nâng cao trong 5 tuần với khu vực/ca, confidence triage, escalation, dashboard quản trị, báo cáo và cloud operations.

Camera nhà máy thật, PLC, tự động dừng máy và xử lý đồng thời nhiều stream không thuộc phạm vi đã cam kết.

## Trạng thái và kiến trúc

Baseline hiện có:

- React 19 + TypeScript + Vite cho monitor, FastAPI cho REST/WebSocket và frontend build.
- Upload video local; tạo, lưu nhiều vùng bốn điểm không chồng nhau; zone intrusion đang bật luôn cảnh báo, còn machine state chỉ gate PPE.
- YOLO11m Safety chạy một lần mỗi frame với `person`, `hat`, `vest`; `person` là nguồn canonical cho tracking/zone, PPE công khai chỉ dùng `hat`/`vest`.
- ByteTrack theo phiên video, chống review/event lặp theo occurrence, HITL review và snapshot đã che danh tính.
- PostgreSQL là database duy nhất cho local, test và deployment; không dùng SQLite hoặc database fallback. Session authentication hỗ trợ ba role.

Các khoảng trống lớn là benchmark/calibration trên dữ liệu nhà máy, authorization nghiệp vụ đầy đủ, zone/shift CRUD, escalation và reporting. YuNet production face redaction đã có person fallback fail-closed; trạng thái mới nhất nằm trong [PROGRESS.md](PROGRESS.md).

```text
React frontend
    ↓ REST / WebSocket contract
FastAPI modular monolith
    ↓ public facade
Vision pipeline (YOLO + tracking + zone + privacy)
    ↓
PostgreSQL / blurred object storage
```

Chi tiết boundary và dependency direction: [ARCHITECTURE.md](ARCHITECTURE.md). Sơ đồ components và data flow runtime: [System diagrams](docs/architecture_diagram.md).

## Đọc theo task

| Khi cần | Đọc tài liệu/nguồn |
|---|---|
| Chạy dự án, cấu hình môi trường hoặc thử API | [README.md](README.md) |
| Cấu hình CI, release Railway hoặc rollback | [CI/CD và Railway release](docs/CI_CD.md) |
| Hiểu vấn đề và đầu ra | [Problem Statement](docs/project-problem-statement.md) |
| Hiểu phạm vi MVP | [PRD](specs/PRD.md) |
| Chọn story và acceptance criteria | [User Story Backlog](specs/USER_STORIES_LIST.md) |
| Chuẩn bị task implementation đã được phê duyệt | [Implementation plans](docs/plans/README.md) |
| Đọc frame alert rule và luồng inference | [Alert Rule Contract](docs/alert-rule-contract.md) |
| Xem tiến độ hoặc quyết định đã chốt | [PROGRESS.md](PROGRESS.md), [DECISIONS.md](DECISIONS.md) |
| Tuân thủ workflow AI/contributor | [AGENTS.md](AGENTS.md) |
| Hiểu kiến trúc hệ thống | [ARCHITECTURE.md](ARCHITECTURE.md), [System diagrams](docs/architecture_diagram.md) |
| Xem filesystem hiện có | [Current Project Structure](docs/PROJECT_STRUCTURE.md) |
| Sửa production code | [Future Project Structure](docs/FUTURE_PROJECT_STRUCTURE.md), rồi README của owner |
| Sửa REST/WebSocket payload | FastAPI routes/Pydantic schemas, frontend wire types và test liên quan; [backend README](backend/README.md) cho protocol inference |
| Sửa database/query/migration | ORM models, Alembic migrations và backend tests liên quan |
| PPE hat/vest | [US-28](specs/done/US-28.md), [US-07](specs/done/US-07-SPEC.md), [alert rule contract](docs/alert-rule-contract.md) |
| Tracking và chống event trùng | [US-08](specs/done/US-08-SPEC.md) |
| Audit quyết định sự kiện US-16 | [US-16](specs/done/US-16.md), [implementation plan](docs/plans/2026-08-15-001-feat-us16-event-decision-audit-plan.md) |
| Multi-zone | [US-27](specs/done/US-27-MULTI-ZONE-SPEC.md) |
| Dataset/evaluation US-13 | [dataset guide](docs/US-13-task2-datapreparation.md), [evaluation workspace](data/evaluation/README.md) |
| Operational JSONL metrics | [Operational Metrics](docs/operational-metrics.md) |
| Hiểu/tải thử streamer nhiều client và bộ nhớ MJPEG | [Streamer concurrency and memory](docs/streamer-concurrency-and-memory.md) |
| Hiểu hoặc vận hành luồng CCTV RTSP, MediaMTX, Railway và HLS/WebRTC | [RTSP CCTV media solution](docs/RTSP_CCTV_MEDIA_SOLUTION.md), [streamer README](streamer/README.md), [implementation plan](docs/plans/2026-08-21-001-feat-rtsp-cctv-media-gateway-plan.md) |
| Cài Python với uv | [uv Setup Guide](docs/guide/setup/uv-setup.md) |
| Quy trình phối hợp AI | [AI Team Workflow](docs/AI_TEAM_WORKFLOW.md) |

Các executable definition (route, schema, frontend wire type, ORM, migration và test) là nguồn sự thật hiện hành. Breaking change cần người dùng cho phép, decision record trong `DECISIONS.md`, cùng compatibility test hoặc migration.
