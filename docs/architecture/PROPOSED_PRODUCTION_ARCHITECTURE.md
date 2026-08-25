# Đề Xuất Kiến Trúc Triển Khai App & AI Model Chuẩn Công Nghiệp (Industry Standard)

## 1. Tổng Quan & Đánh Giá Codebase Hiện Tại (Baseline Assessment)

Dự án **P-047** hiện tại là một **Modular Monolith** rất gọn gàng, có chất lượng code tốt, phân chia layer rõ ràng giữa `frontend/`, `backend/`, và `vision/`. Tuy nhiên, để đưa vào môi trường vận hành thực tế tại nhà máy sản xuất (phục vụ hàng chục/hàng trăm camera RT real-time 24/7 với độ trễ tối thiểu), kiến trúc thử nghiệm hiện tại cần được nâng cấp ở nhiều điểm nghẽn (bottlenecks).

### 1.1. Các Điểm Mạnh Hiện Có
- **Kiến trúc mã nguồn sạch (Clean Layering):** Đã tách biệt API, Services, Integrations, Models và Schemas theo `docs/FUTURE_PROJECT_STRUCTURE.md`.
- **Safety Rules Deterministic:** Áp dụng logic rule rõ ràng (VD: Zone intrusion luôn critical, PPE gate theo trạng thái máy running) không dựa hoàn toàn vào LLM, giúp đảm bảo tính chính xác và an toàn tuyệt đối.
- **Privacy & Anonymization:** Đã tích hợp sẵn cơ chế che mặt/đầu người (YuNet + Fallback) trước khi lưu vết snapshot.
- **Tách Vision Worker:** Đã có bước đầu tiên tách Vision Worker ra một REST service độc lập (`Dockerfile.ai`, `vision_worker.py`).

### 1.2. Các Hạn Chế & Điểm Nghẽn Khi Scale Môi Trường Công Nghiệp
1. **Luồng Ingestion & Decoding Video (Media Pipeline):**
   - *Hiện tại:* Backend đọc trực tiếp file `.mp4`/`.jpg` qua OpenCV và gửi từng frame sampled dạng HTTP POST multipart/JPEG tới Vision Worker.
   - *Hạn chế:* Tốn băng thông mạng nội bộ (mã hóa JPEG/HTTP overhead mỗi frame), CPU bottleneck khi decode H.264/H.265 bằng phần mềm, và chưa có khả năng thu nhận trực tiếp luồng **RTSP/WebRTC** từ camera IP nhà máy với Zero-Copy / GPU decoding.
2. **AI Inference & Tracking State:**
   - *Hiện tại:* PyTorch CPU / Ultralytics YOLO11m chạy qua FastAPI, giữ state tracking (ByteTrack) trong bộ nhớ RAM in-process của 1 worker instance.
   - *Hạn chế:* Tốc độ FPS thấp (CPU), không thể scale-out horizontal nhiều worker cho cùng 1 camera do tracking state bị dính chặt vào process (Process-bound state). Không sử dụng được GPU acceleration như TensorRT, Triton Inference Server.
3. **Đồng Bộ & Xử Lý Sự Kiện (Event-Driven Pipeline):**
   - *Hiện tại:* Xử lý đồng bộ (synchronous execution) trong request-response cycle hoặc WebSocket loop.
   - *Hạn chế:* Nếu DB ghi chậm hay S3 latency cao sẽ gây nghẽn toàn bộ pipeline inference.
4. **Lưu Trữ Snapshot & Video Evidence:**
   - *Hiện tại:* Lưu trực tiếp lên đĩa cục bộ (`MEDIA_ASSET_DIR`) hoặc S3 đơn lẻ. Chưa có chính sách Data Retention, cold storage archive cho dữ liệu video/snapshot lớn theo thời gian.

---

## 2. Kiến Trúc Đích Chuẩn Công Nghiệp (Target Industry-Standard Architecture)

Dưới đây là sơ đồ tổng thể kiến trúc hybrid Edge-Cloud chuẩn công nghiệp dành cho Computer Vision Real-time Safety Monitoring:

