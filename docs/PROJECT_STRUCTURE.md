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
├── frontend/            # Static HTML/CSS/JavaScript baseline UI
│   ├── index.html       # Upload, four-point zone, inference and review flow
│   ├── styles.css       # Sentinel visual stylesheet brought from src/ui
│   ├── baseline.css     # Functional video and Canvas overrides
│   ├── event-log.css    # Confirmed-violation history cards and responsive layout
│   ├── app.js           # 29-line ES module composition root
│   ├── modules/
│   │   ├── README.md
│   │   ├── config.js
│   │   ├── dom.js
│   │   ├── state.js
│   │   ├── video-controller.js
│   │   ├── video-preview.js
│   │   ├── zone-controller.js
│   │   ├── inference-client.js
│   │   ├── frame-sampler.js
│   │   ├── overlay-renderer.js
│   │   ├── review-controller.js
│   │   ├── event-log-controller.js
│   │   └── ui.js
│   └── README.md
├── data/                # Sample video streams, test data and reviewed snapshots
│   └── snapshots/
├── docs/                # Architecture, technical guides and documentation index
├── specs/               # Product requirements and PRD-aligned user story backlog
│   ├── README.md
│   ├── PRD.md
│   └── USER_STORIES.md
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
│   ├── index.html              # Monitor markup; loads app.js as an ES module
│   ├── styles.css              # Sentinel visual system
│   ├── baseline.css            # Functional video and Canvas states
│   ├── event-log.css           # Confirmed-event history view
│   ├── app.js                  # Small composition root and event wiring
│   ├── modules/
│   │   ├── README.md           # Module boundaries and dependency rules
│   │   ├── config.js           # Sampling interval and backend URL resolution
│   │   ├── dom.js              # Cached DOM element references
│   │   ├── state.js            # Single mutable baseline session state
│   │   ├── video-controller.js # Upload, preview, play, stop and frame capture
│   │   ├── video-preview.js    # Preview-frame selection and paused snapshot
│   │   ├── zone-controller.js  # Four-point selection, drag, delete and reset
│   │   ├── inference-client.js # WebSocket protocol, fallback and backpressure
│   │   ├── frame-sampler.js    # 2 FPS gate and binary JPEG capture delivery
│   │   ├── overlay-renderer.js # Polygon, bounding boxes and foot-point drawing
│   │   ├── review-controller.js # Human review and REST event persistence
│   │   ├── event-log-controller.js # Confirmed events and snapshot history
│   │   └── ui.js               # Status, rules, toast, timer and formatting
│   └── README.md
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
│   └── USER_STORIES.md
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
3. **`frontend/`**: Tiếp tục dùng HTML/CSS/JavaScript native trong baseline, nhưng tách `app.js` thành ES modules theo trách nhiệm. `app.js` chỉ composition/wiring; transport không truy cập DOM, renderer không gọi network, controller review không điều khiển video trực tiếp. Có thể đánh giá SPA framework sau khi baseline và contract ổn định.
4. **`contracts/`**: Chuẩn hóa schema giao tiếp giữa Vision worker và Backend API.
5. **Central tracking**: Root `DECISIONS.md` và `PROGRESS.md` là hai nguồn tracking duy nhất; module không tạo bản riêng.

### Frontend refactor boundaries

Refactor tương lai giữ nguyên UI và wire contract hiện tại; đây là thay đổi cấu trúc, không thay đổi hành vi.

| Module | Owns | Must not own |
|---|---|---|
| `app.js` | Khởi tạo module và nối callbacks | WebSocket protocol, Canvas drawing, business rules |
| `state.js` | Zone, playback, detections and pending-review state | DOM access, socket ownership or side effects |
| `video-controller.js` | Video/file lifecycle and Canvas frame capture | Backend message parsing |
| `video-preview.js` | Preview-frame selection and paused snapshots | Playback or socket ownership |
| `zone-controller.js` | Exactly-four-point editing and normalized coordinates | Person detection or event saving |
| `inference-client.js` | Configure/meta/binary protocol and one-frame backpressure | Review UI or Canvas drawing |
| `frame-sampler.js` | Sampling interval and Canvas-to-JPEG delivery | Socket lifecycle or review decisions |
| `overlay-renderer.js` | Pure rendering from zone and detection inputs | Socket or REST calls |
| `review-controller.js` | Pending candidate, officer decision and `/events` request | Frame sampling |
| `event-log-controller.js` | Confirmed-event navigation, loading, and snapshot cards | Inference or review decisions |
| `ui.js` | Labels, alerts, toast and timer | Session/network ownership |

Target each implementation file to remain near or below 150 lines. Shared state is passed explicitly or imported from `state.js`; modules do not create duplicate mutable state. Native browser modules keep the baseline build-free.
