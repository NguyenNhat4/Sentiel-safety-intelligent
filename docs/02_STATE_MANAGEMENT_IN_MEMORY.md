# Phân Tích Nguyên Nhân Gốc Rễ & Giải Pháp Kiến Trúc: State Management Trong Process Memory (Nghẽn Tracking & Anti-flicker)

## 1. Tóm Tắt Điểm Nghẽn

Hệ thống P-047 hiện tại đang duy trì toàn bộ trạng thái theo vết đối tượng (Tracking State - ByteTrack) và trạng thái làm mượt thời gian (Temporal Anti-flicker State - `PpeTemporalSmoother`) **trực tiếp trong RAM (In-Process Dictionary)** của một worker process duy nhất.

Thiết kế này tạo ra một điểm nghẽn nghiêm trọng về khả năng mở rộng (Scalability Bottleneck): Hệ thống **hoàn toàn không thể mở rộng theo chiều ngang (Horizontal Auto-scaling multi-replica)**. Khi bật từ 2 worker instances trở lên hoặc khi worker bị crash/restart, toàn bộ trạng thái vắng mặt/xuất hiện PPE và Track ID của người lao động bị phân mảnh, dẫn đến mất cảnh báo vi phạm hoặc phát sinh cảnh báo giả liên tục (flickering).

---

## 2. Phân Tích Nguyên Nhân Gốc Rễ (Root Cause Analysis)

### 2.1. Lưu Trữ Tracking & Temporal State Trong Process RAM

1. **AI Vision Layer (`vision/api.py`):**
   - **Vị trí trong mã nguồn:** Lớp `PpeVisionFacade` và `PpeTemporalSmoother`.
   - **Cơ chế lưu trữ:**
     ```python
     # vision/api.py (dòng 155-163, 179-181)
     class PpeTemporalSmoother:
         def __init__(self, temporal_frames: int = 10) -> None:
             self._temporal_frames = temporal_frames
             self._history: dict[int, _TrackPpeHistory] = {} # In-RAM dict theo track_id

     class PpeVisionFacade:
         def __init__(...):
             self._sessions: dict[str, tuple[Any, float]] = {} # ByteTrack instance in RAM
             self._smoothers: dict[str, PpeTemporalSmoother] = {} # Temporal Smoother in RAM
     ```
     Mỗi khi có một session theo dõi mới (`monitoring_session_id`), `PpeVisionFacade` khởi tạo một đối tượng ByteTrack tracker và một `PpeTemporalSmoother` rồi lưu vào các dictionary Python trong RAM của process hiện tại.

2. **Backend Violation Tracking Layer (`backend/app/services/violation_tracking_service.py`):**
   - **Vị trí trong mã nguồn:** Lớp `ViolationTrackingService`.
   - **Cơ chế lưu trữ:**
     ```python
     # backend/app/services/violation_tracking_service.py
     class ViolationTrackingService:
         def __init__(...):
             self._sessions: dict[str, SessionTrackerState] = {}
     ```
     Các chuỗi xác nhận vi phạm (activation streak frames, PPE alert confirmation frames) cũng được lưu trữ trong thuộc tính `_sessions` trong bộ nhớ RAM của backend process.

---

### 2.2. Hạn Chế Và Kịch Bản Lỗi Sản Xuất (Production Failure Scenarios)

#### Kịch Bản 1: Phân Mảnh Trạng Thái Khi Horizontal Auto-scaling (Multi-Replica Workers)

Khi lưu lượng camera tăng lên, nếu triển khai 2 hoặc nhiều replicas cho `vision-worker` đằng sau một Nginx / Kubernetes Load Balancer:

```
                  ┌─────────────────┐
                  │  Load Balancer  │
                  └────────┬────────┘
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
    ┌─────────────────┐         ┌─────────────────┐
    │ Worker Instance1│         │ Worker Instance2│
    │  (RAM State A)  │         │  (RAM State B)  │
    └─────────────────┘         └─────────────────┘
```

- **Frame $N$ (Camera 1)** được gửi tới **Worker Instance 1**: Worker 1 khởi tạo Track ID #101, đếm thiếu mũ streak = 1.
- **Frame $N+1$ (Camera 1)** được Load Balancer chuyển tới **Worker Instance 2**: Worker 2 không có bộ nhớ RAM của Worker 1. ByteTrack của Worker 2 xem đây là đối tượng mới $\rightarrow$ gán Track ID #205. `PpeTemporalSmoother` của Worker 2 khởi tạo đếm lại từ streak = 1.
- **Hậu quả:**
  - Track ID bị nhảy liên tục giữa các khung hình (ID flickering).
  - Chuỗi đếm frame xác nhận (`temporal_frames=10` hoặc `ppe_confirmation_frames=6`) liên tục bị reset về 0.
  - **Hệ thống hoàn toàn không thể phát ra cảnh báo vi phạm PPE.**

