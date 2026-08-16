# Sơ đồ hệ thống P-047

Các sơ đồ này mô tả runtime hiện hành và boundary đã chốt. Contract thực thi vẫn nằm ở FastAPI,
Pydantic, frontend wire types, SQLAlchemy/Alembic và tests.

## Sơ đồ components

```mermaid
flowchart LR
    Browser[React browser]
    Client[REST and WebSocket client]
    API[FastAPI API transport]
    Service[Backend services]
    Integration[Integration adapters]
    Models[Models schemas and core]
    Vision[Vision facade]
    Database[(PostgreSQL)]
    Storage[(Protected snapshot storage)]
    Notify[Notification provider]

    Browser --> Client
    Client -->|REST or binary JPEG WebSocket| API
    API --> Service
    Service --> Integration
    Service --> Models
    Integration --> Vision
    Models --> Database
    Integration --> Storage
    Integration --> Notify
```

## Sơ đồ data flow runtime

```mermaid
flowchart TD
    A[Browser video and saved zone configuration] --> B[WebSocket inference endpoint]
    B --> C[Frame inference service]
    C --> D[Vision facade: one YOLO11m Safety track call]
    D --> E[Observations: person, hat, vest, track ID, foot point]
    E --> F[Safety rule and four-frame occurrence debounce]
    F -->|Normal or continuing occurrence| G[Correlated result and browser overlays]
    F -->|New violation occurrence| H[Pause video and open grouped HITL review]
    H -->|False alarm| I[Persist feedback audit only]
    H -->|Acknowledged| J[Redact snapshot before annotation]
    J -->|Redaction failure| K[Return error and keep review pending]
    J --> L[Write redacted snapshot]
    L -->|Storage failure| K
    L --> M[Persist event, audit, and object metadata]
    M -->|Database failure| K
    M --> N[Return acknowledged event IDs]
```

Runtime realtime dùng `/api/v1/ws/inference`: browser chỉ gửi tối đa hai frame mẫu mỗi giây và
chỉ có một frame đang chờ. `POST /api/v1/analysis/frame` là REST fallback, không có state debounce
giữa các request. Snapshot chỉ được ghi sau acknowledgment; nếu redaction, storage hoặc database
thất bại thì backend không tạo event và UI giữ review để operator thử lại.
