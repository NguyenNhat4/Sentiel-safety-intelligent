# Backend Integrations

Adapter tại đây chuyển đổi provider hoặc protocol bên ngoài thành interface backend dùng được. Chúng không quyết định rule an toàn, severity hay event state.

`ppe_vision.py` cache public `vision.api.PpeVisionFacade` dùng checkpoint YOLO11m Safety duy nhất cho person canonical, ByteTrack và observation `hat`/`vest` trong một model call mỗi frame. Adapter không quyết định alert hoặc event state.

`privacy_vision.py` là boundary độc lập cho redaction fail-closed và annotation snapshot. Adapter cache YuNet theo cấu hình; detected face được blur trước và person không có face dùng fallback 40%. Event service luôn gọi theo thứ tự `redact → annotate → persist`; privacy không tải hoặc phụ thuộc checkpoint PPE.

`telegram_notifications.py` chỉ chuyển nội dung cảnh báo đã được backend quyết định sang Telegram Bot API. Routing theo khu vực và người nhận vẫn thuộc backend service; lỗi nhà cung cấp không được làm gián đoạn inference.

`rtsp_frame_source.py` là adapter media đầu vào cho backend/vision. Nó chỉ derive
path `cameras/<stream_camera_id>` từ RTSP origin cấu hình phía server, giới hạn
tần suất lấy frame và reconnect sau lỗi đọc; browser không được cung cấp URL
RTSP tùy ý.
