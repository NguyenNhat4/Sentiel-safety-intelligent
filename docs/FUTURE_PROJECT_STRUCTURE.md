# Cấu Trúc Dự Án Tương Lai — Bản Chốt

> **Trạng thái:** baseline kiến trúc đã chốt ngày 2026-08-06. Đây là cấu trúc đích, không phải mô tả filesystem hiện tại. Cấu trúc đang tồn tại được duy trì tại [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md).
>
> Sau khi chốt, thay đổi ranh giới module hoặc thêm thư mục cấp cao chỉ được thực hiện khi có quyết định mới trong root [`DECISIONS.md`](../DECISIONS.md), đồng thời cập nhật tài liệu này và `PROJECT_STRUCTURE.md` khi filesystem thực tế thay đổi.

## 1. Mục tiêu thiết kế

Cấu trúc này là guardrail cho cả người và AI:

1. Mỗi business capability có đúng một nơi sở hữu code, dữ liệu và use case.
2. File transport, nghiệp vụ, persistence và UI không làm thay trách nhiệm của nhau.
3. Người review biết owner và test cần gọi mà không phải đọc toàn repo.
4. Module có thể được thay thế bên trong mà không làm vỡ module khác nếu public contract không đổi.
5. Vẫn giữ **modular monolith** trong MVP và giai đoạn nâng cao 5 tuần; không tách microservice sớm.

## 2. Cấu trúc đích