```
[ IP Cameras (RTSP/H.264/H.265) ]
               │
               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       EDGE / ON-PREMISE INGESTION LAYER                     │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ MediaMTX / NVIDIA DeepStream / LiveKit (RTSP -> WebRTC / Frame Stream) │  │
│  └──────────────────────────────────┬────────────────────────────────────┘  │
└─────────────────────────────────────┼───────────────────────────────────────┘
                                      │ NVMM GPU Zero-Copy Stream
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          AI INFERENCE & VISION LAYER                        │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Triton Inference Server / NVIDIA DeepStream Engine                  │  │
│  │  - Model: YOLO11m Safety (TensorRT FP16 / INT8 Precision)             │  │
│  │  - Model: YuNet / RetinaFace TensorRT (Privacy Redaction)            │  │
│  │  - Multi-Object Tracking: NvTracker / ByteTrack C++ Extensions        │  │
│  └──────────────────────────────────┬────────────────────────────────────┘  │
└─────────────────────────────────────┼───────────────────────────────────────┘
                                      │ Detection Payload (JSON Metadata)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        EVENT BUS & MESSAGE BROKER                           │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Apache Kafka / Redis Streams / NATS JetStream                        │  │
│  └──────────────────────────────────┬────────────────────────────────────┘  │
└─────────────────────────────────────┼───────────────────────────────────────┘
                                      │ High-throughput Event Queue
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BACKEND & RULE ENGINE                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  FastAPI Stateful Business Logic Workers                              │  │
│  │  - Zone Intrusion Geometry (Shapely / GEOS C Engine)                 │  │
│  │  - PPE Rule Validation & Anti-Flicker Temporal State                  │  │
│  │  - Human-in-the-loop (HITL) Triage & Escalation                       │  │
│  └──────────────┬───────────────────┬──────────────────────┬─────────────┘  │
└─────────────────┼───────────────────┼──────────────────────┼────────────────┘
                  │                   │                      │
                  ▼                   ▼                      ▼
┌───────────────────┐       ┌───────────────────┐  ┌────────────────────────┐
│  DATA STORAGE     │       │   NOTIFICATION    │  │   REALTIME FRONTEND    │
│  - PostgreSQL     │       │   - Telegram Bot  │  │   - React 19 UI        │
│  - TimescaleDB    │       │   - MQTT / PLC    │  │   - WebRTC Live Stream │
│  - MinIO / S3     │       │   - Webhook Escal.│  │   - WebSocket Alerts   │
└───────────────────┘       └───────────────────┘  └────────────────────────┘
```

---

## 3. Các Thành Phần Cốt Lõi & Giải Pháp Công Nghệ Chi Tiết

### 3.1. Ingestion Video & Decode Tốc Độ Cao (Streaming Pipeline)
- **Công nghệ:** **NVIDIA DeepStream SDK** hoặc **MediaMTX + FFmpeg HWAccel (NVDEC/VAAPI)**.
- **Luồng xử lý:**
  1. IP Camera đẩy luồng RTSP (H.264/H.265).
  2. Ingestion service sử dụng Phần cứng GPU (NVDEC) giải mã trực tiếp vào bộ nhớ GPU (NVMM - NVIDIA Memory Management), **không đưa frame thô về RAM CPU** (Zero-Copy).
  3. Phát trực tiếp cho Browser qua **WebRTC** (độ trễ < 200ms) để Giám sát viên xem video mượt mà, thay vì gửi từng ảnh JPEG qua WebSocket/REST.

### 3.2. AI Inference Engine High-Throughput
- **Công nghệ:** **NVIDIA Triton Inference Server** với **TensorRT Export (FP16 / INT8)**.
- **Cải tiến:**
  - Chuyển model YOLO11m từ PyTorch (`.pt`) sang TensorRT Engine (`.engine`), giúp **tăng tốc 5x - 10x FPS**, giảm 70% VRAM GPU.
  - Sử dụng Triton Dynamic Batching: gom các frame từ nhiều camera chạy đồng thời trong 1 GPU inference pass.
  - Phân tách Tracking State: Dùng Redis / Shared State hoặc GStreamer Pipeline State để ByteTrack chạy ổn định khi scale-out multi-replica.

### 3.3. Hàng Đợi Sự Kiện & Tách Biệt Async Workflows (Event-Driven Architecture)
- **Công nghệ:** **Redis Streams** (cho quy mô vừa và nhỏ) hoặc **Apache Kafka / NATS** (cho hệ thống đại quy mô).
- **Lợi ích:**
  - Inference Service chỉ gửi Bounding Box + Metadata vào Event Queue.
  - Backend Rule Workers nhận message từ Queue, thực hiện kiểm tra Polygon (dùng GEOS / Shapely C-extension) và đánh giá PPE.
  - Tránh triệt để rủi ro nghẽn pipeline khi DB ghi chậm hoặc khi gửi thông báo Telegram/Email bị timeout.

