# Cấu Trúc Dự Án Hiện Tại (Current Project Structure)

Tài liệu này chi tiết hóa cấu trúc thư mục hiện tại của dự án **P-047: AI Agent Giám Sát An Toàn PPE & Khu Vực Nguy Hiểm Bằng Computer Vision**. Cấu trúc đích được quản lý riêng; mọi thay đổi boundary phải có quyết định kiến trúc mới.

---

## Cấu trúc hiện tại (Current Project Structure)

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
│   ├── package.json
│   └── vite.config.ts
├── data/                # Sample video streams, test data and reviewed snapshots
│   └── snapshots/
├── models/              # Machine learning model weights (YOLO & PPE weights)
│   ├── README.md
│   ├── ppe_yolov8n.pt
│   └── yolo11n.pt
├── docs/                # Problem statement, structure docs, technical guides and documentation index
│   ├── README.md                    # Documentation catalog
│   ├── PROJECT_STRUCTURE.md         # Current project structure (maintained)
│   └── FUTURE_PROJECT_STRUCTURE.md  # Future structure, ownership and migration guide (read-only)
├── specs/               # Product requirements and PRD-aligned user story backlog
│   ├── README.md
│   ├── PRD.md
│   ├── USER_STORIES_LIST.md
│   ├── US-01.md ... US-06.md  # Detailed specs for completed user stories
│   └── backlog/         # Incomplete MVP and five-week advanced user stories
│       ├── README.md
│       └── US-07.md ... US-26.md
├── src/                 # Legacy LangGraph scaffold; migrate/remove incrementally, no new production code
│   ├── agents/          # Example graph, state, nodes and tools
│   ├── api/             # Legacy chat/status routes
│   ├── models/          # Legacy chat schemas
│   ├── services/        # Legacy LLM factory
│   └── ui/              # Legacy static UI
├── DECISIONS.md         # Single project-wide design decision log
├── PROGRESS.md          # Single project-wide progress tracker
├── ARCHITECTURE.md      # Canonical system architecture and diagrams
├── docker-compose.yml
└── README.md
```

### Giải thích
`backend/` là runtime FastAPI hiện hành. `src/` là scaffold LangGraph cũ còn tồn tại trong filesystem nhưng không còn là đích cho production code mới. Ownership, dependency, cách đặt code và lộ trình migration được chốt trong một file duy nhất: `docs/FUTURE_PROJECT_STRUCTURE.md`.