```text
P-047/
├── .github/
│   └── CODEOWNERS                    # Bắt buộc reviewer theo vùng sở hữu
│
├── backend/
│   ├── README.md
│   ├── app/
│   │   ├── README.md
│   │   ├── api/                      # HTTP/WS composition; không chứa nghiệp vụ
│   │   │   ├── README.md
│   │   │   ├── dependencies.py       # Auth/session/request dependencies
│   │   │   └── router.py             # Gắn router của các module và version prefix
│   │   ├── core/                     # Hạ tầng dùng toàn backend, không chứa use case
│   │   │   ├── README.md
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── errors.py
│   │   │   ├── logging.py
│   │   │   └── security.py
│   │   ├── modules/                  # Business capabilities của modular monolith
│   │   │   ├── README.md
│   │   │   ├── auth/                 # Login, token/session, RBAC, actor audit
│   │   │   ├── monitoring/           # Phiên video/ảnh, frame flow, machine/zone input
│   │   │   ├── rules/                # Rule version, validate, preview, decision policy
│   │   │   ├── events/               # Event lifecycle, review, dedup, audit, snapshot policy
│   │   │   ├── organization/         # Khu vực, ca, assignment, timezone
│   │   │   ├── analytics/            # Query/dashboard metric nghiệp vụ
│   │   │   ├── escalation/           # Severity routing, delivery, retry, acknowledge
│   │   │   └── reporting/            # Lịch, report snapshot, render và lịch sử gửi
│   │   ├── integrations/             # Adapter tới hệ thống/engine bên ngoài domain
│   │   │   ├── README.md
│   │   │   ├── vision/               # Gọi public facade của vision và map contract
│   │   │   ├── llm/                  # Structured output + deterministic fallback
│   │   │   ├── notifications/        # Email/chat provider adapter
│   │   │   └── storage/              # Snapshot/object storage adapter
│   │   ├── jobs/                     # Entry point cho report/escalation background jobs
│   │   │   └── README.md
│   │   └── main.py                   # Composition root FastAPI; chỉ wiring/lifespan
│   ├── migrations/                   # Alembic; migration đã apply không được sửa lại
│   │   └── README.md
│   └── tests/
│       ├── README.md
│       ├── unit/                      # Mirror module sở hữu behavior
│       ├── integration/               # API + DB + adapter boundary
│       └── contract/                  # OpenAPI/WS/vision contract compatibility
│
├── vision/
│   ├── README.md
│   ├── api.py                         # Public facade duy nhất backend được gọi
│   ├── types.py                       # Observation types nội bộ, map sang contracts/
│   ├── pipeline.py                    # Chỉ điều phối các bước CV
│   ├── person/                        # Person detection adapter
│   │   └── README.md
│   ├── ppe/                           # Helmet/glasses/gloves detection + class mapping
│   │   └── README.md
│   ├── tracking/                      # Track lifecycle/ByteTrack adapter
│   │   └── README.md
│   ├── association/                   # Gắn PPE observation vào person/track
│   │   └── README.md
│   ├── zones/                         # Geometry, foot point, polygon observation
│   │   └── README.md
│   ├── privacy/                       # Blur/redact in-memory; không persistence
│   │   └── README.md
│   └── tests/                         # Unit + pipeline integration bằng fixture
│       └── README.md
│
├── frontend/
│   ├── README.md
│   ├── src/
│   │   ├── app/                       # Router, providers, shell và composition
│   │   │   └── README.md
│   │   ├── api/                       # HTTP/WS client và generated contract types
│   │   │   ├── README.md
│   │   │   └── generated/             # Sinh từ OpenAPI/schema; không sửa tay
│   │   ├── features/
│   │   │   ├── README.md
│   │   │   ├── auth/
│   │   │   ├── monitor/
│   │   │   ├── rules/
│   │   │   ├── alerts/
│   │   │   ├── events/
│   │   │   ├── organization/
│   │   │   ├── dashboard/
│   │   │   ├── escalations/
│   │   │   └── reports/
│   │   ├── shared/                    # UI primitive/hook thuần, không business state
│   │   │   ├── README.md
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   └── lib/
│   │   ├── styles/
│   │   └── main.tsx
│   ├── tests/                         # Integration/component shared setup
│   │   └── README.md
│   ├── package.json
│   └── vite.config.ts
│
├── contracts/
│   ├── README.md                      # Nguồn, version và cách generate/validate
│   ├── schemas/
│   │   ├── vision-observation.schema.json
│   │   ├── inference-message.schema.json
│   │   ├── safety-rule.schema.json
│   │   └── safety-event.schema.json
│   ├── generated/
│   │   └── openapi.json               # Artifact sinh từ FastAPI
│   └── fixtures/                      # Ví dụ tương thích cho contract tests
│
├── models/
│   ├── README.md                      # License, nguồn, version, input/output
│   ├── registry.yaml                  # Logical name → artifact/checksum/class map
│   ├── checksums.sha256
│   ├── model-cards/
│   └── weights/                       # Artifact model; không chứa Python logic
│
├── data/
│   ├── README.md                      # Data policy và nguồn dữ liệu
│   ├── demo/                          # Dữ liệu mô phỏng được phép dùng
│   ├── edge-cases/
│   ├── ground-truth/                  # Nhãn version hóa cho đánh giá
│   └── snapshots/                     # Runtime, chỉ ảnh đã blur; mặc định gitignored
│
├── evaluation/
│   ├── README.md
│   ├── evaluate_detection.py          # Precision/recall theo ground truth
│   ├── evaluate_events.py             # Dedup/false-alarm metrics
│   ├── evaluate_latency.py            # End-to-end p50/p95
│   └── reports/                       # Kết quả tái lập theo release
│
├── tests/
│   ├── README.md
│   └── e2e/                           # Luồng xuyên frontend-backend-vision
│
├── infra/
│   ├── README.md
│   ├── docker/                        # Dockerfiles và container entrypoints
│   ├── cloud/                         # IaC/config cloud sau khi target được chốt
│   └── observability/                 # Dashboard/alert/logging config
│
├── docs/
│   ├── README.md                      # Master documentation index
│   ├── PROJECT_STRUCTURE.md           # Filesystem hiện tại
│   ├── FUTURE_PROJECT_STRUCTURE.md    # Baseline đích này
│   ├── project-problem-statement.md
│   ├── architecture_diagram.md
│   ├── guide/
│   ├── runbooks/                      # Deploy, rollback, backup, incident response
│   └── reports/                       # Traceability/UAT/security/benchmark summaries
│
├── specs/
│   ├── README.md
│   ├── PRD.md
│   ├── USER_STORIES_LIST.md
│   ├── US-01.md ... US-06.md
│   └── backlog/
│       ├── README.md
│       └── US-07.md ... US-26.md
│
├── ARCHITECTURE.md                    # Kiến trúc hệ thống ở mức tổng quan
├── DECISIONS.md                       # Decision log duy nhất toàn repo
├── PROGRESS.md                        # Progress tracker duy nhất toàn repo
├── AGENTS.md                          # Workflow/guardrail cho AI và contributor
├── Makefile                           # Entry point chuẩn cho setup/check/run
├── pyproject.toml
├── docker-compose.yml
└── README.md
```

Các thư mục feature/module trong cây trên đều phải có `README.md` khi được tạo thực tế, dù cây rút gọn không lặp lại dòng này cho từng feature.

## 3. Ranh giới sở hữu backend

Mỗi thư mục `backend/app/modules/<capability>/` dùng cùng một template. Chỉ tạo file khi có behavior thật, không tạo placeholder rỗng:

