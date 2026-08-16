# Models (YOLO & PPE Weights)

Thư mục này chứa các artifact model được pin và quản lý bằng Git LFS. Runtime hiện hành
chỉ dùng YOLO11m Safety ONNX cho person canonical, tracking và PPE.

## Checkpoint runtime

1. **`models/yolo11m_safety.onnx`**
   - Runtime artifact xuất từ source checkpoint bên dưới, fixed 640px với NMS trong graph.
   - File: `yolo11m_safety.onnx`, kích thước `80421341` bytes.
   - SHA-256: `bab27de97cb0beabb896e1afd0dc44d1abb50f05d932525a6e0169d251a508f2`.
   - Runtime dùng ONNX Runtime CPUExecutionProvider qua Ultralytics; `PPE_MODEL_PATH` phải trỏ tới file này.
2. **`models/yolo11m_safety.pt`**
   - Repository: `wesjos/Yolo-hard-hat-safety-vest`.
   - Revision pin: `95ffeeb1e0897d60564c811ace5935bcd43d982b`.
   - File: `yolo11m_safety.pt`, kích thước `121046621` bytes.
   - SHA-256: `f53324f39d76da6017d41038e74f95b3dceb33524738721e03f69f3ea58a1ece`.
   - Giấy phép khai báo trên model card: Apache-2.0.
   - Chỉ dùng làm source của `scripts/export_safety_model_to_onnx.py`, không phải runtime fallback.
   - Mapping nguồn chính xác trong checkpoint là `{0: hat, 1: nohat, 2: novest, 3: person, 4: vest}`. Startup kiểm tra toàn bộ mapping này và fail nếu khác.
   - Profile public `hat_vest_v1` chỉ chạy/chấp nhận source ID `0`, `3`, `4`, rồi chỉ phát hành `hat`, một `person` canonical và `vest`. `nohat`/`novest` không đi qua contract; backend tự suy luận qualified absence cho requirement đang bật.
   - Model ONNX được gọi đúng một lần mỗi frame. Detection `person` class `3` là nguồn canonical duy nhất cho bounding box, `foot_point`, zone rule, ByteTrack và payload; `hat`/`vest` từ cùng call được associate vào person đó.

## Artifact đã retire

`models/yolo11n.pt` là person baseline cũ, SHA-256 `0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1`. Artifact không còn được cấu hình, preload hoặc gọi trong runtime sau khi person canonical chuyển sang class `3` của YOLO11m Safety; file chỉ được giữ cho lịch sử/benchmark có kiểm soát.

`models/ppe_yolov8n.pt` là checkpoint SH17 cũ, SHA-256 `5449f62bd7cf30c01c7fd138db2729a38abcb4d5120449773fba475d54f30b62`. US-28 đã loại artifact này khỏi cấu hình, startup, inference, privacy và annotation runtime. File chỉ còn để bảo toàn lịch sử/release có kiểm soát và không được xem là dependency đang hoạt động.

## Lưu ý về Git

- Các file `.pt` và `.onnx` bị ignore mặc định; artifact runtime được allowlist rõ ràng trong `.gitignore`.
- Checkpoint trong thư mục này được Git LFS quản lý theo `.gitattributes`, không lưu trực tiếp vào Git object database.
