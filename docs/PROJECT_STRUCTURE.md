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
│   │   │   │   ├── ppe_requirements.py # Persisted PPE requirement REST resource
│   │   │   │   ├── statistics.py  # Compliance & violation metrics
│   │   │   │   └── websocket.py   # Alert and frame-inference WebSockets
│   │   │   └── router.py
│   │   ├── core/        # Typed Settings (Pydantic), CORS & DB Engine
│   │   │   ├── config.py
│   │   │   └── database.py
│   │   ├── integrations/ # Provider adapters; no safety decisions
│   │   │   ├── README.md
│   │   │   └── ppe_vision.py # Adapter to the public vision PPE facade
│   │   ├── models/      # SQLAlchemy ORM models by resource
│   │   │   ├── event.py
│   │   │   └── ppe_requirement.py
│   │   ├── schemas/     # Pydantic validation schemas
│   │   │   ├── analysis.py
│   │   │   ├── event.py
│   │   │   ├── ppe_requirement.py
│   │   │   └── statistics.py
│   │   ├── services/    # Core Services & AI Reasoning
│   │   │   ├── analysis_service.py
│   │   │   ├── event_service.py
│   │   │   ├── frame_inference_service.py # YOLO, foot point and polygon evaluation
│   │   │   ├── llm_service.py     # AI Agent reasoning & recommendation service
│   │   │   ├── ppe_requirement_service.py # PPE persistence and alert rule
│   │   │   └── statistics_service.py
│   │   └── main.py      # FastAPI App entrypoint
│   ├── migrations/      # Alembic DB Migrations
│   │   └── versions/     # Ordered, reversible Alembic revisions
│   │       ├── README.md
│   │       └── 20260806_01_add_ppe_requirements.py
│   └── tests/           # Pytest API & Agent test suite
│       ├── conftest.py
│       ├── test_agent.py
│       ├── test_analysis.py
│       ├── test_events.py
│       ├── test_frame_inference_ppe.py
│       ├── test_ppe_requirements.py
│       └── test_statistics.py
├── vision/              # Framework- and persistence-independent CV observations
│   ├── README.md
│   ├── api.py           # Public PPE observation facade called through backend integration
│   └── tests/           # Unit tests for vision-only behavior
│       ├── README.md
│       └── test_api.py
├── frontend/            # React 19 + TypeScript + Vite dashboard
│   ├── src/
│   │   ├── api/         # REST configuration/events and WebSocket inference
│   │   │   └── ppe-requirements.ts # Shared PPE requirement transport
│   │   ├── components/  # Shared application shell
│   │   ├── features/
│   │   │   ├── monitor/ # Video, zone, Canvas and frame sampling
│   │   │   ├── alerts/  # Rule result and Human-in-the-Loop review
│   │   │   ├── events/  # Acknowledged violation history
│   │   │   ├── rules/   # PPE requirement switches and explicit-save state
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
├── models/              # Git LFS-managed baseline and PPE model checkpoints
│   ├── README.md        # Provenance, checksums, licenses and class mapping
│   ├── ppe_yolov8n.pt  # SH17 YOLOv8n PPE-presence checkpoint
│   └── yolo11n.pt      # Person-detection baseline checkpoint
├── docs/                # Problem statement, structure docs, technical guides and documentation index
│   ├── README.md                    # Documentation catalog
│   ├── PROJECT_STRUCTURE.md         # Current project structure (maintained)
│   └── FUTURE_PROJECT_STRUCTURE.md  # Future structure, ownership and migration guide (read-only)
├── specs/               # Product requirements and PRD-aligned user story backlog
│   ├── README.md
│   ├── PRD.md
│   ├── USER_STORIES_LIST.md
│   ├── US-01.md ... US-06.md  # Detailed specs for completed user stories
│   ├── US-07/           # Detailed implementation package for US-07
│   │   └── US-07-SPEC.md
│   └── backlog/         # Remaining MVP and advanced user stories
│       └── README.md
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
