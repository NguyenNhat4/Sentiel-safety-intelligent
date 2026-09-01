# Phân Tích Nguyên Nhân Gốc Rễ & Giải Pháp Kiến Trúc: Quản Lý Storage & Data Retention Policy

## 1. Tóm Tắt Điểm Nghẽn

Trong hệ thống P-047, các hình ảnh chụp vi phạm an toàn (Violation Snapshots) được mã hóa mã hóa base64, thực hiện che mờ riêng tư (Privacy Redaction), vẽ bounding box và ghi trực tiếp vào ổ đĩa cục bộ (`data/snapshots/`) hoặc upload đồng bộ lên AWS S3 ngay tại luồng tạo sự kiện.

Bên cạnh đó, mặc dù bảng cơ sở dữ liệu `safety_events` đã được thiết kế các trường quản lý thời hạn lưu trữ (`snapshot_retention_until` và `audit_retention_until`), hệ thống **chưa có bất kỳ cơ chế tự động dọn dẹp (Data Retention Purging Cron Job) hoặc chính sách chuyển vùng lưu trữ (Data Lifecycle Policy)** sang Cold Storage / AWS Glacier.

Điểm nghẽn này gây nguy cơ cạn kiệt dung lượng ổ đĩa cục bộ (Disk Full) và tăng chi phí lưu trữ S3 một cách không kiểm soát khi hệ thống vận hành liên tục trong môi trường nhà máy sản xuất.

---

## 2. Phân Tích Nguyên Nhân Gốc Rễ (Root Cause Analysis)

### 2.1. Ghi Snapshot Trực Tiếp Trong Đường Cảnh Báo Critical (Direct Synchronous Snapshot Storage)

1. **Vị trí trong mã nguồn:** `backend/app/services/event_service.py` (hàm `_save_snapshot`).
2. **Cơ chế thực thi:**
   ```python
   # backend/app/services/event_service.py (dòng 425-455)
   def _save_snapshot(self, snapshot_data: str, snapshot_people: ..., snapshot_detections: ...) -> str:
       # 1. Decode Base64 image
       frame = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)

       # 2. Synchronous Privacy Blur (YuNet) & Annotation
       redaction = self._snapshot_redactor(frame, people)
       annotated = self._snapshot_annotator(redaction["image"], people, ...)

       # 3. Synchronous Disk Write I/O
       filename = f"event-{uuid.uuid4().hex}.jpg"
       snapshot_file = self._snapshot_dir / filename
       snapshot_file.write_bytes(redacted_bytes.tobytes())
       return f"/snapshots/{filename}"
   ```
3. **Phân tích nguyên nhân:**
   - Việc lưu trữ snapshot thực hiện nối tiếp (synchronously) trong hàm `create_event()`.
   - Chưa có cơ chế **Async Write-Behind Pattern**: Luồng xử lý không ghi ảnh vào một bộ đệm hàng đợi (Queue/Buffer) để xử lý sau, mà buộc phải chờ quá trình nén JPEG và ghi đĩa/upload S3 hoàn tất 100% mới trả về response sự kiện.

---

### 2.2. Thiếu Cơ Chế Tự Động Dọn Dẹp Ảnh Hết Hạn & Chuyển Vùng Lưu Trữ (Data Retention & Lifecycle Deficit)

1. **Thiết Kế Cấu Trúc Dữ Liệu Hiện Tại (`backend/app/models/event.py` & `backend/app/services/event_service.py`):**
   ```python
   # backend/app/services/event_service.py (dòng 92-96)
   db_event = SafetyEvent(
       ...
       audit_retention_until=now + timedelta(days=self._settings.audit_retention_days), # Default 90 days
       snapshot_retention_until=now + timedelta(days=self._settings.snapshot_retention_days), # Default 30 days
   )
   ```
   Hệ thống đã tự động tính toán mốc thời gian hết hạn của snapshot (`snapshot_retention_until`) và dữ liệu audit log (`audit_retention_until`) khi một sự kiện an toàn được tạo ra.

2. **Thiếu Tác Vụ Dọn Dẹp Thực Tế (Missing Purge Task):**
   - Rà soát toàn bộ dự án cho thấy **hoàn toàn chưa có background task, cron job hoặc lệnh CLI nào** thực hiện truy vấn `DELETE FROM safety_events WHERE snapshot_retention_until < NOW()` hoặc xóa tệp tin `.jpg` tương ứng trong thư mục `data/snapshots/`.
   - Thư mục `data/snapshots/` sẽ liên tục phình to về dung lượng theo thời gian.

3. **Thiếu Chính Sách Chuyển Vùng Lưu Trữ (S3 Lifecycle Policy):**
   - Khi cấu hình `MEDIA_STORAGE_BACKEND=s3` (`backend/app/services/media_asset_service.py`), tất cả snapshot vi phạm và video clip đều nằm ở S3 Standard Tier.
   - Không có cơ chế tự động chuyển snapshot cũ (ví dụ sau 14 ngày) từ **S3 Standard** sang **S3 Infrequent Access (IA)** hoặc **S3 Glacier / Deep Archive**, dẫn đến chi phí lưu trữ băng thông/dung lượng đám mây tăng cao.

---

