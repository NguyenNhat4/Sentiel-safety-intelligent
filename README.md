# AI Agent Giám Sát An Toàn PPE & Khu Vực Nguy Hiểm Bằng Computer Vision

> Tóm tắt 1 câu: Thiếu giám sát an toàn liên tục tại nhà máy → AI Agent phân tích camera theo thời gian thực (YOLO + OpenCV) cho Cán bộ an toàn và Quản lý khu vực.

## Vấn đề (Problem)

📍 Thực trạng: Nhà máy có khu vực nguy hiểm (máy dập, xe nâng, hóa chất) yêu cầu đội mũ/kính/găng đúng quy định và không xâm nhập vùng cấm; giám sát bằng người không xuể, vi phạm dễ bị bỏ sót.
🎯 Vấn đề: Cần AI Agent phân tích luồng camera phát hiện thiếu PPE và người xâm nhập vùng cấm khi máy đang chạy, cảnh báo realtime, ghi nhận vi phạm và thống kê tuân thủ theo khu vực/ca.
🔒 Ràng buộc: Cảnh báo nguy hiểm nghiêm trọng (người trong vùng nguy hiểm) escalate ngay tới người phụ trách (HITL); tôn trọng quyền riêng tư (làm mờ danh tính, chỉ lưu vi phạm); bảo mật dữ liệu hình ảnh; cân bằng độ chính xác/false alarm.

## Giải pháp (Solution)

Sản phẩm giám sát an toàn tự động bằng Computer Vision:
- Feature 1: **Phát hiện thiếu PPE & xâm nhập vùng cấm** bằng YOLO pretrained và OpenCV polygon zone.
- Feature 2: **Cảnh báo realtime** thông qua FastAPI WebSocket cho Frontend React.
- Feature 3: **Quản lý & Thống kê vi phạm** lưu trữ vào PostgreSQL, Dashboard theo khu vực và ca.
- Feature 4: **Đảm bảo Privacy** tự động làm mờ khuôn mặt danh tính người vi phạm.

## Target User

- Primary: Cán bộ an toàn (Safety Officer) - Nhận cảnh báo realtime, đánh giá vi phạm, escalate.
- Secondary: Quản lý khu vực (Zone Manager) - Theo dõi thống kê tuân thủ, dashboard.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Computer Vision | Python, Ultralytics YOLO, OpenCV, ByteTrack |
| Backend | FastAPI + SQLAlchemy |
| Frontend | React + TypeScript + Vite |
| Database | PostgreSQL |
| DevOps | Docker Compose |

## Quick Start

```bash
# 1. Clone repo
git clone https://github.com/AI20K-Build-Cohort-2/P-047.git
cd P-047

# 2. Setup environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Start Backend & Database
docker-compose up -d db
uvicorn backend.app.main:app --reload

# 4. Start Frontend
cd frontend
npm install
npm run dev
```

## Project Structure

### Cấu trúc hiện tại (Current Project Structure)

```text
P-047/
├── backend/             # Modular Monolith FastAPI Backend
│   ├── app/
│   │   ├── api/         # API Routers (v1 REST endpoints, WebSocket & AI Safety Agent)
│   │   │   ├── v1/
│   │   │   │   ├── agent.py       # AI Safety Agent chat & recommendation endpoint
│   │   │   │   ├── analysis.py    # Video stream analysis orchestration
│   │   │   │   ├── events.py      # Safety violation event management & ACK
│   │   │   │   ├── statistics.py  # Compliance & violation metrics
│   │   │   │   └── websocket.py   # Realtime alert push (/ws/alerts)
│   │   │   └── router.py
│   │   ├── core/        # Typed Settings (Pydantic), CORS & DB Engine
│   │   │   ├── config.py
│   │   │   └── database.py
│   │   ├── models/      # SQLAlchemy ORM Models (SafetyEvent)
│   │   │   └── event.py
│   │   ├── schemas/     # Pydantic validation schemas
│   │   │   ├── analysis.py
│   │   │   ├── event.py
│   │   │   └── statistics.py
│   │   ├── services/    # Core Services & AI Reasoning
│   │   │   ├── analysis_service.py
│   │   │   ├── event_service.py
│   │   │   ├── llm_service.py     # AI Agent reasoning & recommendation service
│   │   │   └── statistics_service.py
│   │   └── main.py      # FastAPI App entrypoint
│   ├── migrations/      # Alembic DB Migrations
│   └── tests/           # Pytest API & Agent test suite
│       ├── conftest.py
│       ├── test_agent.py
│       ├── test_analysis.py
│       ├── test_events.py
│       └── test_statistics.py
├── vision/              # Computer Vision pipeline (YOLO & OpenCV)
├── frontend/            # React + TypeScript + Vite Dashboard UI
├── data/                # Sample video streams and test data
├── docs/                # Project documentation
├── docker-compose.yml
└── README.md
```

**Giải thích:**
Dự án đã được khởi tạo phân hệ **`backend/`** kế thừa các best-practice từ `src/` (như cấu hình Pydantic typed settings, tích hợp LangChain/OpenAI LLM Safety Agent cho bài toán tư vấn xử lý sự cố an toàn, tích hợp WebSocket realtime và bộ test suite toàn diện).

### Cấu trúc tương lai (Future Project Structure)

Trong các phase tiếp theo, dự án hoàn thiện kiến trúc Modular Monolith để kết nối hoàn chỉnh giữa Computer Vision Pipeline (`vision/`), Web Backend (`backend/`), và Dashboard (`frontend/`):

```text
P-047/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── agent.py
│   │   │       ├── analysis.py
│   │   │       ├── events.py
│   │   │       ├── statistics.py
│   │   │       └── websocket.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── database.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── analysis_service.py
│   │   │   ├── event_service.py
│   │   │   ├── llm_service.py
│   │   │   └── statistics_service.py
│   │   └── main.py
│   ├── migrations/
│   └── tests/
│
├── vision/
│   ├── detection/
│   │   ├── person_detector.py
│   │   └── ppe_detector.py
│   ├── tracking/
│   ├── association/
│   ├── zones/
│   ├── privacy/
│   ├── rules/
│   ├── pipeline.py
│   └── tests/
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── features/
│   │   │   ├── monitor/
│   │   │   ├── alerts/
│   │   │   ├── events/
│   │   │   └── dashboard/
│   │   └── types/
│   └── package.json
│
├── data/
│   ├── demo/
│   ├── edge-cases/
│   └── expected-results.json
│
├── contracts/
│   ├── detection.schema.json
│   └── event.schema.json
│
├── docs/
│   ├── architecture.md
│   ├── rules.md
│   └── limitations.md
│
├── docker-compose.yml
└── README.md
```

**Giải thích:**
Cấu trúc tương lai đảm bảo sự phân tách trách nhiệm rõ ràng (separation of concerns):
1. **`vision/`**: Luồng Computer Vision chạy độc lập để nhận diện người, trang bị PPE, kiểm tra vùng polygon nguy hiểm và làm mờ khuôn mặt.
2. **`backend/`**: Gateway tích hợp REST API, WebSocket realtime, cơ sở dữ liệu PostgreSQL và AI Safety Agent (LLM) hỗ trợ phân tích/đề xuất xử lý sự cố.
3. **`frontend/`**: Giao diện React SPA trực quan dành cho Cán bộ An toàn & Quản lý Khu vực.
4. **`contracts/`**: Chuẩn hóa schema giao tiếp giữa Vision worker và Backend API.


## License

MIT
