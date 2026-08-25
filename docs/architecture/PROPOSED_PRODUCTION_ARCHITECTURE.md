# Báo Cáo Phân Tích Vấn Đề Hiện Tại & Kiến Trúc Sản Xuất Chuẩn Công Nghiệp (Loại Bỏ Scope Streaming)

> **Lưu ý Phạm Vi (Scope Boundary):** Dựa trên định hướng dự án và yêu cầu thực tế, luồng **Live Streaming (RTSP / WebRTC / MediaMTX / Streamer / HLS)** được xác định là **OUT OF SCOPE** (Nằm ngoài phạm vi). Hệ thống giữ nguyên cơ chế Quản lý Media Asset dạng Direct-File (Upload ảnh/video mô phỏng) và phát qua REST/WebSocket như hiện tại.

---

## 1. Phân Tích Chi Tiết Các Vấn Đề Cốt Lõi Của System Hiện Tại

Dù dự án P-047 có cấu trúc mã nguồn sạch và phân lớp rất tốt giữa `frontend/`, `backend/`, và `vision/`, hệ thống vẫn gặp một số **điểm nghẽn kỹ thuật (bottlenecks)** quan trọng khi đưa vào môi trường vận hành sản xuất thực tế:

### 1.1. AI Model Inference & Latency (Nghẽn Xử Lý Mô Hình Vision)
- **Chạy trên PyTorch CPU / Python Wrapper:**
  - Mô hình YOLO11m Safety (`yolo11m_safety.pt`) và YuNet Face Detector hiện chạy qua PyTorch CPU hoặc OpenCV CPU.
  - Latency xử lý mỗi frame dao động từ **150ms – 350ms/frame**, dẫn đến tốc độ FPS thấp, không đáp ứng được yêu cầu phản hồi gần realtime khi xử lý nhiều camera.
- **Overhead Mã Hóa/Gửi Frame Qua HTTP REST:**
  - Khi tách `vision_worker` chạy độc lập, backend phải mã hóa từng frame thành JPEG thô và gửi qua HTTP REST `POST /v1/infer` (`multipart/form-data`).
  - Việc encode JPEG và giao thức HTTP REST tạo ra **overhead băng thông và CPU lớn** không cần thiết cho mỗi frame.

### 1.2. State Management Dính Chặt Với Process Memory (Nghẽn Tracking & Anti-flicker)
- **Tracking State Trong RAM In-Process:**
  - Luồng ByteTrack (`_sessions`) và bộ lọc làm mượt thời gian (`PpeTemporalSmoother`) đang được lưu trực tiếp trong Python dictionary (`dict`) trong RAM của 1 worker process.
- **Hạn Chế:**
  - Không thể mở rộng theo chiều ngang (Horizontal Auto-scaling multi-replica worker): Nếu bật 2 worker instances, state tracking bị phân mảnh làm mất Track ID của người trong frame.
  - Khi worker crash hoặc restart, toàn bộ lịch sử tracking bị xóa sạch.

### 1.3. Đồng Bộ Hóa Request Path & I/O Latency (Nghẽn Xử Lý Bất Đồng Bộ)
- **Thực Thi Gần Như Đồng Bộ (Synchronous Execution Path):**
  - Trong luồng xử lý frame, việc đánh giá quy tắc an toàn (Zone Intrusion, PPE requirement), tính toán occurrence, thực hiện privacy redaction (che mặt), lưu đĩa/S3 và phát thông báo Telegram... được thực thi nối tiếp trong luồng chính hoặc WebSocket loop.
- **Rủi Ro:**
  - Nếu Database ghi chậm hoặc kết nối mạng tới S3/Telegram bị trễ/timeout, toàn bộ luồng suy luận vision bị đình trệ (block frame inference pipeline).

### 1.4. Quản Lý Storage & Data Retention
- **Lưu Trữ Ảnh/Snapshot Trực Tiếp Trong Đường Cấp Báo:**
  - Snapshot vi phạm được mã hóa, redact và upload trực tiếp lên S3/Volume cục bộ trước khi trả kết quả event. Chưa có cơ chế Async Write-behind hoặc chính sách Data Lifecycle Policy (Tự động chuyển snapshot cũ sang Cold Storage / Glacier).

---

## 2. Bảng Tóm Tắt Vấn Đề Hiện Tại vs Giải Pháp Chuẩn Công Nghiệp (Excluding Streaming)

