# AI Agent Giám Sát An Toàn PPE & Khu Vực Nguy Hiểm Bằng Computer Vision

> Tóm tắt 1 câu: Thiếu giám sát an toàn liên tục tại nhà máy → AI Agent phân tích camera theo thời gian thực (YOLO + OpenCV) cho Cán bộ an toàn và Quản lý khu vực.

## Vấn đề (Problem)

📍 Thực trạng: Nhà máy có khu vực nguy hiểm (máy dập, xe nâng, hóa chất) yêu cầu đội mũ/kính/găng đúng quy định và không xâm nhập vùng cấm; giám sát bằng người không xuể, vi phạm dễ bị bỏ sót.
🎯 Vấn đề: Cần AI Agent phân tích luồng camera phát hiện thiếu PPE và người xâm nhập vùng cấm khi máy đang chạy, cảnh báo realtime, ghi nhận vi phạm và thống kê tuân thủ theo khu vực/ca.
🔒 Ràng buộc: Cảnh báo nguy hiểm nghiêm trọng (người trong vùng nguy hiểm) escalate ngay tới người phụ trách (HITL); tôn trọng quyền riêng tư (làm mờ danh tính, chỉ lưu vi phạm); bảo mật dữ liệu hình ảnh; cân bằng độ chính xác/false alarm.

## Giải pháp (Solution)

Sản phẩm giám sát an toàn tự động bằng Computer Vision:
- Feature 1: **Phát hiện thiếu PPE & xâm nhập vùng cấm** bằng YOLO pretrained và OpenCV polygon zone.
- Feature 2: **Luồng xác minh gần realtime** qua FastAPI frame API và giao diện HTML/CSS/JavaScript.
- Feature 3: **Quản lý & Thống kê vi phạm** lưu trữ vào PostgreSQL, Dashboard theo khu vực và ca.
- Feature 4: **Đảm bảo Privacy** tự động làm mờ khuôn mặt danh tính người vi phạm.

## Target User

- Primary: Cán bộ an toàn (Safety Officer) - Nhận cảnh báo realtime, đánh giá vi phạm, escalate.
- Secondary: Quản lý khu vực (Zone Manager) - Theo dõi thống kê tuân thủ, dashboard.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Computer Vision | Python, Ultralytics YOLO, OpenCV |
| Backend | FastAPI + SQLAlchemy |
| Frontend | HTML, CSS, JavaScript (served by FastAPI) |
| Database | SQLite for the local baseline; PostgreSQL for production |
| DevOps | Docker Compose |

## New Developer Onboarding

Use Python 3.11–3.13 for local development. Python 3.14 currently causes the shared FastAPI `TestClient` suite to stall after collection.

### 1. Install the project

```bash
git clone https://github.com/AI20K-Build-Cohort-2/P-047.git
cd P-047

# Create the environment with a supported Python version, for example Python 3.12
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Local baseline configuration uses data/safety_events.db
cp .env.example .env
```

YOLO downloads/loads its configured model when inference is first used, so the first analyzed frame can be slower than later frames.

### 2. Run the application

```bash
make run
```

The FastAPI process serves both layers:

- Monitor UI: <http://localhost:8000/>
- Swagger REST documentation: <http://localhost:8000/docs>
- ReDoc REST documentation: <http://localhost:8000/redoc>
- Raw OpenAPI schema: <http://localhost:8000/openapi.json>
- Health check: <http://localhost:8000/health>

You should see these important REST routes in Swagger:

- `POST /api/v1/analysis/frame`
- `GET /api/v1/events`
- `POST /api/v1/events`
- `GET /api/v1/events/{event_id}`
- `GET /api/v1/statistics/summary`

The realtime inference endpoint is:

```text
ws://localhost:8000/api/v1/ws/inference
```

It will **not appear in Swagger** because OpenAPI describes HTTP APIs and does not describe WebSocket routes. Its configure/frame/result protocol is documented in [`backend/README.md`](backend/README.md#frame-inference-contract).

If the REST routes are missing from Swagger, verify that the correct application is running:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/openapi.json
```

Stop any old server on port 8000, run `make run` from the repository root, and hard-refresh `/docs`.

### 3. Run tests and checks

Run all repository checks before submitting a change:

```bash
make check
```

Run individual groups while developing:

```bash
# Lint Python
make lint

# Verify Python formatting
make format

# All Python tests
make test

# Backend tests only
PYTHONPATH=. .venv/bin/pytest backend/tests -v

# One focused backend test
PYTHONPATH=. .venv/bin/pytest backend/tests/test_analysis.py::test_zone_entry_does_not_request_review_when_machine_is_stopped -v

# Frontend JavaScript syntax
for file in frontend/app.js frontend/modules/*.js; do node --check "$file"; done
```

Tests use an isolated in-memory SQLite database. They do not write events into the local development database.

### 4. Baseline manual smoke test

1. Open <http://localhost:8000/> and upload a video.
2. Draw exactly four zone points.
3. Set the machine to running and press Play.
4. Confirm that person bounding boxes are rendered.
5. Confirm that playback pauses only when a person's foot point enters the zone while the machine is running.
6. Choose **Vi phạm thực tế**, then manually open **Nhật ký vi phạm** and confirm the event snapshot appears.

## Project Structure

Chi tiết về cấu trúc thư mục dự án (bao gồm cấu trúc hiện tại và định hướng kiến trúc tương lai) đã được chuyển sang tài liệu riêng:

👉 **[docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)**

### Tóm tắt nhanh:
- **`backend/`**: Modular Monolith FastAPI Backend (REST API, WebSocket, AI Safety Agent LLM, SQLAlchemy/PostgreSQL, Pytest).
- **`vision/`**: Computer Vision Pipeline (YOLO detection, ByteTrack tracking, Polygon zone rule check, Privacy face blurring).
- **`frontend/`**: Vanilla HTML/CSS/JavaScript baseline UI cho cán bộ an toàn.
- **`docs/`**: Tài liệu kiến trúc, PRD, cấu trúc dự án và hướng dẫn.
- **`data/`**: Video stream mẫu và dữ liệu kiểm thử.


## License

MIT
