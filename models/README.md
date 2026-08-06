# Models (YOLO & PPE Weights)

Thư mục này chứa các file trọng số mô hình AI (Model Weights / Checkpoints) được sử dụng cho phễu Computer Vision và phễu suy luận vi phạm an toàn.

## Các mô hình hiện có

1. **`models/yolo11n.pt`**:
   - Mô hình YOLO11 Nano baseline dùng để phát hiện con người (`person`, class 0) trong khung hình video.
   - Được gọi mặc định bởi `FrameInferenceService` trong Backend.

2. **`models/ppe_yolov8n.pt`**:
   - Mô hình YOLOv8 Nano đã được huấn luyện (fine-tuned) để nhận diện các trang bị bảo hộ lao động (PPE: Mũ bảo hộ, áo phản quang/áo bảo hộ, kính, v.v.).

## Lưu ý về Git
- Các file `.pt` (trọng số binary dung lượng lớn) được quản lý qua quy tắc `*.pt` trong `.gitignore` để tránh commit dữ liệu phình to repository.
