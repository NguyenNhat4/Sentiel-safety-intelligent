# Kiến trúc hệ thống P-047

Tài liệu này là nguồn kiến trúc duy nhất của dự án. Nó mô tả hướng đích; runtime hiện tại
được ghi rõ để không nhầm phần đã chạy với phần còn phải triển khai.

## Mục tiêu và ràng buộc

- Phân tích video/ảnh mô phỏng để phát hiện người, thiếu mũ bảo hộ/áo phản quang và xâm nhập vùng nguy hiểm.
- Một stream có thể chứa nhiều vùng bốn điểm; xâm nhập vùng enabled luôn là critical, không phụ thuộc trạng thái máy mô phỏng. Kết quả mơ hồ phải chuyển Human-in-the-Loop (HITL).
- Cảnh báo gần realtime, không tạo event lặp cho một vi phạm liên tục.
- Không lưu video thô; chỉ lưu snapshot sự kiện sau khi che danh tính thành công.
- Ba vai trò được backend phân quyền: `system_admin`, `safety_officer` và `area_manager`.
- MVP là một stream mô phỏng; camera thật, PLC, tự dừng máy và multi-stream nằm ngoài phạm vi.

## Kiến trúc đích

Giữ **modular monolith** để giao nhanh và triển khai đơn giản. `frontend/`, `backend/` và
`vision/` là ba owner production; chỉ tách service khi có nhu cầu scale hoặc vận hành đã đo được.
Sơ đồ component và data flow runtime nằm trong `docs/architecture_diagram.md`.

## Boundary và dependency

| Owner | Trách nhiệm | Không được làm |
|---|---|---|
| Frontend | Capture frame, UI state, overlay, review và dashboard | Tự quyết severity hoặc authorization |
| Backend API | Parse/authenticate/map REST và WebSocket | Chứa SQL, CV hoặc rule nghiệp vụ |
| Backend services | Use case, rule, transaction, dedup, RBAC, analytics và reporting | HTTP rendering hoặc provider SDK details |
| Integrations | Adapter vision, storage, LLM và notification | Quyết định event state hoặc permission |
| Vision | Detection, association, tracking, geometry, confidence, redaction | Biết HTTP, database, user hoặc event lifecycle |

Luồng phụ thuộc bắt buộc:

```mermaid
flowchart LR
    frontendFeature[Frontend feature] --> frontendApi[Frontend API]
    frontendApi --> backendApi[Backend API]
    backendApi --> backendService[Backend service]
    backendService --> modelCore[Model, schema, core]
    backendService --> integration[Integration adapter]
    integration --> localVision[Local vision facade]
    integration --> remoteWorker[Remote safety vision HTTP worker]
    remoteWorker --> workerVision[Worker vision facade]
```

Executable contracts hiện hành (FastAPI/Pydantic, frontend wire types, SQLAlchemy/Alembic và
tests) là nguồn sự thật. Thay đổi breaking phải được phê duyệt và có migration hoặc
compatibility test.

Các bất biến an toàn:

1. LLM chỉ diễn giải hoặc đề xuất rule có schema; deterministic code quyết định severity/routing.
2. Zone entry của một vùng enabled luôn critical, dù machine state là `running` hay `stopped`. Machine state vẫn là audit/operational context, không phải điều kiện chặn zone alert. Lỗi kênh ngoài không làm mất cảnh báo trong ứng dụng.
3. PPE chỉ được đánh giá khi máy đang `running`; khi máy `stopped`, các switch requirement và observation PPE không được tạo PPE alert.
4. Dedup theo session + track + rule key có `zone_id` + occurrence; retry dùng idempotency key. Zone collection không có giới hạn số lượng nghiệp vụ cố định và phải bị từ chối nếu hai polygon giao, chạm hoặc chứa nhau.
5. Privacy thất bại thì không persist snapshot và không được gắn `privacy_blurred=true`.
6. Audit giữ rule version, `zone_id`, machine state của zone, shift, confidence, actor và transition; không giữ raw stream. Một review nhiều vùng vẫn lưu event riêng theo từng zone.

## Trạng thái triển khai

