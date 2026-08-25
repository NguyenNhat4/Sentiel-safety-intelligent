# Sơ Đồ Kiến Trúc & Luồng Hệ Thống (System Diagrams & Sequence Flows)

Tài liệu này tổng hợp các sơ đồ thành phần (Component Diagrams), sơ đồ topo (Topology) và sơ đồ luồng trình tự (Sequence Diagrams) chi tiết của hệ thống **P-047 Safety Monitoring**.

---

## 1. Sơ Đồ Thành Phần Hệ Thống (Component Architecture)

```mermaid
flowchart LR
    Browser[React 19 Frontend UI] -->|REST API & WebSocket| Backend[FastAPI Modular Monolith]
    Admin[System Admin] -->|Tải lên Ảnh/Video| Backend
    Backend --> Postgres[(PostgreSQL Database)]
    MediaVol[(Media Volume / Bucket)] --> Backend
    Backend -->|Khung hình & Yêu cầu| Vision[Local / Remote Safety Vision Facade]
    Vision -->|Phát hiện Person, Hat, Vest & ByteTrack ID| Backend
    Backend -->|Snapshot sự kiện đã làm mờ| Storage[(Snapshot Storage)]
```

---

## 2. Sơ Đồ Chu Kỳ Cấu HÌnh & Phiên Camera (Camera Configuration & Session Lifecycle)

```mermaid
flowchart TD
    Slot[Slot Camera cố định cam_1 đến cam_4] --> Config[Cấu hình nguyên tử Asset, Zone & Quy tắc PPE]
    Config --> Save[Lưu cấu hình - Không chạy inference]
    Save --> Run[Chạy mô phỏng tất cả camera hoặc Replay từng camera]
    Run --> Session[Tạo phiên mới do Backend sở hữu]
    Session --> Source[Mở tệp media trực tiếp từ volume/cache]
    Source --> Infer[FrameInferenceService suy luận frame]
    Infer --> Rules[SafetyRuleEngine kiểm tra quy tắc an toàn]
    Rules --> WS[WebSocket: Trạng thái phiên, Detections, Rolling FPS]
    Rules --> HITL[Danh sách chờ xác minh Human-in-the-Loop]
    HITL --> Events[(Lưu sự kiện đã được duyệt)]
    Source --> EOF[Kết thúc tệp Video EOF]
    EOF --> Replay[Mở lại nút Replay cho camera đó]
```

---

## 3. Các Sơ Đồ Trình Tự Chi Tiết (Detailed Sequence Diagrams)

### 3.1. Luồng Tải Lên & Quản Lý Media Asset (Upload Media Flow)

```mermaid
sequenceDiagram
    autonumber
    actor Admin as System Admin
    participant UI as React Frontend
    participant API as Backend FastAPI
    participant Bucket as Railway Bucket (S3)
    participant DB as PostgreSQL DB
    participant Cache as Media Asset Cache Volume

    Admin->>UI: Tải lên video/ảnh mới (Thư viện media)
    UI->>API: POST /api/v1/media-assets/presigned-url (metadata, filename, bytes)
    API->>DB: Khởi tạo bản ghi MediaAsset (status=PENDING)
    API->>UI: Trả về Presigned Upload URL & asset_id
    UI->>Bucket: Upload trực tiếp file media (PUT/POST binary)
    Bucket-->>UI: Upload thành công
    UI->>API: POST /api/v1/media-assets/{asset_id}/complete
    API->>Bucket: Kiểm tra file & Validate frame đầu tiên (OpenCV decode)
    API->>Cache: Tải tệp về Media Volume cache (/app/data/media-assets)
    API->>DB: Cập nhật trạng thái MediaAsset (status=READY)
    API-->>UI: Xác nhận thành công, Asset đã sẵn sàng
```

### 3.2. Luồng Cấu Hình Camera & Vùng An Toàn (Camera & Zone Configuration Flow)

```mermaid
sequenceDiagram
    autonumber
    actor Officer as Safety Manager
    participant UI as React Frontend
    participant API as Backend FastAPI
    participant DB as PostgreSQL DB

    Officer->>UI: Chọn ô Camera Slot (ví dụ: cam_1)
    UI->>API: GET /api/v1/camera-configurations/cam_1
    API-->>UI: Trả về Cấu hình hiện tại (Asset_id, Zones, Rules)
    Officer->>UI: Chọn Media Asset READY từ danh sách & xem trước
    Officer->>UI: Vẽ Polygon Vùng nguy hiểm (Zone) & Bật Machine State (RUNNING/STOPPED)
    Officer->>UI: Cấu hình quy tắc PPE (Thiếu Mũ, Thiếu Áo, Zone Intrusion)
    Officer->>UI: Nhấn "Lưu cấu hình"
    UI->>API: PUT /api/v1/camera-configurations/cam_1 (Payload nguyên tử)
    API->>API: Kiểm tra hợp lệ (Polygon không chồng lấn, Asset READY)
    API->>DB: Lưu Atomic Transaction (CameraConfig, MonitoringZone, PPERequirement)
    API-->>UI: Lưu thành công
```