```text
<capability>/
├── README.md       # Purpose, owner, public API, data, dependencies, related stories
├── router.py       # HTTP/WS parsing, status code, dependency injection
├── schemas.py      # Request/response DTO; không chứa ORM model
├── service.py      # Use case/application orchestration
├── domain.py       # Entity/value/policy/state transition thuần
├── repository.py  # Query/persistence của chính module
├── models.py       # SQLAlchemy model do module sở hữu
└── errors.py       # Lỗi có nghĩa nghiệp vụ của module
```

Không bắt buộc một module nhỏ phải có đủ tất cả file. Khi một file bắt đầu chứa hai nhóm use case độc lập, tách thành package theo use case thay vì thêm hậu tố kiểu `helpers2.py` hoặc `utils_new.py`.

| Module | Sở hữu | Không sở hữu | Story chính |
|---|---|---|---|
| `auth` | Danh tính, credential, token/session, role/permission | UI login, zone assignment, notification routing | US-20 |
| `monitoring` | Monitoring session, image/video input, machine state, frame orchestration | Thuật toán YOLO, event state machine | US-01–04, US-24 |
| `rules` | Rule schema/version, preview/confirm, deterministic evaluation, confidence triage | Detection, event persistence, LLM provider code | US-11, US-15 |
| `events` | Event/dedup/review state machine, immutable audit context, snapshot persistence policy | Pixel processing, dashboard aggregation | US-05, US-06, US-08, US-09, US-12, US-16 |
| `organization` | Zone, shift, assignment, timezone, soft delete | Polygon math, RBAC engine | US-21 |
| `analytics` | Dashboard/statistics query và metric definitions | Offline model benchmark, periodic delivery | US-10, US-22 |
| `escalation` | Severity routing, delivery state, retry/idempotency, acknowledge | Provider SDK, event decision | US-14 |
| `reporting` | Schedule, aggregation snapshot, render, delivery history | Dashboard UI, notification provider SDK | US-23 |

Các yêu cầu vận hành US-17–US-19 và US-25–US-26 là cross-cutting; code vẫn phải nằm trong module/adapter sở hữu cụ thể, còn evidence nằm tại `docs/reports/` và cấu hình vận hành tại `infra/`.

## 4. Dependency direction bắt buộc

```text
Frontend feature
    ↓ REST / WebSocket contract
Backend API/router
    ↓
Backend module service → module domain/repository
    ↓ port/interface
Backend integration adapter
    ↓
Vision facade / LLM / notification / storage
```

Quy tắc:

1. `vision/` không import `backend/`, không biết FastAPI, database, user, severity hay event lifecycle.
2. `vision/` chỉ trả **observation**: người, PPE, track, geometry, confidence và ảnh đã redact khi được yêu cầu. Quyết định “có tạo/escalate event không” thuộc `rules` + `events`.
3. Module backend không import `models.py` hoặc `repository.py` của module khác. Tương tác qua public service/port và contract đã công bố trong README của module.
4. `router.py` không query database và không gọi YOLO trực tiếp; `repository.py` không quyết định nghiệp vụ; `models.py` không serialize HTTP response.
5. `integrations/` chỉ chuyển đổi protocol/provider. Fallback LLM phải gọi cùng contract với provider thật và không được quyết định severity.
6. Frontend feature không import nội bộ của feature khác. Dữ liệu chéo đi qua app composition hoặc public export đã ghi trong feature README.
7. `shared/`, `core/`, `utils` không được dùng làm nơi chứa code chưa xác định owner. Chỉ đưa abstraction vào vùng dùng chung sau khi có ít nhất hai consumer thật và tên thể hiện đúng trách nhiệm.

## 5. Contract và nguồn sự thật

| Boundary | Nguồn sự thật | Derived artifact |
|---|---|---|
| REST API | Pydantic schema + FastAPI route trong module sở hữu | `contracts/generated/openapi.json`, frontend generated types |
| WebSocket | JSON Schema trong `contracts/schemas/inference-message.schema.json` | Python/TypeScript validator hoặc type sinh tự động |
| Backend ↔ Vision | `vision-observation.schema.json` và fixture version hóa | Adapter types ở hai phía |
| Safety rule | `safety-rule.schema.json` + rule domain validation | LLM structured-output schema, UI form types |
| Safety event | Event domain/state machine | API schema và audit/event fixture |

- Generated artifact không được sửa tay.
- Thay đổi breaking phải tăng contract version, có compatibility test và migration path.
- Không duy trì hai type viết tay cho cùng một wire contract.
- Correlation ID và timestamp phải đi xuyên frontend → backend → vision → event để đo latency và audit.

