# Sơ đồ hệ thống P-047

Các sơ đồ này mô tả runtime hiện hành và boundary đã chốt. Contract thực thi vẫn nằm ở FastAPI,
Pydantic, frontend wire types, SQLAlchemy/Alembic và tests.

## Sơ đồ components

```mermaid
flowchart LR
    Browser[React browser]
    MediaMTX[MediaMTX RTSP Server]
    Streamer[Streamer Service]
    API[FastAPI API transport]
    Service[Backend services]
    Worker[Camera Inference Worker]
    Integration[Integration adapters]
    Models[Models schemas and core]
    Vision[Vision facade]
    Database[(PostgreSQL)]
    Storage[(Protected snapshot storage)]
    Notify[Notification provider]

    Streamer -->|RTSP stream| MediaMTX
    Worker -->|Read RTSP| MediaMTX
    Worker --> Integration
    Browser -->|Authenticated HLS| Streamer
    Browser -->|REST and Camera Detections WS| API
    API --> Service
    Service --> Worker
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
    A[RTSP Stream from MediaMTX] --> B[Camera Inference Worker]
    B --> C[Frame inference service]
    C --> D[Vision facade: one YOLO11m Safety track call]
    D --> E[Observations: person, hat, vest, track ID, foot point]
    E --> F[Safety rule evaluation and occurrence debounce]
    F -->|Detection metadata| G[Publish to /api/v1/ws/camera-detections]
    G --> H[Render source-coordinate overlays in browser]
    F -->|New violation occurrence| I[Open grouped HITL review in UI]
    I -->|False alarm| J[Persist feedback audit only]
    I -->|Acknowledged| K[Redact snapshot with YuNet + person fallback]
    K -->|Redaction failure| L[Return error and keep review pending]
    K --> M[Write redacted snapshot]
    M -->|Storage failure| L
    M --> N[Persist event, decision audit context, and track metadata]
    N -->|Database failure| L
    N --> O[Return acknowledged event IDs]
```

Runtime realtime hỗ trợ 2 luồng:
1. **Luồng RTSP chính**: Backend đọc RTSP từ MediaMTX qua `CameraInferenceWorker` (2 FPS), phân tích và push metadata qua `/api/v1/ws/camera-detections` cho frontend hiển thị overlay trên luồng HLS.
2. **Luồng Direct Frame Fallback**: Sử dụng `/api/v1/ws/inference` hoặc REST `POST /api/v1/analysis/frame` (mô phỏng client gửi frame trực tiếp).

Snapshot chỉ được ghi sau khi operator xác nhận (`acknowledged`); nếu redaction, storage hoặc database thất bại thì backend không tạo event và UI giữ review để operator thử lại.

