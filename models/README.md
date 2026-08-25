# Models (YOLO & PPE Weights)

Thư mục này chứa các checkpoint được pin và quản lý bằng Git LFS. Runtime dùng
YOLO11n Safety KD cho person canonical, tracking và PPE; YuNet là detector độc
lập chỉ phục vụ privacy snapshot.

## Checkpoint runtime

1. **`models/yolo11n_safety_kd_best.pt`**
   - Checkpoint knowledge-distillation do chủ dự án cung cấp ngày 2026-08-25.
   - Metadata nhúng ghi Ultralytics `8.4.128`, ngày tạo
     `2026-08-25T08:02:19.095869+00:00` và giấy phép `AGPL-3.0`.
   - Runtime file có kích thước `5480154` bytes.
   - Runtime SHA-256: `940467d80536e1a26313bd700e33d3e7a17816659ca7346708e0dc8e03aa06c6`.
   - Metadata checkpoint tham chiếu training data tại
     `/kaggle/working/PPE&Person-group-1/data.yaml`; repository/revision của
     training code và provenance/version của dataset chưa được cung cấp, nên vẫn
     là gate cần đóng trước pilot.
   - Mapping nguồn chính xác trong checkpoint là `{0: hat, 1: nohat, 2: novest, 3: person, 4: vest}`. Startup kiểm tra toàn bộ mapping này và fail nếu khác.
   - Profile public `hat_vest_v1` chỉ chạy/chấp nhận source ID `0`, `3`, `4`, rồi chỉ phát hành `hat`, một `person` canonical và `vest`. `nohat`/`novest` không đi qua contract; backend tự suy luận qualified absence cho requirement đang bật.
   - Model được gọi đúng một lần mỗi frame. Detection `person` class `3` là nguồn canonical duy nhất cho bounding box, `foot_point`, zone rule, ByteTrack và payload; `hat`/`vest` từ cùng call được associate vào person đó.

2. **`models/face_detection_yunet_2023mar.onnx`**
   - Source: official OpenCV Zoo [`models/face_detection_yunet`](https://github.com/opencv/opencv_zoo/tree/41c69c8506f4ddb038aad0f5da660cbc2a83f58e/models/face_detection_yunet).
   - Revision pin: `41c69c8506f4ddb038aad0f5da660cbc2a83f58e` (`update yunet to v2`).
   - File size: `232589` bytes.
   - SHA-256: `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`.
   - License: MIT for all files in the OpenCV Zoo YuNet model directory.
   - Runtime: OpenCV `FaceDetectorYN`, OpenCV DNN backend and CPU target. The 2023 model has static ONNX input dimensions, so this runtime deliberately does not force the OpenCV 5 ONNX Runtime engine.
   - Privacy only: every detected face is expanded and blurred. A canonical person without an associated face retains the conservative upper-40% fallback; YuNet never affects PPE or violation decisions.

## Artifact đã retire

`models/yolo11m_safety.pt` là runtime Safety cũ từ
`wesjos/Yolo-hard-hat-safety-vest`, revision
`95ffeeb1e0897d60564c811ace5935bcd43d982b`, SHA-256 runtime
`e5b2ad353a33579e821ed9be77ed8406b7bac14bb8abf5d6db77b071ea021218`.
Artifact được giữ để rollback/benchmark có kiểm soát nhưng không còn được cấu
hình, kiểm tra startup hoặc copy vào production image.

`models/yolo11n.pt` là person baseline cũ, SHA-256 `0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1`. Artifact không còn được cấu hình, preload hoặc gọi trong runtime sau khi person canonical chuyển sang class `3` của Safety checkpoint; file chỉ được giữ cho lịch sử/benchmark có kiểm soát.

`models/ppe_yolov8n.pt` là checkpoint SH17 cũ, SHA-256 `5449f62bd7cf30c01c7fd138db2729a38abcb4d5120449773fba475d54f30b62`. US-28 đã loại artifact này khỏi cấu hình, startup, inference, privacy và annotation runtime. File chỉ còn để bảo toàn lịch sử/release có kiểm soát và không được xem là dependency đang hoạt động.

## Lưu ý về Git

- Các file `.pt` bị ignore mặc định; checkpoint runtime mới được allowlist rõ ràng trong `.gitignore`.
- Checkpoint `.pt` và `.onnx` trong thư mục này được Git LFS quản lý theo `.gitattributes`, không lưu trực tiếp vào Git object database.
