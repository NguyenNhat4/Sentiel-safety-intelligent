# Cấu Trúc Dự Án Hiện Tại (Current Project Structure)

Tài liệu này chi tiết hóa cấu trúc thư mục hiện tại của dự án **P-047: AI Agent Giám Sát An Toàn PPE & Khu Vực Nguy Hiểm Bằng Computer Vision**. Cấu trúc đích được quản lý riêng; mọi thay đổi boundary phải có quyết định kiến trúc mới.

---

## Cấu trúc hiện tại (Current Project Structure)

```text
P-047/
├── alembic.ini          # Alembic entrypoint for backend migrations
├── backend/             # Modular Monolith FastAPI Backend
│   ├── app/
│   │   ├── api/         # API Routers (v1 REST endpoints, WebSocket & AI Safety Agent)
│   │   │   ├── v1/
│   │   │   │   ├── agent.py       # AI Safety Agent chat & recommendation endpoint
│   │   │   │   ├── analysis.py    # Video stream analysis orchestration
│   │   │   │   ├── auth.py        # Authentication and system-admin account APIs
│   │   │   │   ├── events.py      # Safety violation event management & ACK
│   │   │   │   ├── monitoring_zones.py # Revisioned per-camera zone collection
│   │   │   │   ├── operational_metrics.py # Read-only JSONL operational metrics aggregate
│   │   │   │   ├── ppe_requirements.py # Persisted PPE requirement REST resource
│   │   │   │   ├── statistics.py  # Compliance & violation metrics
│   │   │   │   └── websocket.py   # Alert and frame-inference WebSockets
│   │   │   └── router.py
│   │   ├── core/        # Typed Settings (Pydantic), CORS & DB Engine
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── operational_metrics.py # Rotated privacy-safe JSONL writer
│   │   │   └── startup_validation.py # Production model and writable-volume validation
│   │   ├── integrations/ # Provider adapters; no safety decisions
│   │   │   ├── README.md
│   │   │   ├── person_tracking.py # Adapter to session-isolated ByteTrack
│   │   │   └── ppe_vision.py # Cached adapter to public SH17 PPE/redaction facade
│   │   ├── models/      # SQLAlchemy ORM models by resource
│   │   │   ├── event.py
│   │   │   ├── monitoring_zone.py
│   │   │   ├── ppe_requirement.py
│   │   │   └── user.py
│   │   ├── schemas/     # Pydantic validation schemas
│   │   │   ├── analysis.py
│   │   │   ├── auth.py
│   │   │   ├── event.py
│   │   │   ├── monitoring_zone.py
│   │   │   ├── ppe_requirement.py
│   │   │   ├── operational_metrics.py
│   │   │   └── statistics.py
│   │   ├── services/    # Core Services & AI Reasoning
│   │   │   ├── auth_service.py
│   │   │   ├── analysis_service.py
│   │   │   ├── event_service.py
│   │   │   ├── frame_inference_service.py # YOLO, foot point and polygon evaluation
│   │   │   ├── llm_service.py     # AI Agent reasoning & recommendation service
│   │   │   ├── monitoring_zone_service.py # Atomic validation and revisioned persistence
│   │   │   ├── ppe_requirement_service.py # PPE persistence and alert rule
│   │   │   ├── operational_metrics_service.py # Bounded JSONL aggregation
│   │   │   ├── violation_tracking_service.py # Session occurrence lifecycle
│   │   │   └── statistics_service.py
│   │   └── main.py      # FastAPI App entrypoint
│   ├── migrations/      # Alembic DB Migrations
│   │   ├── README.md
│   │   └── versions/     # Ordered, reversible Alembic revisions
│   │       ├── README.md
│   │       ├── 20260801_01_create_safety_events.py
│   │       ├── 20260806_01_add_ppe_requirements.py
│   │       ├── 20260807_01_add_event_occurrences.py
│   │       ├── 20260811_01_add_authentication_schema.py
│   │       ├── 20260811_02_add_forced_password_change.py
│   │       └── 20260811_03_add_monitoring_zones.py
│   └── tests/           # Pytest API & Agent test suite
│       ├── conftest.py
│       ├── test_agent.py
│       ├── test_analysis.py
│       ├── test_events.py
│       ├── test_frame_inference_ppe.py
│       ├── test_monitoring_zones.py
│       ├── test_ppe_requirements.py
│       ├── test_operational_metrics.py
│       ├── test_violation_tracking.py
│       └── test_statistics.py
├── vision/              # Framework- and persistence-independent CV observations
│   ├── README.md
│   ├── api.py           # Public PPE, redaction and session-tracking facades
│   ├── pipeline.py      # Pure identity redaction and person-head fallback logic
│   └── tests/           # Unit tests for vision-only behavior
│       ├── README.md
│       ├── test_api.py
│       ├── test_privacy_pipeline.py
│       └── test_tracking.py
├── frontend/            # React 19 + TypeScript + Vite dashboard
│   ├── src/
│   │   ├── api/         # REST configuration/events and WebSocket inference
│   │   │   ├── auth.ts   # Authentication/account transport
│   │   │   ├── monitoring-zones.ts # Revisioned multi-zone REST transport
│   │   │   ├── statistics.ts # Area-dashboard statistics transport
│   │   │   └── ppe-requirements.ts # Shared PPE requirement transport
│   │   ├── components/  # Shared application shell
│   │   ├── features/
│   │   │   ├── auth/    # Login and system-admin account management
│   │   │   ├── area/    # Dedicated area-manager compliance dashboard
│   │   │   ├── monitor/ # Video, multi-zone draft editor, Canvas and frame sampling
│   │   │   ├── alerts/  # Rule result, detection list summary, ReviewModal, and SnapshotOverlay
│   │   │   ├── events/  # Acknowledged violation history
│   │   │   ├── operational-metrics/ # Separate JSONL metrics observability page
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
│   ├── evaluation/      # Committed US-13 templates; real dataset media remains outside Git
│   │   ├── README.md
│   │   ├── shooting-sheet-template.csv
│   │   ├── ground-truth-template.json
│   │   └── manifest-template.json
│   ├── test.mp4         # Local model benchmark input when present
│   └── snapshots/
├── models/              # Git LFS-managed baseline and PPE model checkpoints
│   ├── README.md        # Provenance, checksums, licenses and class mapping
│   ├── ppe_yolov8n.pt  # SH17 YOLOv8n PPE-presence checkpoint
│   └── yolo11n.pt      # Person-detection baseline checkpoint
├── docs/                # Problem statement, structure docs, technical guides and documentation index
│   ├── README.md                    # Documentation catalog
│   ├── PROJECT_STRUCTURE.md         # Current project structure (maintained)
│   ├── FUTURE_PROJECT_STRUCTURE.md  # Future structure, ownership and migration guide (read-only)
│   ├── US-13-task2-datapreparation.md # Custom dataset annotation, split and locking guide
│   ├── operational-metrics.md       # JSONL metrics operation, API, privacy and UI guide
│   └── plans/                       # Implementation-ready plans and their reading guide
├── specs/               # Product requirements and PRD-aligned user story backlog
│   ├── README.md
│   ├── PRD.md
│   ├── USER_STORIES_LIST.md
│   ├── US-01.md ... US-06.md  # Detailed specs for completed user stories
│   ├── done/            # Completed implementation specifications
│   │   ├── README.md
│   │   ├── US-07-SPEC.md
│   │   ├── US-08-SPEC.md
│   │   ├── US-12.md
│   │   └── US-27-MULTI-ZONE-SPEC.md # Completed multi-zone implementation specification
│   └── backlog/         # Remaining MVP and advanced user stories
│       ├── README.md
│       └── US-09.md ... US-26.md
├── scripts/             # Explicit-entrypoint automation and model benchmarks
│   ├── README.md
│   ├── benchmark_model.py
│   ├── bootstrap_legacy_sqlite.py # One-time safe adoption of pre-Alembic local SQLite
│   ├── production_start.py # Docker preflight, migration and one-worker startup
│   ├── docker_smoke.py # Repeatable black-box local Docker smoke check
│   ├── backup_data.py # Timestamped archive of persistent Docker data
│   ├── restore_data.py # Safe restore into empty persistent Docker data
│   └── validate_us13_dataset.py # Validate US-13 evaluation manifest and checksums
├── eval/                # Evaluation reports and benchmark results
│   └── results/
│       ├── report.md
│       └── model-benchmark-report.md
├── src/                 # Legacy LangGraph scaffold; migrate/remove incrementally, no new production code
│   ├── agents/          # Example graph, state, nodes and tools
│   ├── api/             # Legacy chat/status routes
│   ├── models/          # Legacy chat schemas
│   ├── services/        # Legacy LLM factory
│   └── ui/              # Legacy static UI
├── DECISIONS.md         # Single project-wide design decision log
├── PROGRESS.md          # Single project-wide progress tracker
├── ARCHITECTURE.md      # Canonical system architecture and diagrams
├── tests/                # Cross-cutting and automation tests
│   ├── test_bootstrap_legacy_sqlite.py
│   ├── test_startup_validation.py
│   └── test_validate_us13_dataset.py
├── docker-compose.yml
├── requirements.docker.txt # Production-only, CPU/headless Python dependency set
└── README.md
```

### Giải thích
`backend/` là runtime FastAPI hiện hành. `src/` là scaffold LangGraph cũ còn tồn tại trong filesystem nhưng không còn là đích cho production code mới. Ownership, dependency, cách đặt code và lộ trình migration được chốt trong một file duy nhất: `docs/FUTURE_PROJECT_STRUCTURE.md`.
