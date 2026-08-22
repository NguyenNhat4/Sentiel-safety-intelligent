# Báo cáo trạng thái inference mô hình

**Dự án:** P-047 – Safety Assistance
**Ngày báo cáo:** 2026-08-22
**Phạm vi:** Luồng media và server-side inference của mô hình PPE

## 1. Tóm tắt cho quản lý

Hệ thống đã tách riêng việc phát video và việc inference mô hình. Frontend xem
video qua HLS. Backend lấy playlist HLS từ MediaMTX, giải mã frame ở mức tối đa
2 FPS, gửi frame vào Safety Vision/YOLO, sau đó áp dụng rule PPE và vùng nguy
hiểm để phát hiện occurrence và tạo luồng Human-in-the-Loop.

Luồng inference HLS hiện là **cầu nối tạm thời để chứng minh mô hình hoạt động**.
RTSP vẫn là contract nguồn CCTV mục tiêu; HLS có độ trễ cao hơn và chưa phải
bằng chứng cho capacity production.

## 2. Luồng xử lý hiện tại

```text
Video camera mô phỏng
        ↓
FFmpeg publisher
        ↓ RTSP/H.264
MediaMTX private gateway
        ↓ HLS playlist (.m3u8)
Backend HLS reader, tối đa 2 FPS/camera
        ↓ JPEG frame
Safety Vision / YOLO11m Safety
        ↓ person, hat, vest, track_id
Backend safety rules
        ↓
Detection metadata → HITL review → event/alert persistence
```

MediaMTX không chạy mô hình. Nó nhận stream, giữ camera path và cung cấp HLS
cho browser/backend. Model chạy trong backend hoặc Safety Vision worker tùy
`VISION_PROVIDER`.

## 3. Trách nhiệm của các thành phần

| Thành phần | Trách nhiệm | Không chịu trách nhiệm |
|---|---|---|
| Streamer | Đọc video mô phỏng, chạy FFmpeg publisher | Quyết định vi phạm |
| MediaMTX | RTSP ingest và HLS delivery | Chạy YOLO, lưu event |
| Backend HLS reader | Lấy playlist, giải mã frame, sampling tối đa 2 FPS | Tự quyết định quyền frontend |
| Safety Vision/YOLO | Nhận diện `person`, `hat`, `vest`, tracking | Quyết định alert cuối cùng |
| Backend rule engine | PPE, zone intrusion, debounce, occurrence, HITL | Render video |
| Frontend | Hiển thị HLS và detection metadata, gửi review | Chạy inference authoritative |

## 4. Cấu hình inference

Đặt trong Railway service `p047-app`:

```env
HLS_INFERENCE_ENABLED=true
HLS_READER_ORIGIN=http://<reader_user>:<reader_password>@mediamtx.railway.internal:8888
HLS_INFERENCE_MAX_FPS=2
```

`<reader_user>` phải có quyền `playback` trên các path `cameras/...` của
MediaMTX. Credential chỉ được đặt trong Railway Variables; không đưa vào
frontend, Git, ticket hoặc log.

Backend tự tạo playlist theo camera mapping:

```text
http://mediamtx.railway.internal:8888/cameras/<stream_camera_id>/index.m3u8
```

## 5. Điều kiện để có alert

Video hiển thị trên frontend chỉ chứng minh HLS playback. Để có alert, toàn bộ
chuỗi sau phải thành công:

1. Camera đã được mapping.
2. HLS playlist mở được từ backend.
3. Backend lấy được frame và gọi model.
4. Model trả observation hợp lệ.
5. Camera/zone có rule tương ứng; PPE cần camera state `running`.
6. Rule debounce đủ số frame.
7. Nhân viên review HITL và lưu kết quả nếu cần tạo event chính thức.

Không có frame hoặc model output thì không thể có alert.

## 6. Bằng chứng đã kiểm tra

- MediaMTX đã có các path H.264 online: `cameras/xuong1`, `cameras/xuong2`,
  `cameras/nohat`.
- HLS playlist/segment đã được tạo và frontend có thể playback.
- Safety Vision worker trả health:

```json
{
  "status": "healthy",
  "contract_version": "safety_vision_v1",
  "model_version": "yolo11m_safety-cpu-v1"
}
```

- HLS frame-source focused tests: **9 passed**.
- Ruff và Python syntax checks: **passed**.
- RTSP reader trước đây thất bại với `401 Unauthorized`; vì mục tiêu ngắn hạn
  là chứng minh model, backend đã chuyển sang HLS reader.

## 7. Giới hạn và rủi ro

- HLS có latency cao hơn RTSP và không phù hợp để tuyên bố low-latency CCTV.
- Chưa có bằng chứng soak test 200 người × 4 camera.
- Health endpoint của worker chỉ chứng minh model đã load, không chứng minh đã
  nhận frame inference.
- Cần kiểm tra thêm log/request inference, detection metadata, rule occurrence
  và event persistence end-to-end.
- RTSP vẫn là hướng production mục tiêu khi reader authentication được cấu hình
  đúng.

## 8. Tiêu chí nghiệm thu inference

Được xem là inference hoạt động khi có đủ bằng chứng:

```text
HLS playlist mở được từ backend
  + backend log "Server-side HLS camera inference started"
  + worker/backend nhận frame và trả detection
  + WebSocket có detection metadata
  + rule mở occurrence hoặc trả normal có frame_count
  + review/event được lưu khi operator xác nhận
```

Không dùng riêng `/health`, `/ping`, HLS playback hoặc MediaMTX path online để
kết luận mô hình đã inference thành công.

## 9. Kế hoạch tiếp theo

1. Đặt `HLS_READER_ORIGIN` với credential có quyền `playback`.
2. Redeploy `p047-app`.
3. Kiểm tra log không còn `401 Unauthorized`.
4. Thực hiện một camera canary với zone và rule đã cấu hình.
5. Ghi nhận detection, occurrence, review và event bằng timestamp/deployment ID.
6. Sau khi có bằng chứng HLS end-to-end, đánh giá lại RTSP reader và latency.

