# Backend Integrations

Adapter tại đây chuyển đổi provider hoặc protocol bên ngoài thành interface backend dùng được. Chúng không quyết định rule an toàn, severity hay event state.

`ppe_vision.py` cache public `vision.api.PpeVisionFacade` dùng checkpoint YOLO11n Safety KD duy nhất cho person canonical, ByteTrack và observation `hat`/`vest` trong một model call mỗi frame. Adapter không quyết định alert hoặc event state.

`remote_vision.py` giữ nguyên interface facade đó nhưng chuyển một JPEG sang vision worker qua contract `safety_vision_v1`. Adapter xác thực health/response, đối chiếu `request_id`, không fallback ngầm sang local và không đưa response lỗi của provider vào exception public. `VISION_PROVIDER=local` vẫn là mặc định; remote chỉ được bật sau khi `/ping` của worker thành công.

`privacy_vision.py` là boundary độc lập cho redaction fail-closed và annotation snapshot. Adapter cache YuNet theo cấu hình; detected face được blur trước và person không có face dùng fallback 40%. Event service luôn gọi theo thứ tự `redact → annotate → persist`; privacy không tải hoặc phụ thuộc checkpoint PPE.

`telegram_notifications.py` chỉ chuyển nội dung cảnh báo đã được backend quyết định sang Telegram Bot API. Routing theo khu vực và người nhận vẫn thuộc backend service; lỗi nhà cung cấp không được làm gián đoạn inference.

`media_storage.py` cấp presigned POST/GET cho Railway Bucket, xác minh metadata object
và download vào cache server-owned khi OpenCV bắt đầu inference. Asset cũ trên volume
vẫn đọc được trong quá trình migration; browser không nhận credential bucket.