## 6. Ownership và luồng cộng tác

`CODEOWNERS` là cơ chế review tự động; README của module là tài liệu ownership cho người và AI. README module tối thiểu phải ghi:

- `Purpose` và phạm vi không sở hữu.
- Maintainer/team và reviewer bắt buộc.
- Public entrypoints/contracts.
- Dữ liệu/table/artifact module sở hữu.
- Dependency được phép.
- Lệnh test tập trung.
- User stories và tài liệu liên quan.

Khi một thay đổi chạm nhiều module:

1. Chọn một **primary owning module** theo use case.
2. Thay đổi module khác qua contract/public entrypoint; không sửa trực tiếp nội bộ để “đi đường tắt”.
3. Nếu cần đổi contract, owner hai phía review; cập nhật fixture/contract test trước hoặc cùng patch.
4. Nếu không xác định được owner duy nhất, dừng triển khai và ghi quyết định boundary vào root `DECISIONS.md`.

## 7. Guardrail cho AI và reviewer

Trước khi tạo hoặc sửa code:

1. Đọc `PROGRESS.md`, `DECISIONS.md`, story liên quan và README của module owner.
2. Ghi rõ mapping: story → owning module → public contract → test layer.
3. Không tạo top-level directory mới, module mới hoặc “common/shared/utils” mới nếu chưa có quyết định kiến trúc.
4. File mới phải có một lý do thay đổi duy nhất. Tên file phải mô tả responsibility, không dùng `misc.py`, `helpers.py`, `common.ts` chung chung.
5. Một file production vượt 300 dòng phải được tách theo responsibility hoặc có lý do ngoại lệ trong `DECISIONS.md`. Không áp dụng cho generated code, migration và fixture.
6. Folder/module mới phải có README và phải cập nhật `PROJECT_STRUCTURE.md` trong cùng thay đổi.
7. Không tạo thêm `DECISIONS.md` hoặc `PROGRESS.md` ở module.

Các rule nên được tự động hóa dần trong `make check`:

- Python import-boundary check: cấm `vision → backend` và cấm module truy cập repository/model của module khác.
- ESLint boundary check: cấm feature frontend import nội bộ feature khác.
- Contract drift check: OpenAPI/schema/generated types phải đồng bộ.
- Privacy test: không persistence raw snapshot; `privacy_blurred=true` chỉ khi redact thành công.
- CODEOWNERS check: file/module mới phải map được tới owner/reviewer.

## 8. Data, model và privacy

1. `models/` chỉ chứa artifact, model card, license, class mapping và checksum; logic load/inference thuộc `vision/`.
2. `data/demo`, `edge-cases`, `ground-truth` chỉ dùng dữ liệu mô phỏng hoặc dữ liệu được phép rõ ràng.
3. Raw video không được lưu liên tục. `data/snapshots/` là runtime storage và chỉ nhận ảnh đã blur/redact thành công.
4. Snapshot gốc phải được xử lý in-memory và hủy; lỗi privacy làm fail việc lưu ảnh/event theo policy US-12.
5. Dataset/model/report cần version, nguồn, threshold và hardware context để US-13 có thể tái lập.

## 9. Phạm vi kiến trúc đã chốt

Cấu trúc hỗ trợ toàn bộ US-01–US-26 nhưng không ngầm mở rộng sản phẩm. Trong phạm vi hiện tại:

- Một modular monolith deployable; background jobs có thể là process riêng nhưng dùng chung codebase/database contract.
- Video/ảnh mô phỏng, một luồng demo tại một thời điểm cho MVP.
- PostgreSQL production, SQLite local/test khi SQLAlchemy behavior tương thích.
- Camera nhà máy thật, PLC, tự động dừng máy và scale nhiều stream vẫn ngoài phạm vi; cần discovery và quyết định kiến trúc mới.

## 10. Trình tự chuyển đổi an toàn

Không big-bang refactor. Mỗi story đang triển khai sẽ di chuyển phần code mà story đó chạm tới:

1. Thiết lập contract tests và public facade `vision/api.py`.
2. Tách business rule/event lifecycle khỏi frame inference service.
3. Chuyển backend sang capability modules theo story ưu tiên MVP.
4. Sinh frontend types từ contract rồi mới mở rộng feature auth/rules/dashboard.
5. Bổ sung organization, escalation, reporting và jobs theo kế hoạch nâng cao.
6. Thêm boundary checks vào `make check`; xóa đường import cũ chỉ sau khi regression đạt.

Mỗi bước phải giữ API/WS behavior hiện hành hoặc có versioned migration được ghi rõ.
