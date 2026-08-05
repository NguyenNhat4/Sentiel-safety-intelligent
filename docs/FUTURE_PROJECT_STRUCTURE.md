# Cấu Trúc Dự Án Tương Lai (Future Project Structure)

> **Tài liệu bất biến:** File này ghi lại định hướng cấu trúc tương lai đã được phê duyệt và không được phép chỉnh sửa. Cấu trúc hiện tại được duy trì tại [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md).

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
│   │   ├── styles/              # React CSS entrypoint
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

## Giải thích

Cấu trúc tương lai đảm bảo sự phân tách trách nhiệm rõ ràng (separation of concerns):

1. **`vision/`**: Luồng Computer Vision chạy độc lập để nhận diện người, trang bị PPE, kiểm tra vùng polygon nguy hiểm và làm mờ khuôn mặt.
2. **`backend/`**: Gateway tích hợp REST API, WebSocket realtime, cơ sở dữ liệu PostgreSQL và AI Safety Agent (LLM) hỗ trợ phân tích/đề xuất xử lý sự cố.
3. **`frontend/`**: React + TypeScript SPA theo feature boundaries. Transport không render UI, Canvas utilities không gọi network, và monitor giữ socket/frame state trong refs để không tạo queue hoặc stale closure. Vite phục vụ development; FastAPI phục vụ `frontend/dist` trong production.
4. **`contracts/`**: Chuẩn hóa schema giao tiếp giữa Vision worker và Backend API.
5. **Central tracking**: Root `DECISIONS.md` và `PROGRESS.md` là hai nguồn tracking duy nhất; module không tạo bản riêng.

## Frontend boundaries

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