## 3. Tác Động Đến Môi Trường Sản Xuất (Production Impact)

| Yếu tố | Trạng thái hiện tại | Rủi ro trong sản xuất |
| :--- | :--- | :--- |
| **Ghi Snapshot** | Ghi đồng bộ (Synchronous File Write) | Gây trễ luồng xử lý vi phạm ($10 - 200\text{ms}$ per event). |
| **Quản lý Ổ Đĩa Local** | Không tự động xóa tệp `.jpg` hết hạn | **Disk Full Crash:** Máy chủ bị sập khi ổ đĩa bị lấp đầy 100%. |
| **Chi phí S3 Cloud** | Lưu cố định S3 Standard vĩnh viễn | Chi phí lưu trữ đám mây tăng trưởng tuyến tính theo thời gian. |
| **Tuân thủ Bảo vệ Dữ liệu** | Không tự động purge dữ liệu quá hạn | Vi phạm các quy định về lưu trữ hình ảnh riêng tư và dữ liệu cá nhân. |

---

## 4. Kiến Trúc Giải Pháp Đề Xuất (Architectural Solution & Action Plan)

Để quản lý lưu trữ bền vững và tối ưu chi phí, hệ thống cần nâng cấp kiến trúc lưu trữ theo 3 giải pháp chính:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                   ASYNC WRITE-BEHIND STORAGE PIPELINE                    │
│                                                                          │
│  [Event Triggered] ──► [Push to In-Memory Buffer] ──► [Background Worker]│
│                                                                  │       │
│                                                                  ▼       │
│                                                      [Fast Local Storage]│
└──────────────────────────────────────────────────────────────────┬───────┘
                                                                   │
┌──────────────────────────────────────────────────────────────────┴───────┐
│                    DATA LIFECYCLE & RETENTION PURGER                     │
│                                                                          │
│   ┌──────────────────────────────────────────────────────────────────┐   │
│   │ Day 0 - 14:  Fast Local Disk / S3 Standard                       │   │
│   │ Day 15 - 30: Auto Move to S3 Glacier / Cold Storage              │   │
│   │ Day 31+:     Automated Retention Cleanup Cron (Purge Binary File)│   │
│   └──────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

### 4.1. Áp Dụng Async Write-Behind Storage Pattern

1. **Bộ Nhớ Đệm Lưu Trữ Bất Đồng Bộ (Async Snapshot Queue):**
   - Khi kích hoạt sự kiện vi phạm, luồng chính chỉ lưu tạm byte buffer của ảnh vào bộ nhớ RAM / Redis Buffer.
   - Một background task (`BackgroundTasks` của FastAPI hoặc Celery Worker) sẽ đảm nhận công việc nén JPEG, đóng dấu thông tin và ghi ra đĩa/S3 bất đồng bộ.
2. **Lợi ích:** Trả về kết quả sự kiện ngay lập tức ($< 1\text{ms}$ storage cost), không làm nghẽn luồng suy luận vision.

### 4.2. Xây Dựng Tác Vụ Dọn Dẹp Dữ Liệu Tự Động (Automated Retention Purger)

1. **Xây dựng Celery Beat Cron Task / Scheduled Worker Service:**
   - Định kỳ chạy 1 lần/ngày (vào thời gian thấp điểm, ví dụ 02:00 AM).
   - Truy vấn các sự kiện hết hạn lưu trữ ảnh:
     ```sql
     SELECT id, snapshot_path FROM safety_events
     WHERE snapshot_retention_until IS NOT NULL
       AND snapshot_retention_until < NOW()
       AND snapshot_path IS NOT NULL;
     ```
2. **Quy Trình Purge an toàn:**
   - Xóa file ảnh `.jpg` trên đĩa cục bộ `data/snapshots/` hoặc gửi yêu cầu xóa đối tượng trên S3 (`s3_client.delete_object()`).
   - Cập nhật trường `snapshot_path = NULL` và `privacy_blurred = False` trong database để giữ lại thông tin audit log nhưng giải phóng hoàn toàn dung lượng lưu trữ ảnh.

### 4.3. Cấu Hình S3 Lifecycle Policy (Tiering & Cold Storage Transition)

1. **S3 Storage Class Transitions:**
   - **0 đến 14 ngày:** Lưu trên **S3 Standard** phục vụ cho người vận hành xem lại và đánh giá sự kiện (Review Event HITL) với tốc độ nhanh nhất.
   - **15 đến 30 ngày:** Tự động chuyển đối tượng sang **S3 Standard-Infrequent Access (Standard-IA)** để giảm 50% chi phí lưu trữ.
   - **Trên 30 ngày:** Xóa tự động các tệp snapshot theo quy định retention.

2. **Cấu hình S3 Lifecycle Rule (XML/Terraform):**
   ```xml
   <LifecycleConfiguration>
       <Rule>
           <ID>P047-Snapshot-Retention-Policy</ID>
           <Status>Enabled</Status>
           <Filter><Prefix>snapshots/</Prefix></Filter>
           <Transition>
               <Days>15</Days>
               <StorageClass>STANDARD_IA</StorageClass>
           </Transition>
           <Expiration>
               <Days>30</Days>
           </Expiration>
       </Rule>
   </LifecycleConfiguration>
   ```