### 3.4. Triển Khai Container Orchestration & Scaling (Kubernetes / KEDA)
- **Công nghệ:** Kubernetes (K3s / EKS) + KEDA (Kubernetes Event-driven Autoscaling).
- **Cơ chế scaling:**
  - **Vision Inference Pods:** Auto-scale theo số lượng luồng camera active hoặc GPU utilization.
  - **Backend Rule Pods:** Auto-scale dựa trên độ dài hàng đợi (queue length) trong Redis/Kafka.

### 3.5. MLOps, Monitoring & Observability
- **Metrics & Logging:** Prometheus + Grafana theo dõi GPU VRAM, Temperature, FPS per Camera, Inference Latency (p95, p99), WebSocket Connection Count.
- **Model Lifecycle & Drift:** MLflow để quản lý version checkpoint (`yolo11m_safety_v1.0`, `v1.1`), kết hợp không gian kiểm thử dataset US-13 hiện có.

---

## 4. Phân Tích Cụ Thể Từng Bottleneck & Giải Pháp Khắc phục (Code-level Fixes)

| Hạng mục | Trạng thái hiện tại | Chuẩn Industry Standard | Hành động chuyển đổi |
|---|---|---|---|
| **Video Decoding** | OpenCV `cv2.VideoCapture` giải mã CPU từng frame. | Hardware Accelerated GPU Decode (NVDEC / VAAPI). | Tích hợp FFmpeg CUDA / PyAV hoặc NVIDIA DeepStream backend. |
| **Model Runtime** | PyTorch CPU / Ultralytics Python wrapper. | TensorRT FP16/INT8 với Triton Inference Server. | Script export `.pt` -> `.onnx` -> `.engine` TensorRT. |
| **Live Stream Frontend** | Frame-by-frame JPEG over WebSocket/REST simulation. | WebRTC / HLS Low-Latency streaming. | Triển khai MediaMTX WebRTC gateway cho Live Monitor UI. |
| **Tracking State** | In-Memory `_smoothers` dict dính liền vào 1 process backend. | Distributed State Tracker (Redis Store hoặc Tracklet ID Router). | Tách Session Tracking state ra khỏi FastAPI web process. |
| **Snapshot Redaction** | YuNet OpenCV CPU / Gaussian Blur synchronous. | TensorRT Face/Person Blur Pipeline trực tiếp trên GPU. | Đẩy bước privacy redaction vào Triton / GPU pipeline trước khi write S3. |
| **Database & Evidence Storage** | PostgreSQL ghi trực tiếp trong request path. | Async Batch Writes + S3 Presigned Direct Upload + Lifecycle Policy. | Dùng Celery/ARQ Worker ghi DB bất đồng bộ; cài S3 Auto-Archive sang Glacier. |

---

## 5. Lộ Trình Triển Khai Theo Giai Đoạn (Phased Migration Roadmap)

### Giai đoạn 1: Chuẩn hóa Production Readiness Hiện tại (Ngắn hạn - 1-2 tuần)
1. Giữ nguyên REST/WS API hợp đồng hiện tại với React.
2. Đóng gói Docker Container tối ưu (Multi-stage build, loại bỏ dev dependencies).
3. Triển khai Async Task Queue (Celery/ARQ + Redis) cho việc ghi log event và gửi Telegram Notification.
4. Export YOLO11m Safety sang ONNX / TensorRT CPU/GPU execution provider trên ONNX Runtime để giảm 50% Latency.

### Giai đoạn 2: Tối ưu AI & Video Streaming Engine (Trung hạn - 3-4 tuần)
1. Triển khai MediaMTX làm RTSP/WebRTC Server phục vụ truyền tải video trực tiếp từ Camera nhà máy.
2. Dựng Triton Inference Server standalone container với TensorRT YOLO11m Engine.
3. Chuyển đổi `FrameInferenceService` gọi Triton gRPC client thay vì REST HTTP multipart/JPEG để tối thiểu độ trễ mạng.

### Giai đoạn 3: Cloud Edge Orchestration & MLOps (Dài hạn - 1-2 tháng)
1. Đóng gói Helm Chart và Kubernetes manifests cho ứng dụng (`p047-app`, `triton-vision`, `mediamtx`, `postgres`, `redis`).
2. Cấu hình Grafana Dashboard theo dõi các chỉ số vận hành real-time (FPS, GPU Utilization, Detection Latency, Violation Counters).
3. Thiết lập MLOps pipeline tự động Re-train model khi có dữ liệu HITL feedback từ Safety Manager.

---
*Tài liệu này là đề xuất kiến trúc chuẩn hóa chính thức phục vụ mở rộng hệ thống P-047.*
