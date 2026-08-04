# Models (YOLO & PPE Weights)

Thư mục này chứa các file trọng số mô hình AI (Model Weights / Checkpoints) được sử dụng cho phễu Computer Vision và phễu suy luận vi phạm an toàn.

## Các mô hình được cấu hình

1. **`models/yolo11n.pt`**:
   - Mô hình YOLO11 Nano baseline dùng để phát hiện con người (`person`, class 0) trong khung hình video.
   - Được gọi mặc định bởi `FrameInferenceService` trong Backend.
   - SHA-256: `0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1`.
   - Cần bổ sung provenance/version chính xác trước khi phát hành production; checksum này chỉ xác định artifact hiện có trong repository.

2. **`models/ppe_yolov8n.pt`**:
   - Model YOLOv8 Nano từ release `v1` của dự án SH17.
   - Nguồn: `https://github.com/ahmadmughees/SH17dataset/releases/download/v1/yolo8n.pt`.
   - SHA-256: `5449f62bd7cf30c01c7fd138db2729a38abcb4d5120449773fba475d54f30b62`.
   - Giấy phép dataset/repository: CC BY-NC-SA 4.0; cần rà soát quyền sử dụng model cho mục đích thương mại trước khi phát hành.
   - Class mapping được đọc tĩnh từ checkpoint: `person`, `ear`, `ear-mufs`, `face`, `face-guard`, `face-mask`, `foot`, `tool`, `glasses`, `gloves`, `helmet`, `hands`, `head`, `medical-suit`, `shoes`, `safety-suit`, `safety-vest` (class `0` đến `16` theo thứ tự).

`ppe_yolov8n.pt` nhận diện sự hiện diện của PPE, không có class `missing_*`. Vì vậy checkpoint này chưa tự đáp ứng semantics US-07 “thiếu PPE rõ ràng”; pipeline cần ghép PPE với từng người và chỉ kết luận thiếu sau khi áp dụng ngưỡng/logic đã được kiểm chứng. Không được suy diễn khả năng nhận diện chỉ từ tên file.

## Lưu ý về Git

- Các file `.pt` bị ignore mặc định và chỉ được thêm có chủ đích.
- Hai checkpoint trong thư mục này được Git LFS quản lý theo `.gitattributes`; không commit trực tiếp binary vào Git object database.