### 3.3. Luồng Chạy Phiên Mô Phỏng & Suy Luận Trực Tiếp (Direct Frame Inference & WebSocket Flow)

```mermaid
sequenceDiagram
    autonumber
    actor Officer as Safety Manager
    participant UI as React Frontend
    participant API as Backend FastAPI / FrameInferenceService
    participant Vision as Vision Facade (YOLO11m Safety)
    participant Rule as SafetyRuleEngine

    Officer->>UI: Nhấn "Chạy mô phỏng"
    UI->>API: POST /api/v1/camera-sessions/run (Chạy tất cả camera đã cấu hình)
    API->>API: Khởi tạo CameraSession mới cho từng cam (UUID session)
    API-->>UI: Trả về danh sách Sessions bắt đầu (status=RUNNING)
    UI->>API: Kết nối WebSocket /api/v1/ws/camera-detections

    loop Suy luận theo thời gian thực (Sample Frame FPS)
        API->>API: Đọc frame tiếp theo từ file tệp media local cache
        API->>Vision: Yêu cầu suy luận frame (Bypass Base64, giữ nguyên resolution)
        Vision-->>API: Trả về bounding boxes (Person, Hat, Vest) & ByteTrack IDs
        API->>Rule: Đánh giá vi phạm (Person vs Polygon Zone vs Machine State vs PPE)
        Rule-->>API: Trả về kết quả (NORMAL / VIOLATE, Zone ID, Track ID)
        API-->>UI: Gửi qua WebSocket (Detections overlay, Bounding Boxes, Session Status, Rolling FPS)
    end

    API->>UI: Đã tới cuối video (EOF) -> Cập nhật Session Status=COMPLETED (Bật nút Replay)
```

### 3.4. Luồng Cảnh Báo Vi Phạm, HITL Review & Lưu Sự Kiện (HITL Review & Event Persistence Flow)

```mermaid
sequenceDiagram
    autonumber
    participant Rule as SafetyRuleEngine
    participant API as Backend FastAPI / Event Service
    participant Privacy as Privacy Vision Pipeline (YuNet)
    participant UI as React Frontend (Live Monitor / Safety Manager)
    participant DB as PostgreSQL DB

    Rule->>API: Phát hiện vi phạm an toàn (Frame Result = VIOLATE)
    API->>API: Kiểm tra Dedup Occurrence (Session + Track ID + Zone ID + Rule Key)
    alt Đã có vi phạm trùng cho Track ID này trong Session
        API->>API: Bỏ qua tạo Alert mới (Tránh lặp)
    else Chưa có vi phạm (Occurrence mới)
        API->>Privacy: Yêu cầu che danh tính khuôn mặt trên frame vi phạm
        Privacy->>Privacy: Chạy YuNet face detection -> Làm mờ khuôn mặt (Fallback: Person crop blur)
        Privacy-->>API: Snapshot đã che danh tính (Privacy Blurred = true)
        API->>UI: Đẩy Cảnh báo vi phạm (HITL Review Queue) tới Safety Manager
        UI->>UI: Hiển thị Modal Review Popup cùng hình ảnh Snapshot đã che danh tính
        Officer->>UI: Chọn "Xác Nhận Vi Phạm" (hoặc "Đánh dấu Báo Cờ False Alarm")
        UI->>API: POST /api/v1/events (Event Payload + Confirmation Result)
        API->>DB: Lưu bản ghi Sự kiện (SafetyEvent & DecisionContextAudit_v1)
        API-->>UI: Xác nhận lưu Event thành công, chuyển cảnh báo tiếp theo trong Queue
    end
```

---

## 4. Các Bất Biến Về Mặt Kiến Trúc (Architectural Invariants)

1. **Kiểm duyệt danh tính (Privacy Gate):** Không bao giờ lưu snapshot thô chưa được che danh tính. Nếu pipeline che danh tính báo lỗi, snapshot bị hủy bỏ và không được ghi vào DB/Storage.
2. **Không truyền URL/Path tùy ý từ Client:** Browser chỉ giao tiếp qua `camera_id`, `asset_id` và `session_id`. Backend toàn quyền kiểm soát tệp media và đường dẫn hệ thống tệp.
3. **Độc lập Quy tắc An toàn:** Bộ suy luận Vision chỉ trả về thông số phát hiện (observations: person, hat, vest, track_id). Quyết định vi phạm an toàn do `SafetyRuleEngine` ở Backend chịu trách nhiệm hoàn toàn.
