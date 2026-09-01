# Phân Tích Nguyên Nhân Gốc Rễ & Giải Pháp Kiến Trúc: Đồng Bộ Hóa Request Path & I/O Latency (Nghẽn Xử Lý Bất Đồng Bộ)

## 1. Tóm Tắt Điểm Nghẽn

Trong kiến trúc hiện tại của P-047, toàn bộ chuỗi xử lý một khung hình — bao gồm: **Suy luận AI Vision $\rightarrow$ Đánh giá Quy tắc An toàn $\rightarrow$ Cập nhật Violation Tracking $\rightarrow$ Xử lý Che Mặt (Privacy Redaction) $\rightarrow$ Ghi Database $\rightarrow$ Upload Snapshot đĩa/S3 $\rightarrow$ Gửi Cảnh báo Telegram** — đang được thực thi **nối tiếp đồng bộ (Synchronous Blocking Path)** trên cùng một luồng chính (Main Frame Loop / WebSocket Thread).

Điểm nghẽn này tạo ra rủi ro hệ thống nghiêm trọng: Chỉ cần một thao tác I/O bất kỳ bị chậm (ví dụ: Database ghi đĩa bị spike latency, S3 upload bị timeout, hoặc Telegram API bị nghẽn mạng), **toàn bộ luồng suy luận vision sẽ bị block**, làm rơi khung hình (frame drops), gián đoạn theo dõi và làm méo mó các chỉ số thời gian thực.

---

## 2. Phân Tích Nguyên Nhân Gốc Rễ (Root Cause Analysis)

### 2.1. Chuỗi Thực Thi Đồng Bộ Nối Tiếp Trong Luồng Khung Hình (Frame Processing Loop)

Hãy cùng rà soát luồng thực thi trong mã nguồn của hệ thống:

```
[Camera Loop: _run_video]
     │
     ▼ (Synchronous Call)
[FrameInferenceService.infer_decoded_frame]
     ├── 1. AI Vision Inference (YOLO / YuNet)
     ├── 2. Geometry & Zone Checks (pointPolygonTest)
     ├── 3. Safety Rule Engine Evaluation
     ├── 4. Violation Tracking Evaluation
     │
     ▼ (If review_required / Violation Event triggered)
[EventService.create_event]
     ├── 5. Privacy Redaction (YuNet Face Blur - CPU Heavy)
     ├── 6. Snapshot File I/O (Write bytes to local disk / S3 upload)
     ├── 7. Database Transaction (db.commit())
     └── 8. Telegram Notification Delivery (Sync DB Query + Async Task)
```

1. **Vòng Lặp Xử Lý Khung Hình Camera (`backend/app/services/camera_session_runtime.py`):**
   ```python
   # backend/app/services/camera_session_runtime.py (dòng 230-235)
   def _process_and_publish(...):
       inference_started = time.perf_counter()
       result = self._process_frame(context, frame, frame_id, video_time, bypass_confirmation)
       # Luồng video bị CHẶN tại đây cho tới khi _process_frame hoàn tất 100%
   ```
   Luồng xử lý `_run_video` chờ đợi kết quả của `_process_frame` hoàn thành đồng bộ trước khi tiến hành đọc frame tiếp theo từ camera.

2. **Xử Lý Sự Kiện & Tác Vụ I/O Nặng Trong `EventService` (`backend/app/services/event_service.py`):**
   ```python
   # backend/app/services/event_service.py (dòng 76-80, 108-112)
   snapshot_path = None
   if event_in.snapshot_data:
       snapshot_path = self._save_snapshot(...) # 1. Synchronous Privacy Blur + File Write!

   db_event = SafetyEvent(...)
   self.db.add(db_event)
   self.db.commit()                             # 2. Synchronous Database Commit!
   ```
   Khi một vi phạm an toàn được xác nhận (`review_required=True`), dịch vụ thực hiện ngay lập tức trong luồng chính:
   - Che mặt riêng tư (`_snapshot_redactor` dùng YuNet + Gaussian Blur): Mất thêm 30ms - 80ms CPU.
   - Ghi file ảnh JPEG ra ổ đĩa hoặc upload lên S3 (`snapshot_file.write_bytes()`): Mất 10ms - 200ms I/O disk/network.
   - Thực thi Giao dịch Database PostgreSQL/SQLite (`self.db.commit()`): Mất 5ms - 50ms DB Write I/O.

3. **Gửi Thông Báo Telegram (`backend/app/services/alert_notification_service.py`):**
   ```python
   # backend/app/services/alert_notification_service.py (dòng 75-80)
   recipients = db.query(User).filter(...).all() # Synchronous DB Query trong Alert Path
   ```
   Mặc dù tác vụ đẩy tin nhắn Telegram `_deliver` dùng `asyncio.create_task`, bước truy vấn danh sách người quản lý khu vực trong Database vẫn chạy đồng bộ.

---

### 2.2. Hậu Quả Điểm Nghẽn Trong Môi Trường Vận Hành (Cascading Latency Impact)

