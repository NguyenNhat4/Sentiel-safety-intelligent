# Cấu trúc dự án đích

> Bản chốt ngày 2026-08-06 cho người và AI cùng làm việc. Đây là hướng tiến hóa từ
> [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md), không phải yêu cầu tạo toàn bộ cây ngay.
> Mọi thay đổi boundary phải có quyết định mới trong [`DECISIONS.md`](../DECISIONS.md).

## 1. Nguyên tắc

1. Giữ một modular monolith: `backend/`, `frontend/` và `vision/` là ba owner production chính.
2. Mỗi task có một primary owner; chỉ tạo folder/file khi có behavior thật.
3. Module giao tiếp qua public API/service/schema, không import nội bộ của nhau.
4. `README.md` tại mỗi module ghi scope, entrypoint, dependency và lệnh test cho cả người lẫn AI.
5. Không dùng `common`, `utils`, `helpers` làm nơi chứa code chưa xác định owner.
6. Di chuyển dần code được task chạm tới; không refactor toàn repo hoặc scaffold cây rỗng.
7. `src/` là scaffold LangGraph cũ, không phải nơi thêm production code mới.

## 2. Cây thư mục đích tối thiểu

```text
P-047/
├── backend/                         # FastAPI, nghiệp vụ và persistence
│   ├── README.md
│   ├── app/
│   │   ├── api/                     # Router HTTP/WS và dependency transport
│   │   ├── core/                    # Config, database, security, logging
│   │   ├── modules/                 # Capability chỉ được tạo khi story cần
│   │   │   ├── monitoring/          # Phiên phân tích, frame/machine/zone input
│   │   │   ├── events/              # Event, review, dedup, snapshot policy
│   │   │   ├── rules/               # Rule và decision policy
│   │   │   ├── auth/                # Identity và RBAC
│   │   │   ├── organization/        # Zone, shift và assignment
│   │   │   ├── analytics/           # Dashboard/statistics query
│   │   │   ├── escalation/          # Routing, retry và acknowledge
│   │   │   └── reporting/           # Schedule, render và delivery history
│   │   ├── integrations/            # Vision, LLM, storage, notification adapters
│   │   └── main.py                  # Composition root; chỉ wiring/lifespan
│   ├── migrations/                  # Alembic history
│   └── tests/                       # Unit, integration và contract tests
├── frontend/                        # React + TypeScript + Vite
│   ├── README.md
│   ├── src/
│   │   ├── api/                     # REST/WS clients và wire types
│   │   ├── components/              # UI dùng lại, không chứa feature state
│   │   ├── features/                # monitor, alerts, events, dashboard; thêm theo story
│   │   ├── styles/
│   │   ├── App.tsx
│   │   └── main.tsx
│   └── tests/                       # Chỉ tạo khi test không thuộc một feature
├── vision/                          # CV thuần, độc lập FastAPI và database
│   ├── README.md
│   ├── api.py                       # Facade duy nhất backend gọi
│   ├── pipeline.py                  # Điều phối detection/tracking/privacy
│   └── tests/
├── models/                          # Weights, nguồn, version và checksum
├── data/                            # Demo data và snapshot runtime đã redact
├── docs/                            # Kiến trúc, contract và hướng dẫn
├── specs/                           # PRD, story và acceptance criteria
├── tests/                           # Chỉ E2E xuyên nhiều owner
├── scripts/                         # Automation có entrypoint rõ ràng
├── AGENTS.md                        # Quy tắc cộng tác người + AI
├── ARCHITECTURE.md
├── DECISIONS.md                     # Decision log duy nhất
├── PROGRESS.md                      # Progress tracker duy nhất
├── Makefile                         # setup/run/check entrypoint
└── README.md
```

Tên capability là boundary đã chốt, nhưng folder chỉ xuất hiện khi story đầu tiên cần nó.
Không tạo thêm top-level directory nếu chưa có quyết định kiến trúc.

## 3. Quyền sở hữu và phụ thuộc

| Vùng | Sở hữu | Không sở hữu |
|---|---|---|
| `backend/api` | Parse request, auth dependency, response mapping | SQL query, YOLO, business decision |
| `backend/core` | Hạ tầng dùng toàn backend | Use case hoặc provider-specific logic |
| `backend/modules` | Use case, domain rule và dữ liệu của capability | Nội bộ capability khác |
| `backend/integrations` | Chuyển đổi protocol/provider | Severity, event state hoặc permission |
| `frontend/api` | HTTP/WS transport và wire types | Render UI hoặc feature state |
| `frontend/features` | UI và browser state của capability | Enforcement phía server |
| `vision` | Detection, tracking, geometry, redaction | HTTP, DB, user, event lifecycle |

Luồng phụ thuộc:

```text
frontend feature → frontend api → backend api → module service/repository
                                             → integration → vision facade/provider
```

- Backend module không import model/repository của module khác; gọi public service hoặc port.
- Frontend feature không import file nội bộ của feature khác; phối hợp tại `App` hoặc public export.
- Vision chỉ trả observation (person, PPE, track, geometry, confidence, ảnh redact).
  `rules` và `events` mới quyết định cảnh báo, lưu hoặc escalation.
- Wire contract hiện hành nằm trong Pydantic/FastAPI và `docs/API_CONTRACT/`;
  data contract nằm trong SQLAlchemy/Alembic và `docs/DATABASE_SCHEMA/`.

## 4. Mẫu module vừa đủ

Một backend capability bắt đầu bằng `README.md`, `router.py`, `schemas.py` và `service.py`.
Chỉ thêm `domain.py`, `repository.py`, `models.py` hoặc `errors.py` khi responsibility xuất hiện.
Test gần owner: backend tại `backend/tests/`, frontend cạnh feature hoặc `frontend/tests/`,
vision tại `vision/tests/`; root `tests/` chỉ dành cho E2E.

README module tối thiểu ghi: purpose/non-goals, maintainer/reviewer, public entrypoint,
dữ liệu sở hữu, dependency được phép, story liên quan và lệnh test tập trung.

## 5. Lộ trình từ cấu trúc hiện tại

1. Giữ runtime hiện tại ổn định; coi `backend/app/api|services|schemas|models` là layout chuyển tiếp.
2. Khi sửa một story, chuyển đúng phần liên quan vào capability owner; giữ API/WS tương thích.
3. Đưa CV ra `vision/api.py` khi thay PPE/blur; backend không gọi implementation sâu.
4. Di chuyển hoặc xóa `src/` khi chức năng LangGraph cũ đã được xác nhận là trùng/thừa;
   không thêm dependency production mới vào đó.
5. Chỉ tách contract artifact, jobs hoặc hạ tầng thành nhánh riêng khi có hai consumer thật.

## 6. Checklist trước khi sửa code

1. Story và primary owner là gì?
2. README, contract và source mẫu nào cần đọc?
3. Public boundary nào bị ảnh hưởng?
4. Test gần owner nào chứng minh thay đổi?
5. Có đang tạo placeholder, import nội bộ, hoặc refactor ngoài scope không?
6. Nếu filesystem đổi, đã cập nhật `PROJECT_STRUCTURE.md` chưa?

Nếu không xác định được một owner hoặc cần top-level/module mới, dừng và xin quyết định.
