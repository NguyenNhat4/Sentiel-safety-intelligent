# Cấu Trúc Dự Án (Project Structure)

Tài liệu này chi tiết hóa cấu trúc thư mục hiện tại và định hướng kiến trúc mở rộng trong tương lai của dự án **P-047: AI Agent Giám Sát An Toàn PPE & Khu Vực Nguy Hiểm Bằng Computer Vision**.

---

## 1. Cấu trúc hiện tại (Current Project Structure)

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
│   │   │   │   └── websocket.py   # Alert and frame-inference WebSockets
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
│   │   │   ├── frame_inference_service.py # YOLO, foot point and polygon evaluation
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
├── frontend/            # React 19 + TypeScript + Vite dashboard
│   ├── src/
│   │   ├── api/         # REST configuration/events and WebSocket inference
│   │   ├── components/  # Shared application shell
│   │   ├── features/
│   │   │   ├── auth/    # Login experience and role entry-point selection
│   │   │   ├── monitor/ # Video, zone, Canvas and frame sampling
│   │   │   ├── alerts/  # Rule result and Human-in-the-Loop review
│   │   │   ├── events/  # Acknowledged violation history
│   │   │   └── dashboard/ # Reserved dashboard boundary
│   │   ├── styles/      # React CSS entrypoint composing Sentinel styles
│   │   ├── types/       # Typed REST/WebSocket contracts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── index.html       # Vite HTML entrypoint
│   ├── styles.css       # Sentinel visual system
│   ├── baseline.css     # Video and Canvas overrides
│   ├── event-log.css    # Violation history styles
│   ├── API_MOCKS.md     # Temporary frontend API mocks and integration contracts
│   ├── package.json
│   └── vite.config.ts
├── data/                # Sample video streams, test data and reviewed snapshots
│   └── snapshots/
├── docs/                # Architecture, technical guides and documentation index
├── specs/               # Product requirements and PRD-aligned user story backlog
│   ├── README.md
│   ├── PRD.md
│   ├── USER_STORIES_LIST.md
│   ├── US-01.md ... US-06.md  # Detailed specs for completed user stories
│   └── backlog/         # Incomplete MVP and five-week advanced user stories
│       ├── README.md
│       └── US-07.md ... US-26.md
├── DECISIONS.md         # Single project-wide design decision log
├── PROGRESS.md          # Single project-wide progress tracker
├── docker-compose.yml
└── README.md
```

### Giải thích
Dự án đã được khởi tạo phân hệ **`backend/`** kế thừa các best-practice từ `src/` (như cấu hình Pydantic typed settings, tích hợp LangChain/OpenAI LLM Safety Agent cho bài toán tư vấn xử lý sự cố an toàn, tích hợp WebSocket realtime và bộ test suite toàn diện).

---

## 2. Cấu trúc tương lai (Future Project Structure)

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
│   │   │   ├── frame_inference_service.py
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
│   │   ├── api/                 # REST and WebSocket transport
│   │   ├── components/          # Shared layout components
│   │   ├── features/
│   │   │   ├── monitor/         # Live video and zone editing
│   │   │   ├── alerts/          # HITL review
│   │   │   ├── events/          # Confirmed history
│   │   │   └── dashboard/       # Compliance metrics
│   │   ├── styles/               # React CSS entrypoint
│   │   ├── types/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── data/
│   ├── demo/
│   ├── edge-cases/
│   ├── snapshots/
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
├── specs/
│   ├── README.md
│   ├── PRD.md
│   ├── USER_STORIES_LIST.md
│   ├── US-01.md ... US-06.md
│   └── backlog/
│       ├── README.md
│       └── US-07.md ... US-26.md
│
├── DECISIONS.md
├── PROGRESS.md
├── docker-compose.yml
└── README.md
```

### Giải thích
Cấu trúc tương lai đảm bảo sự phân tách trách nhiệm rõ ràng (separation of concerns):
1. **`vision/`**: Luồng Computer Vision chạy độc lập để nhận diện người, trang bị PPE, kiểm tra vùng polygon nguy hiểm và làm mờ khuôn mặt.
2. **`backend/`**: Gateway tích hợp REST API, WebSocket realtime, cơ sở dữ liệu PostgreSQL và AI Safety Agent (LLM) hỗ trợ phân tích/đề xuất xử lý sự cố.
3. **`frontend/`**: React + TypeScript SPA theo feature boundaries. Transport không render UI, Canvas utilities không gọi network, và monitor giữ socket/frame state trong refs để không tạo queue hoặc stale closure. Vite phục vụ development; FastAPI phục vụ `frontend/dist` trong production.
4. **`contracts/`**: Chuẩn hóa schema giao tiếp giữa Vision worker và Backend API.
5. **Central tracking**: Root `DECISIONS.md` và `PROGRESS.md` là hai nguồn tracking duy nhất; module không tạo bản riêng.

### Frontend boundaries

React refactor giữ nguyên UI và wire contract đã xác nhận; đây là thay đổi cấu trúc, không thay đổi hành vi nghiệp vụ.

| Area | Owns | Must not own |
|---|---|---|
| `api/` | URL resolution, REST requests, WebSocket protocol and backpressure | React rendering or Canvas drawing |
| `components/` | Shared shell and navigation | Backend requests or monitor session state |
| `features/monitor/` | Video lifecycle, zone editing, sampling, Canvas and orchestration | Backend inference implementation |
| `features/alerts/` | Rule results, snapshot and review controls | Frame sampling or socket ownership |
| `features/events/` | Acknowledged event loading and cards | Inference or pending review decisions |
| `types/` | REST/WebSocket contract types | Mutable runtime state |

React state owns renderable state; refs own video, Canvas, WebSocket and per-frame mutable values. The refactor preserves the validated UI behavior and existing backend wire contracts.
