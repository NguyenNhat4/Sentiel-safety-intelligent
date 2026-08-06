# Cấu trúc dự án đích

> Bản chốt ngày 2026-08-06 cho người và AI cùng làm việc. Tài liệu này là chính sách
> định tuyến code đích, không phải yêu cầu scaffold toàn bộ cây. Mọi thay đổi kiến trúc
> tiếp theo phải được ghi vào `DECISIONS.md` trước khi triển khai.

## 1. Nguyên tắc

1. Giữ ba owner production: `backend/`, `frontend/` và `vision/`.
2. Backend tổ chức theo layer đơn giản tương tự scaffold `src/`: API, model, schema và service; không chia `modules/<capability>`.
3. Mỗi task chỉ tạo file có behavior thật và đặt vào đúng layer hiện hữu.
4. Giữ dependency một chiều; API không chứa SQL, model inference hoặc business rule.
5. `vision/` độc lập FastAPI và database, chỉ trả observation qua facade công khai.
6. Không dùng `common`, `utils`, `helpers` làm nơi chứa code chưa xác định trách nhiệm.
7. `src/` là scaffold LangGraph cũ để tham khảo cách phân layer; production mới vẫn nằm trong `backend/`, `frontend/` hoặc `vision/`.
8. Migrate từng phần được task chạm tới; không scaffold cây rỗng hoặc refactor ngoài phạm vi.

## 2. Cây thư mục đích tối thiểu

```text
P-047/
├── backend/                         # FastAPI, nghiệp vụ và persistence
│   ├── README.md
│   ├── app/
│   │   ├── api/
│   │   │   ├── router.py           # Tổng hợp router
│   │   │   └── v1/                 # REST/WS transport theo resource
│   │   ├── core/                    # Config, database, security, logging
│   │   ├── integrations/            # Adapter vision, LLM, storage, notification
│   │   ├── models/                  # SQLAlchemy ORM theo resource
│   │   ├── schemas/                 # Pydantic request/response và internal DTO
│   │   ├── services/                # Use case, rule, transaction và orchestration
│   │   └── main.py                  # Composition root; wiring/lifespan
│   ├── migrations/                  # Alembic history
│   └── tests/                       # Unit, integration và contract tests
├── frontend/                        # React + TypeScript + Vite
│   ├── README.md
│   ├── src/
│   │   ├── api/                     # REST/WS clients và wire types
│   │   ├── components/              # UI dùng lại, không chứa feature state
│   │   ├── features/                # UI và browser state theo feature
│   │   ├── styles/
│   │   ├── types/
│   │   ├── App.tsx
│   │   └── main.tsx
│   └── tests/                       # Chỉ tạo khi test không thuộc một feature
├── vision/                          # CV thuần, độc lập FastAPI và database
│   ├── README.md
│   ├── api.py                       # Facade duy nhất backend gọi
│   ├── pipeline.py                  # Detection/tracking/geometry/privacy khi cần
│   └── tests/
├── models/                          # Weights, nguồn, version và checksum
├── data/                            # Demo data và snapshot runtime đã redact
├── docs/                            # Kiến trúc và hướng dẫn
├── specs/                           # PRD, story và acceptance criteria
├── tests/                           # Chỉ E2E xuyên nhiều owner
├── scripts/                         # Automation có entrypoint rõ ràng
├── AGENTS.md
├── ARCHITECTURE.md
├── DECISIONS.md
├── PROGRESS.md
├── Makefile
└── README.md
```

Không tạo `backend/app/modules`, repository layer riêng hoặc top-level directory mới nếu chưa có nhu cầu thực tế và quyết định kiến trúc.

## 3. Trách nhiệm theo layer

| Layer | Sở hữu | Không sở hữu |
|---|---|---|
| `backend/api` | Parse/validate request, dependency injection, response mapping | SQL, YOLO, business decision |
| `backend/core` | Hạ tầng dùng toàn backend | Use case hoặc provider-specific logic |
| `backend/models` | ORM table, constraint và relationship | HTTP hoặc orchestration |
| `backend/schemas` | Pydantic/wire/internal DTO | SQL và side effect |
| `backend/services` | Use case, deterministic rule, transaction, query orchestration | HTTP rendering hoặc provider SDK details |
| `backend/integrations` | Chuyển đổi provider/protocol | Severity, permission hoặc event lifecycle |
| `frontend/api` | HTTP/WS transport | Render UI hoặc feature state |
| `frontend/features` | UI và browser state | Enforcement phía server |
| `vision` | Detection, association, tracking, geometry, confidence, redaction | HTTP, DB, user hoặc event lifecycle |

Luồng phụ thuộc:

```text
frontend feature → frontend api → backend api → backend service
                                             → model/schema/core
                                             → integration → vision facade/provider
```

- API gọi service; service không import API.
- Service dùng ORM model/schema cùng backend và gọi provider qua integration.
- Integration không quyết định rule an toàn; vision không đọc database hoặc requirement.
- Runtime contract nằm trong FastAPI/Pydantic, frontend wire types, SQLAlchemy/Alembic và tests.
- Thay đổi breaking cần phê duyệt, decision record và compatibility test hoặc migration.

## 4. Quy tắc đặt file

Ví dụ resource PPE:

```text
backend/app/api/v1/ppe_requirements.py
backend/app/models/ppe_requirement.py
backend/app/schemas/ppe_requirement.py
backend/app/services/ppe_requirement_service.py
backend/app/integrations/ppe_vision.py
backend/tests/test_ppe_requirements.py
```

- Một resource nhỏ không cần thêm folder con hoặc repository abstraction.
- Tách file khi responsibility khác nhau, không tách chỉ để đạt hình thức kiến trúc.
- Module README bắt buộc cho owner lớn hoặc folder có boundary/provider riêng; không bắt buộc README cho từng layer kỹ thuật đã được `backend/README.md` mô tả.
- Test backend đặt tại `backend/tests`, frontend cạnh feature, vision tại `vision/tests`, E2E xuyên owner tại root `tests`.

## 5. Lộ trình từ cấu trúc hiện tại

1. Giữ `backend/app/api|core|integrations|models|schemas|services` làm layout production chính.
2. Chuyển code trong `backend/app/modules` về layer tương ứng và xóa `modules` khi không còn consumer.
3. Đưa CV được task chạm tới ra `vision/api.py`; backend gọi thông qua `backend/app/integrations`.
4. Di chuyển hoặc xóa `src/` khi chức năng LangGraph cũ đã được xác nhận trùng/thừa; không thêm production mới vào đó.
5. Chỉ thêm job/infrastructure/top-level owner khi có behavior và consumer thật.

## 6. Checklist trước khi sửa code

1. Task thuộc backend, frontend hay vision?
2. File thuộc API, model, schema, service hay integration?
3. Contract runtime nào bị ảnh hưởng và đã đọc đủ source/test chưa?
4. Dependency có đi đúng chiều không?
5. Có đang tạo abstraction/folder rỗng hoặc refactor ngoài scope không?
6. Nếu filesystem đổi, đã cập nhật `PROJECT_STRUCTURE.md` chưa?