#### Kịch Bản 2: Mất Toàn Bộ State Khi Worker Process Crash Hoặc Restart

- Khi một worker instance gặp sự cố (OOM, unhandled exception, pod reschedule, deployment update), process bị kill và khởi động lại.
- **Hậu quả:** Toàn bộ dictionary `_sessions` và `_history` trong RAM bị xóa sạch. Các vụ vi phạm đang diễn ra dở dang bị mất vết, hệ thống phải mất hàng chục khung hình để tích lũy lại lịch sử đếm từ đầu.

---

## 3. Bảng So Sánh Mô Hình State Management

| Đặc điểm | In-Process Memory (Hiện tại) | Distributed State Store (Chuẩn sản xuất) |
| :--- | :--- | :--- |
| **Vị trí lưu trữ** | RAM `dict` của 1 Python process | Redis Cluster / External Shared State Store |
| **Horizontal Scaling** | ❌ Không hỗ trợ (Single Replica Only) | ✅ Hỗ trợ mở rộng vô hạn (Multi-replica / Auto-scale) |
| **Khả năng chịu lỗi (Fault Tolerance)** | ❌ Worker crash = Mất sạch tracking state | ✅ State được duy trì độc lập với chu kỳ sống của worker |
| **Độ ổn định Track ID** | Nhảy Track ID liên tục khi scale multi-worker | Giữ nguyên Track ID nhờ Session-Affinity Routing |
| **Độ trễ truy xuất State** | $< 0.1 \text{ms}$ (In-memory) | $1 - 3 \text{ms}$ (Redis In-Memory Key-Value) |

---

## 4. Kiến Trúc Giải Pháp Đề Xuất (Architectural Solution & Action Plan)

Để loại bỏ hoàn toàn điểm nghẽn State Management, hệ thống cần áp dụng kiến trúc quản lý trạng thái tập trung và điều hướng thông minh theo 2 giải pháp chính:

```
[Camera Stream / RTSP Client]
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│    Ingress / Gateway (Session-Affinity / Sticky Routing)    │
│    "Mỗi camera_id / session_id luôn tới cùng 1 Worker"      │
└────────────┬──────────────────────────────────┬─────────────┘
             │                                  │
             ▼                                  ▼
┌──────────────────────────┐        ┌──────────────────────────┐
│  Vision Worker Instance 1│        │  Vision Worker Instance 2│
└────────────┬─────────────┘        └───────────┬──────────────┘
             │                                  │
             └─────────────────┬────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Redis Cluster State Store                   │
│   - Session Tracker State (TTL = 300s)                      │
│   - Temporal Streak History Counters                        │
│   - Distributed Lock (Redlock per Camera Session)           │
└─────────────────────────────────────────────────────────────┘
```

### 4.1. Giải Pháp 1: Sticky Session / Session-Affinity Routing Cấp Gateway

1. **Điều hướng theo Camera ID / Session ID:**
   - Cấu hình Ingress / Load Balancer (Nginx, Traefik, HAProxy, Envoy) sử dụng cơ chế Hash Ring dựa trên `monitoring_session_id` hoặc `camera_id`.
   - Đảm bảo tất cả các frame thuộc cùng một phiên camera luôn luôn được định tuyến tới **cùng một Worker Replica**.
2. **Ưu điểm:** Tối ưu hóa hiệu năng, tận dụng CPU cache tại chỗ mà không làm mất Track ID của ByteTrack trong suốt chu kỳ sống của session.

### 4.2. Giải Pháp 2: External State Store Với Redis (Distributed Tracking & Temporal State)

1. **Tách State Ra Khỏi Memory Process:**
   - Chuyển toàn bộ dữ liệu làm mượt `_TrackPpeHistory` và trạng thái `SessionTrackerState` sang lưu trữ trên **Redis Key-Value**.
   - Cấu trúc Key trên Redis:
     - `p047:tracker:session:{monitoring_session_id}:track:{track_id}` (Hash)
     - Khóa lưu các trường: `hat_present_streak`, `hat_missing_streak`, `last_seen_timestamp`.
     - Đặt cơ chế tự động dọn dẹp (TTL - Time To Live = 300 seconds).

2. **Serialized Tracker Snapshot (Cho ByteTrack):**
   - Lưu vết ma trận trạng thái của ByteTrack (Kalman Filter state & track feature vector) vào Redis khi worker thực hiện xong frame.
   - Khi một worker mới tiếp quản phiên (failover), worker có thể khôi phục lại trạng thái ByteTrack chính xác từ Redis snapshot.

3. **Khả Năng Chịu Lỗi Cao (High Availability):**
   - Khi một worker instance bị sập, các worker còn lại có thể đọc state từ Redis và tiếp tục đếm chuỗi xác nhận vi phạm mà không làm đứt đoạn tiến trình.