Hiện đã có React → FastAPI qua REST/WebSocket, person detection, collection nhiều polygon với
machine state riêng, zone-scoped occurrence, grouped review, privacy gate in-memory, PostgreSQL
event history, PPE production model và RBAC. Safety Vision có thể chạy trong backend hoặc qua worker HTTP `safety_vision_v1`; cả REST/WebSocket browser và vòng RTSP server-side đều tiếp tục đi qua `FrameInferenceService`, còn rule, occurrence, HITL và persistence vẫn thuộc backend. PostgreSQL là database duy nhất cho mọi môi trường; SQLite và database fallback là đường tương thích cũ phải được loại bỏ trước khi tuyên bố hoàn tất chuyển đổi. Các capability nâng cao khác vẫn là đích cần triển khai.

Thứ tự tiến hóa theo backlog:

1. **Đóng MVP:** PPE + tracking/dedup + multi-zone một stream + event state + auth/RBAC + image parity + metrics.
2. **Bổ sung context:** zone/shift và confidence-based HITL.
3. **Nâng cao:** escalation → analytics theo zone/shift → reporting.
4. **Vận hành:** cloud, observability, backup/restore, security/performance và UAT.

## Kiến trúc media RTSP-first đã chốt

```mermaid
flowchart LR
    react[React] -->|REST| backend[Backend control plane]
    backend -->|Read and write mapping| postgres[(PostgreSQL)]
    backend -->|Upload and lifecycle control| streamer[Streamer]

    source[MP4 camera source] --> ffmpeg[FFmpeg publisher]
    ffmpeg -->|RTSP and H.264| mediamtx[MediaMTX]
    mediamtx -->|RTSP| vision[Backend and vision]
    mediamtx -->|HLS| browser[Browser scale path]
    mediamtx -.->|Optional WHEP| lowLatency[Low-latency browser]
```

RTSP là contract nguồn camera; HLS chỉ là delivery contract cho browser và không
được dùng thay bằng chứng inference. MediaMTX sở hữu protocol gateway/fan-out;
FastAPI giữ upload, registry, lifecycle control, RBAC và mapping nhưng không proxy
media bytes. Một FFmpeg publisher phục vụ một camera path. MJPEG hiện tại được
giữ làm compatibility/rollback transport đến khi browser, inference và capacity
gates hoàn tất.

HLS ưu tiên cho tải lớn vì đi qua HTTP proxy/CDN dễ hơn; WebRTC là slice riêng
nếu latency requirement thấp hơn khả năng HLS. Production giữ RTSP/publisher
trong private network, public playback qua TLS, pin MediaMTX exact version và đo
egress thực tế trước khi tuyên bố đạt 200 người × 4 camera.

### Luồng runtime của một camera

```mermaid
flowchart LR
    video["Volume: camera MP4"] --> scan[Streamer scans source]
    scan --> supervisor[One supervised FFmpeg process]
    supervisor -->|RTSP over TCP| mediaPath[MediaMTX camera path]
    mediaPath -->|Path online| ready[Gateway ready]
    ready -->|Rollback| mjpeg[Browser via MJPEG]
    ready -->|Authenticated HLS| hls[Browser via HTTPS ingress]
    ready -->|Bounded 2 FPS RTSP| inference[Backend and vision inference]
    supervisor -->|Unexpected exit| backoff[Bounded backoff]
    backoff --> supervisor
```

Camera identity đi xuyên suốt bằng `stream_camera_id`; `media_path` luôn được
server derive thành `cameras/<validated-id>`, không nhận URL tùy ý từ browser.
Mapping `camera_id ↔ stream_camera_id` vẫn thuộc backend/PostgreSQL và độc lập
với publisher lifecycle.

### Topology Railway hiện tại

```mermaid
flowchart LR
    browser[Internet browser] -->|HTTPS and MJPEG rollback| streamer["Streamer: public HTTPS"]
    volume[(Persistent video volume)] --> streamer

    subgraph privateNetwork[Railway private network]
        mediamtx["MediaMTX 1.20.1: private RTSP and HLS"]
        vision[Backend and vision RTSP reader]
    end

    streamer -->|Authenticated RTSP and H.264| mediamtx
    mediamtx -->|Private RTSP read| vision

    browser -->|REST control plane| backend["p047-app backend: mapping and RBAC"]
    backend --> postgres[(PostgreSQL)]
```

Deployment ngày 2026-08-21 đã chứng minh bốn publisher RTSP/H.264 online và
authenticated HLS gateway trả playlist thật. Source hiện có server-side RTSP
reader cùng metadata WebSocket, nhưng chưa có live RTSP-to-model/rule/event UAT
hoặc tải 200 × 4. MediaMTX vẫn private; browser chỉ đi qua HLS gateway có token.