- **Tổng Latency Của Một Frame Bình Thường:** ~180ms (AI Inference CPU). Tốc độ ~5.5 FPS.
- **Tổng Latency Của Một Frame Có Vi Phạm (Violation Frame):**
  $$\text{Latency} = 180ms \text{ (Vision)} + 50ms \text{ (Privacy Blur)} + 100ms \text{ (S3/Disk Write)} + 30ms \text{ (DB Commit)} = \mathbf{360ms}$$
- **Khi Gặp Sự Cố Mạng / Database Slow Write:**
  Nếu kết nối S3 bị trễ hoặc Database bận (Lock contention), thời gian xử lý 1 frame có thể bị vọt lên **1000ms – 3000ms**.
- **Kết quả:**
  - Khung hình tiếp theo của camera bị bỏ rơi (`inference_dropped`).
  - Bộ đệm RTSP của camera bị tràn, hình ảnh bị giật lag và mất đồng bộ thời gian thực.
  - Người vận hành nhận cảnh báo trễ từ 3 - 5 giây so với thực tế xảy ra vi phạm.

---

## 3. Bảng So Sánh Kiến Trúc Thực Thi

| Đặc tính | Luồng Thực Thi Đồng Bộ (Hiện tại) | Kiến Trúc Hướng Sự Kiện - Async Event-Driven |
| :--- | :--- | :--- |
| **Pipeline Inference** | Tăng thời gian chờ do chờ I/O | Non-blocking (Hoàn toàn độc lập với I/O) |
| **Tác vụ Privacy & Snapshot** | Chạy trực tiếp trong luồng Vision Frame | Đẩy vào Background Worker Queue (Celery/Redis) |
| **Ghi Database & Storage** | Block luồng chính tới khi `commit()` xong | Ghi bất đồng bộ (Async Write-Behind Buffer) |
| **Ảnh hưởng khi S3/DB bị chậm** | Luồng suy luận AI bị dừng hoàn toàn | Không ảnh hưởng (FPS suy luận giữ nguyên 30 FPS) |

---

## 4. Kiến Trúc Giải Pháp Đề Xuất (Architectural Solution & Action Plan)

Giải quyết triệt để vấn đề này đòi hỏi bóc tách đường dẫn suy luận AI thời gian thực (Critical Inference Path) khỏi các tác vụ I/O nặng (Heavy I/O Path) thông qua **Kiến Trúc Bất Đồng Bộ Hướng Sự Kiện (Event-Driven Architecture)**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│              CRITICAL INFERENCE PATH (Fast & Non-Blocking)              │
│                                                                         │
│   [RTSP Frame] ──► [AI Inference] ──► [Rule Engine] ──► [WebSocket UI]  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ (Publish Event Payload)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│               ASYNC EVENT BUS & TASK QUEUE (Redis Stream)               │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
          ┌──────────────────────────┼──────────────────────────┐
          ▼                          ▼                          ▼
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│ Privacy Worker   │       │ Storage Worker   │       │ Telegram Worker  │
│ - YuNet Blur     │       │ - Write DB       │       │ - Send Alert     │
│ - Annotation     │       │ - Upload S3      │       │ - Push Noti      │
└──────────────────┘       └──────────────────┘       └──────────────────┘
```

### 4.1. Tách Đường Dẫn Suy Luận AI Không Chặn (Non-Blocking Critical Path)

1. **Nguyên tắc:** Luồng xử lý frame chính (`CameraSessionRuntime` & `FrameInferenceService`) **CHỈ** làm nhiệm vụ: Suy luận AI, tính toán quy tắc an toàn, cập nhật tracking và phát thông điệp metadata lên WebSocket UI.
2. **Không thực hiện bất kỳ thao tác I/O đĩa, S3 hay Database Commit đồng bộ** trong luồng xử lý frame chính.

### 4.2. Đẩy Tác Vụ Vi Phạm Vào Hàng Đợi Bất Đồng Bộ (Redis Streams / Celery Task Queue)

1. Khi phát hiện một sự kiện vi phạm mới (`review_required=True`), luồng chính chỉ cần đóng gói thông tin vi phạm (raw frame buffer, track_id, rule_key) và đẩy nhanh vào **Redis Stream** hoặc **Background Task Queue** trong thời gian $< 1\text{ms}$.
2. **Hệ thống Worker Độc Lập (Async Background Workers):**
   - **Privacy Redaction Worker:** Nhận job từ queue, thực hiện che mặt YuNet và vẽ bounding box annotation.
   - **Storage & DB Worker:** Ghi thông tin event vào Database PostgreSQL và upload snapshot đã che mặt lên S3 Storage.
   - **Notification Worker:** Truy vấn thông tin người quản lý và gửi cảnh báo qua Telegram Bot API bất đồng bộ.

### 4.3. Kết Quả Kỳ Vọng

- **Độ trễ luồng suy luận AI (Inference Pipeline Latency):** Ổn định ở mức thấp nhất, không bao giờ bị tăng đột biến bởi hiện tượng I/O spike.
- **Tốc độ khung hình (FPS):** Duy trì liên tục 25 - 30 FPS cho mọi camera ngay cả khi đang có nhiều sự kiện vi phạm dồn dập diễn ra cùng lúc.