| Hạng mục | Trạng thái hiện tại | Giải pháp Chuẩn Industry Standard | Hành động chuyển đổi |
|---|---|---|---|
| **AI Inference Engine** | PyTorch CPU / OpenCV CPU wrapper. | TensorRT FP16 / ONNXRuntime GPU Execution Provider. | Convert `.pt` -> `.onnx`/`.engine`, tích hợp ONNXRuntime-GPU/Triton. |
| **Worker Protocol** | HTTP REST POST multipart/JPEG overhead cao. | High-speed Binary Protocol / gRPC hoặc Shared Memory IPC. | Chuyển sang gRPC / Protobuf hoặc tối ưu hóa binary Payload payload. |
| **Tracking & Temporal State** | In-Memory `dict` trong RAM của 1 process Python. | Distributed Key-Value Store (Redis Store với TTL theo session). | Tách ByteTrack state và Temporal Smoother ra Redis store. |
| **Xử Lý Sự Kiện & Alert** | Đồng bộ trong pipeline inference frame. | Event-Driven Async Queue (Redis Streams / Celery / ARQ). | Đẩy bước Lưu Snapshot DB/S3 và Gửi Telegram vào Async Worker. |
| **Storage Evidence** | Ghi S3/Volume trực tiếp trong request path. | Async Write-Behind + S3 Lifecycle Auto-Archiving. | Upload snapshot bất đồng bộ; đặt S3 Lifecycle Rule lưu trữ 90 ngày. |
| **Live Streaming** | **OUT OF SCOPE** (Giữ nguyên REST/WS upload hiện tại). | **OUT OF SCOPE** (Không đụng tới RTSP/WebRTC/MediaMTX). | Giữ nguyên direct-file media asset library & WebSocket overlay. |

---

## 3. Kiến Trúc Mục Tiêu (Target Industry-Standard Architecture - Non-Streaming Focus)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DIRECT FILE / MEDIA ASSET                         │
│  (React UI Upload Video/Image -> Railway Bucket / Local Volume Cache)        │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │ Sampled Frame Buffer
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       ACCELERATED VISION INFERENCE LAYER                    │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ Triton Inference Server / ONNXRuntime GPU Worker                      │  │
│  │ - Model: YOLO11m Safety (TensorRT FP16 Engine)                        │  │
│  │ - Model: YuNet Privacy Redaction (ONNX TensorRT Execution)            │  │
│  └──────────────────────────────────┬────────────────────────────────────┘  │
└─────────────────────────────────────┼───────────────────────────────────────┘
                                      │ Detection JSON Payload (Bounding Boxes)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      DISTRIBUTED STATE & EVENT BROKER                       │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Redis Key-Value & Message Queue                                      │  │
│  │  - ByteTrack & Temporal Smoothing State Store (Redis Keys)           │  │
│  │  - Event Task Queue (Redis Streams / Celery / ARQ)                   │  │
│  └──────────────────────────────────┬────────────────────────────────────┘  │
└─────────────────────────────────────┼───────────────────────────────────────┘
                                      │ Async Task Stream
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BACKEND RULE & ASYNC WORKERS                        │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  FastAPI Application + Async Background Workers                       │  │
│  │  - Rule Evaluation (Zone Intrusion & PPE Gate)                        │  │
│  │  - Occurrence Deduplication & Event Creation                          │  │
│  │  - Async Privacy Snapshot Generation & S3 Upload                      │  │
│  │  - Async Notification Dispatcher (Telegram Bot API)                   │  │
│  └──────────────┬───────────────────┬──────────────────────┬─────────────┘  │
└─────────────────┼───────────────────┼──────────────────────┼────────────────┘
                  │                   │                      │
                  ▼                   ▼                      ▼
