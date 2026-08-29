# Cấu Trúc Dự Án Hiện Tại (Current Project Structure)

Tài liệu này chi tiết hóa cấu trúc thư mục hiện tại của dự án **P-047: AI Agent Giám Sát An Toàn PPE & Khu Vực Nguy Hiểm Bằng Computer Vision**. Cấu trúc đích được quản lý riêng; mọi thay đổi boundary phải có quyết định kiến trúc mới.

---

## Cấu trúc hiện tại (Current Project Structure)

```text
P-047/
├── .github/             # GitHub Actions CI, Railway deploy/rollback and dependency audit
│   └── workflows/
│       ├── ci.yml        # Required PR/main checks and Docker Hub :latest publication
│       ├── deploy-railway.yml # CI-gated Railway image redeploy and health verification
│       └── dependency-audit.yml # Non-blocking nightly dependency audit
├── alembic.ini          # Alembic entrypoint for backend migrations
├── docker-compose.yml   # PostgreSQL and backend with volume-backed media assets
├── Dockerfile.ai        # CPU proof image for the standalone Safety Vision worker
├── Dockerfile.ai.gpu    # CUDA 12.8 image for the RunPod Safety Vision worker
├── requirements.ai.txt  # Minimal runtime dependencies for the worker image
├── backend/             # Modular Monolith FastAPI Backend
│   ├── app/
│   │   ├── api/         # API Routers (v1 REST endpoints, WebSocket & AI Safety Agent)
│   │   │   ├── v1/
│   │   │   │   ├── agent.py       # AI Safety Agent chat & recommendation endpoint
│   │   │   │   ├── analysis.py    # Legacy single-frame inference compatibility
│   │   │   │   ├── auth.py        # Authentication and system-admin account APIs
│   │   │   │   ├── camera_configurations.py # Atomic asset, zone and PPE configuration
│   │   │   │   ├── camera_sessions.py # Explicit Run, Replay and lifecycle queries
│   │   │   │   ├── events.py      # Safety violation event management & ACK
│   │   │   │   ├── media_assets.py # Authenticated media inventory, upload and content
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
│   │   │   ├── ppe_vision.py # Unified YOLO11n Safety KD person/tracking/PPE adapter
│   │   │   ├── remote_vision.py # Versioned outbound HTTP Safety Vision adapter
│   │   │   ├── privacy_vision.py # Cached YuNet-first, person-fallback privacy adapter
│   │   │   ├── media_storage.py # Railway Bucket presigned media and cache transfer adapter
│   │   │   └── telegram_notifications.py # Telegram Bot API delivery adapter
│   │   ├── models/      # SQLAlchemy ORM models by resource
│   │   │   ├── camera_configuration.py # Fixed camera configuration and session lifecycle
│   │   │   ├── event.py
│   │   │   ├── media_asset.py # Backend-owned image/video asset registry
│   │   │   ├── monitoring_zone.py
│   │   │   ├── ppe_requirement.py
│   │   │   ├── user.py
│   │   │   └── vision_tracking_state.py # PostgreSQL v2 continuation-state row
│   │   ├── schemas/     # Pydantic validation schemas
│   │   │   ├── analysis.py
│   │   │   ├── auth.py
│   │   │   ├── camera_configuration.py
│   │   │   ├── camera_session.py
│   │   │   ├── event.py
│   │   │   ├── health.py # Typed public /health dependency-readiness response
│   │   │   ├── media_asset.py
│   │   │   ├── monitoring_zone.py
│   │   │   ├── ppe_requirement.py
│   │   │   ├── operational_metrics.py
│   │   │   ├── remote_vision.py # Strict v1/v2 worker wire contracts and portable state DTO
│   │   │   └── statistics.py
│   │   ├── services/    # Core Services & AI Reasoning
│   │   │   ├── alert_notification_service.py # Area-scoped alert recipient routing
│   │   │   ├── auth_service.py
│   │   │   ├── camera_configuration_service.py # Atomic asset, zones and rules transaction
│   │   │   ├── camera_session_runtime.py # Direct finite image/video inference sessions
│   │   │   ├── event_service.py
│   │   │   ├── frame_inference_service.py # YOLO, foot point and polygon evaluation
│   │   │   ├── camera_detection_hub.py # Latest-only per-camera metadata fan-out
│   │   │   ├── llm_service.py     # AI Agent reasoning & recommendation service
│   │   │   ├── media_asset_service.py # Atomic upload, validation and protected deletion
│   │   │   ├── monitoring_zone_service.py # Atomic validation and revisioned persistence
│   │   │   ├── ppe_requirement_service.py # PPE persistence and alert rule
│   │   │   ├── operational_metrics_service.py # Bounded JSONL aggregation
│   │   │   ├── violation_tracking_service.py # Session occurrence lifecycle
│   │   │   ├── vision_tracking_state_service.py # TTL, validation and revision/frame CAS
│   │   │   └── statistics_service.py
│   │   ├── vision_worker.py # Standalone FastAPI Safety Vision worker entrypoint
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
│   │       ├── 20260811_03_add_monitoring_zones.py
│   │       ├── 20260813_01_migrate_ppe_profile_hat_vest.py
│   │       ├── 20260814_01_add_user_area_telegram.py
│   │       ├── 20260815_02_add_restricted_area_detection.py # Per-zone whole-camera person-alert switch
│   │       ├── 20260815_03_add_event_track_identity.py # One event per session-local tracked person
│   │       └── 20260819_01_add_stream_configuration.py # Persisted active mock stream
│   │       └── 20260819_01_add_event_decision_audit.py # Immutable reviewed-event context and retention deadlines
│   │       ├── 20260821_01_add_zone_intrusion_rule.py # Per-zone intrusion enable switch
│   │       └── 20260822_01_camera_wide_machine_state.py # Camera mapping machine-state compatibility contract
│   │       └── 20260823_01_add_media_assets_and_camera_sessions.py # US-29 direct media runtime
│   │       ├── 20260823_02_add_media_storage_backend.py # Bucket/volume storage metadata
│   │       ├── 20260824_01_repair_sqlite_camera_session_index.py # Legacy replay-safe index repair
│   │       ├── 20260824_02_camera_wide_ppe_requirements.py # Camera-wide hat/vest requirements
│   │       └── 20260825_01_add_vision_tracking_states.py # v2 JSONB continuation state and TTL index
│   └── tests/           # Pytest API & Agent test suite
│       ├── conftest.py
│       ├── test_agent.py
│       ├── test_alert_notifications.py
│       ├── test_camera_detection_hub.py
│       ├── test_analysis.py
│       ├── test_events.py
│       ├── test_event_audit.py
│       ├── test_event_audit_migration.py
│       ├── test_frame_inference_ppe.py
│       ├── test_remote_vision.py # Outbound worker adapter contract
│       ├── test_vision_tracking_state.py # TTL, validation and CAS persistence behavior
│       ├── test_vision_tracking_state_migration.py # Reversible JSONB migration contract
│       ├── test_vision_worker.py # Standalone worker API contract
│       ├── test_monitoring_zones.py
│       ├── test_ppe_requirements.py
│       ├── test_ppe_profile_migration.py
│       ├── test_operational_metrics.py
│       ├── test_camera_session_index_migration.py # SQLite replay-after-completion migration regression
│       ├── test_violation_tracking.py
│       ├── test_statistics.py
│       └── test_us29_media_runtime.py # Upload, aggregate save and direct-file sessions
├── vision/              # Framework- and persistence-independent CV observations
│   ├── README.md
│   ├── api.py           # Public hat/vest, independent redaction and session-tracking facades
│   ├── face_detection.py # Thread-safe OpenCV YuNet provider
│   ├── pipeline.py      # Face blur, per-person fallback and post-redaction annotation
│   ├── tracking_state.py # Versioned JSON-safe ByteTrack continuation codec
│   └── tests/           # Unit tests for vision-only behavior
│       ├── README.md
│       ├── test_api.py
│       ├── test_face_detection.py
│       ├── test_privacy_pipeline.py
│       └── test_tracking.py
├── frontend/            # React 19 + TypeScript + Vite dashboard
│   ├── src/
│   │   ├── api/         # REST configuration/events and WebSocket inference
│   │   │   ├── camera-detection-client.ts # Authenticated camera metadata socket
│   │   │   ├── auth.ts   # Authentication/account transport
│   │   │   ├── vision-worker-compare.ts # Dev-only typed CPU/CUDA worker client and latency summary
│   │   │   ├── camera-configurations.ts # Atomic fixed-camera configuration transport
│   │   │   ├── media-assets.ts # Storage-aware inventory, upload and protected playback transport
│   │   │   ├── media-assets.test.ts # S3 presigned URL vs filesystem content routing regression
│   │   │   ├── simulation.ts # Run, Replay and session lifecycle transport
│   │   │   ├── events.ts  # Reviewed-event list, detail and persistence transport
│   │   │   ├── events.test.ts
│   │   │   ├── monitoring-zones.ts # Revisioned multi-zone REST transport
│   │   │   ├── statistics.ts # Area-dashboard statistics transport
│   │   │   └── ppe-requirements.ts # Shared PPE requirement transport
│   │   ├── components/  # Shared application shell
│   │   ├── features/
│   │   │   ├── camera-config/ # Safety Manager asset preview, zone and per-zone rules
│   │   │   ├── auth/    # Login and system-admin account management
│   │   │   ├── area/    # Dedicated area-manager compliance dashboard
│   │   │   ├── media/ # Sys Admin library and authenticated image/video rendering
│   │   │   ├── monitor/ # Four fixed slots, session lifecycle and detection overlays
│   │   │   │   ├── DetectionOverlay.tsx # Source-coordinate boxes over direct media
│   │   │   │   └── AreaManagerPage.test.tsx # Official KPI and false-alarm audit coverage
│   │   │   ├── alerts/  # Rule result, shared violation copy, ReviewModal, and SnapshotOverlay
│   │   │   ├── events/  # Reviewed-event history and immutable decision-audit detail
│   │   │   │   ├── README.md
│   │   │   │   ├── EventDetailDialog.tsx
│   │   │   │   ├── EventDetailDialog.test.tsx
│   │   │   │   ├── event-detail.css
│   │   │   │   ├── EventLogPage.tsx
│   │   │   │   └── EventLogPage.test.tsx
│   │   │   ├── operational-metrics/ # Separate JSONL metrics observability page
│   │   │   ├── rules/   # PPE requirement switches and explicit-save state
│   │   │   ├── vision-worker-compare/ # Dev-only image/video overlays and CPU/CUDA RTT comparison
│   │   │   └── dashboard/ # Reserved dashboard boundary
│   │   ├── styles/      # React CSS entrypoint composing Sentinel styles
│   │   ├── types/       # Typed REST/WebSocket contracts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── index.html       # Vite HTML entrypoint
│   ├── vision-worker-compare.html # Separate noindex developer benchmark entrypoint
│   ├── settings-single-block-prototype.html # Standalone unified camera settings layout prototype
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
│   ├── face_detection_yunet_2023mar.onnx # Pinned OpenCV YuNet face detector
│   ├── ppe_yolov8n.pt  # Retired SH17 artifact retained only for controlled history
│   ├── yolo11n_safety_kd_best.pt # Runtime knowledge-distilled Safety checkpoint
│   ├── yolo11m_safety.pt # Retired Safety checkpoint retained for rollback/benchmark
│   └── yolo11n.pt      # Retired person baseline retained for controlled history
├── docs/                # Problem statement, structure docs and technical guides
│   ├── README.md                    # Documentation catalog
│   ├── PROJECT_STRUCTURE.md         # Current project structure (maintained)
│   ├── FUTURE_PROJECT_STRUCTURE.md  # Future structure, ownership and migration guide (read-only)
│   ├── architecture/                # Architecture diagrams, problem statement and alert contracts
│   │   ├── alert-rule-contract.md       # Approved frame-level PPE and zone alert contract
│   │   ├── architecture_diagram.md      # Current component and runtime data-flow diagrams
│   │   └── project-problem-statement.md # Safety monitoring problem formulation
│   ├── ops/                         # Operations, CI/CD, Vision deployment and metrics
│   │   ├── AI_TEAM_WORKFLOW.md          # Multi-agent collaboration guidelines
│   │   ├── CI_CD.md                     # New-contributor CI, Railway release and rollback runbook
│   │   ├── DEPLOYMENT_FLOW.md           # Visual deployment flow diagrams, service matrix and team runbook
│   │   ├── RAILWAY_SEED_DATA.md         # Why production deploys do not auto-seed and staging2 seed runbook
│   │   ├── local-docker-postgres.md     # Local Docker PostgreSQL configuration
│   │   ├── operational-metrics.md       # JSONL metrics operation, API, privacy and UI guide
│   │   ├── RUNPOD_VISION_DEPLOYMENT.md # CPU/RunPod split-worker deployment runbook
│   ├── data/                        # Dataset preparation and annotation guides
│   │   └── US-13-task2-datapreparation.md # Custom dataset annotation, split and locking guide
│   ├── guide/                       # Setup guides and reference materials
│   └── plans/                       # Implementation-ready plans and their reading guide
│       ├── 2026-08-21-001-feat-remote-vision-service-plan.md # Remote worker implementation plan
│       └── 2026-08-15-001-feat-us16-event-decision-audit-plan.md
├── specs/               # Product requirements and PRD-aligned user story backlog
│   ├── README.md
│   ├── PRD.md
│   ├── USER_STORIES_LIST.md
│   ├── ISSUE-43-DISTRIBUTED-TRACKING-STATE-SPEC.md # Approved PostgreSQL-backed worker-neutral tracking state
│   ├── US-29-DEMO-MULTI-CAMERA-STREAM-SPEC.md # Demo Day multi-camera stream configuration
│   ├── US-01.md ... US-06.md  # Detailed specs for completed user stories
│   ├── done/            # Completed implementation specifications
│   │   ├── README.md
│   │   ├── US-07-SPEC.md
│   │   ├── US-08-SPEC.md
│   │   ├── US-12.md
│   │   ├── US-16.md     # Completed immutable event decision-audit specification
│   │   ├── US-27-MULTI-ZONE-SPEC.md # Completed multi-zone implementation specification
│   │   └── US-28.md     # Completed YOLO11m Safety hat/vest cutover specification
│   └── backlog/         # Remaining MVP and advanced user stories
├── tasks/               # Scoped implementation plans and execution checklists
│   ├── README.md
│   ├── plan.md
│   └── todo.md
│       ├── README.md
│       └── US-09.md ... US-26.md
├── scripts/             # Explicit-entrypoint automation and model benchmarks
│   ├── README.md
│   ├── deploy_all_production.sh # Build, publish, redeploy, wait and health-check the app
│   ├── test_deploy_all_production.sh # No-network regression for the app release
│   ├── sync_code_to_google_drive.sh # Sync only backend/app and vision Python source through rclone
│   ├── test_sync_code_to_google_drive.sh # No-network regression for Google Drive sync arguments
│   ├── benchmark_privacy.py # YuNet/redaction/JPEG latency benchmark
│   ├── benchmark_model.py
│   ├── run_vision_compare_ui.sh # Lifecycle for local CPU/GPU workers plus Vite comparison UI
│   ├── container_entrypoint.sh # Fix volume ownership then drop to appuser
│   ├── bootstrap_legacy_sqlite.py # One-time safe adoption of pre-Alembic local SQLite
│   ├── push_app.sh      # Build and publish the main P-047 app image to Docker Hub
│   ├── production_start.py # Docker preflight, migration and one-worker startup
│   ├── docker_smoke.py # Repeatable black-box local Docker smoke check
│   ├── test_snapshot_bucket.py # S3-compatible snapshot bucket write/read/delete check
│   ├── migrate_media_assets_to_s3.py # One-time verified volume-to-bucket media copy
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
├── context-map.md       # Single repository context map and documentation index
├── PROGRESS.md          # Single project-wide progress tracker
├── ARCHITECTURE.md      # Canonical system architecture and diagrams
├── tests/                # Cross-cutting and automation tests
│   ├── test_bootstrap_legacy_sqlite.py
│   ├── test_startup_validation.py
│   └── test_validate_us13_dataset.py
├── docker-compose.yml
├── .env.development.example # Development environment template for `make setup`
├── .env.production.example  # Production Docker Compose environment template
├── requirements.docker.txt # Production-only, CPU/headless Python dependency set
└── README.md
```

### Giải thích
`backend/` là runtime FastAPI hiện hành. `src/` là scaffold LangGraph cũ còn tồn tại trong filesystem nhưng không còn là đích cho production code mới. Ownership, dependency, cách đặt code và lộ trình migration được chốt trong một file duy nhất: `docs/FUTURE_PROJECT_STRUCTURE.md`.
│   │   │   ├── media_asset_service.py # Atomic upload, validation and protected deletion