┌───────────────────┐       ┌───────────────────┐  ┌────────────────────────┐
│  DATABASE         │       │  OBJECT STORAGE   │  │   REALTIME FRONTEND    │
│  - PostgreSQL     │       │  - S3 Bucket      │  │   - React 19 UI        │
│  - Alembic        │       │  - Auto-Archiving │  │   - WebSocket Alerts   │
└───────────────────┘       └───────────────────┘  └────────────────────────┘
```

---

## 4. Kế Hoạch Tác Chiến 5 Ngày Cho Team 4 Người (Fast-Track 5-Day Plan)

Không đụng tới Video Streaming giúp team **tiết kiệm 40% khối lượng công việc hạ tầng**, cho phép tập trung 100% nguồn lực vào **Tối ưu tốc độ AI (Inference Speed), Bất đồng bộ hóa công việc (Async Pipeline), và Phân tách State (Distributed Tracking)**.

### 4.1. Phân Chia Vai Trò Chi Tiết (Role Ownership)
- **Dev 1 (AI Acceleration Lead):** Export model YOLO11m Safety & YuNet sang TensorRT FP16 / ONNXRuntime-GPU. Tối ưu `/v1/infer` API dưới **20ms/frame**.
- **Dev 2 (Backend Async Lead):** Tích hợp Redis Queue (Celery / ARQ) để tách toàn bộ I/O nặng (Lưu S3, Gửi Telegram, Batch insert DB) ra khỏi luồng xử lý frame.
- **Dev 3 (Distributed State & Redis Lead):** Chuyển đổi ByteTrack tracking state và `PpeTemporalSmoother` từ Python RAM `dict` sang Redis Store.
- **Dev 4 (Frontend & Integration QA):** Tối ưu hóa UI React 19, xử lý WebSocket reconnection, Optimistic UI cho Event Review, và viết End-to-End Test Benchmark.

---

### 4.2. Lộ Trình Triển Khai 5 Ngày Theo Mục Tiêu Ngày (Day-by-Day Roadmap)

#### **Ngày 1: Benchmark, Environment Freeze & Task Queue Setup**
- **Sáng (Tất cả):** Họp chốt Interface contract API/WebSocket hiện tại. Thêm Service `redis:7-alpine` vào `docker-compose.yml` và `.env.development`.
- **Dev 1 (AI):** Benchmark baseline tốc độ hiện tại. Export `yolo11m_safety.pt` sang ONNX format với Dynamic Axes.
- **Dev 2 (Backend):** Khởi tạo Celery/ARQ async worker framework trong `backend/app/core/celery_app.py`.
- **Dev 3 (State):** Thiết kế Redis Key Schema cho tracking state: `session:{session_id}:tracks` và `session:{session_id}:smoother`.
- **Dev 4 (Frontend):** Rà soát frontend performance, chuẩn bị benchmark script kiểm tra độ trễ hiển thị WebSocket.

#### **Ngày 2: AI Optimization & Async Worker Integration**
- **Dev 1 (AI):** Cấu hình ONNXRuntime với TensorRT/CUDA Execution Provider cho Vision Worker. Kiểm tra latency giảm từ **200ms -> 25ms**.
- **Dev 2 (Backend):** Chuyển hàm `send_telegram_notification` và `upload_redacted_snapshot_to_s3` thành Async Background Tasks trong Celery/ARQ.
- **Dev 3 (State):** Refactor `PpeTemporalSmoother` để đọc/ghi state trực tiếp từ Redis thay vì biến cục bộ in-process.
- **Dev 4 (Frontend):** Tối ưu rendering `DetectionOverlay.tsx` để giảm bớt React re-render không cần thiết khi nhận WebSocket frame high-FPS.

#### **Ngày 3: Binary Payload & State Externalization Verification**
- **Dev 1 & 2 (AI + Backend):** Tối ưu hóa giao thức giữa Backend và Vision Worker (gửi Compressed Binary Payload thay vì multipart/form-data JPEG thô).
- **Dev 3 (State):** Kiểm thử khả năng Horizontal Scale: Bật 2 Vision Workers cùng đọc chung State từ Redis, xác nhận không mất Track ID người.
- **Dev 4 (Frontend):** Hoàn thiện Optimistic UI cho nút Xác nhận/Bỏ qua sự kiện (Event Review/ACK) trên giao diện Safety Manager.

#### **Ngày 4: End-to-End Stress Testing & Safety Rules Audit**
- **Dev 1 & 3 (AI + State):** Chạy Stress Test: Giả lập 4-8 camera sessions chạy đồng thời. Đo chỉ số GPU VRAM, CPU Usage và Memory leak.
- **Dev 2 & 4 (Backend + Frontend):** Kiểm thử toàn bộ Safety Rules (Zone Intrusion, Machine State PPE Compliance, Anti-Flicker grace period).
- **Tất cả:** Sửa triệt để các lỗi phát sinh (Edge cases, timeout, Redis connection pool exhaustion).

#### **Ngày 5: Test Suite, Documentation & Staging Release**
- **Sáng (Tất cả):** Khóa mã nguồn (Code Freeze). Chạy toàn bộ test suites (`make check`, pytest backend/vision, frontend tests).
- **Dev 2 & 3:** Đóng gói Docker Compose Production hoàn chỉnh (`PostgreSQL`, `Redis`, `p047-app`, `vision-worker-gpu`).
- **Dev 1 & 4:** Cập nhật tài liệu kỹ thuật, hướng dẫn triển khai deployment và chuẩn bị kịch bản Rehearsal Demo.
- **Chiều:** Rehearsal Demo: Trình diễn hệ thống chạy mô phỏng 4 camera với tốc độ cực nhanh, mượt mà và ổn định chuẩn công nghiệp.

---
*Tài liệu này là kế hoạch chuẩn hóa kiến trúc chính thức cho dự án P-047 (Excluding Streaming).*
