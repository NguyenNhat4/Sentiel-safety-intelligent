# Phân Tích Nguyên Nhân Gốc Rễ & Giải Pháp Kiến Trúc: AI Model Inference & Latency (Nghẽn Xử Lý Mô Hình Vision)

## 1. Tóm Tắt Điểm Nghẽn

Trong môi trường vận hành thực tế của hệ thống P-047, luồng suy luận thị giác máy tính (AI Vision Pipeline) gặp phải vấn đề độ trễ cao (High Latency) và tốc độ xử lý thấp (Low FPS). Độ trễ xử lý mỗi khung hình (frame) dao động từ **150ms đến 350ms/frame** (tương đương chỉ **3 - 6 FPS** trên mỗi luồng camera).

Điều này dẫn đến không thể mở rộng hệ thống để xử lý đồng thời nhiều luồng RTSP camera realtime, gây hiện tượng tích tụ bộ nhớ đệm (buffer overflow) và sụt giảm đáng kể khả năng phản hồi thời gian thực đối với các cảnh báo an toàn lao động.

---

## 2. Phân Tích Nguyên Nhân Gốc Rễ (Root Cause Analysis)

Qua rà soát mã nguồn ở các thành phần `vision/` và `backend/app/`, nguyên nhân gốc rễ được xác định bởi 2 yếu tố kỹ thuật chính:

### 2.1. Thực Thi Mô Hình Trên PyTorch CPU & OpenCV CPU (Hardware Execution Engine Bottleneck)

1. **Mô hình YOLO11m Safety (`models/yolo11m_safety.pt`):**
   - **Vị trí trong mã nguồn:** `vision/api.py` (lớp `PpeVisionFacade._create_model`).
   - **Cơ chế thực thi:**
     ```python
     # vision/api.py (dòng 345-349)
     def _create_model(self) -> Any:
         if self._model_factory is not None:
             return self._model_factory(self._model_path)
         from ultralytics import YOLO
         return YOLO(str(Path(self._model_path)))
     ```
     Mô hình YOLO11m được khởi tạo trực tiếp qua thư viện Ultralytics PyTorch và thực thi suy luận mặc định trên **CPU** với định dạng dấu chân đơn (FP32).
   - **Độ phân giải đầu vào lớn (`imgsz=960`):** Mỗi khung hình được đưa vào suy luận ở kích thước $960 \times 960$. Việc tính toán các phép nhân ma trận (matrix multiplication) của mô hình YOLO11m trên PyTorch CPU tốn tới 120ms - 250ms cho mỗi frame.

2. **Mô hình Nhận Diện Khuôn Mặt YuNet (`models/face_detection_yunet_2023mar.onnx`):**
   - **Vị trí trong mã nguồn:** `vision/face_detection.py` (lớp `YuNetFaceDetector`).
   - **Cơ chế thực thi:**
     ```python
     # vision/face_detection.py (dòng 38-46)
     self._detector = cv2.FaceDetectorYN.create(
         model=str(self._model_path),
         config="",
         input_size=(100, 100),
         score_threshold=self._score_threshold,
         nms_threshold=0.3,
         top_k=5000,
         backend_id=cv2.dnn.DNN_BACKEND_OPENCV,
         target_id=cv2.dnn.DNN_TARGET_CPU,
     )
     ```
     Mô hình YuNet được cấu hình cứng với backend `DNN_BACKEND_OPENCV` và target `DNN_TARGET_CPU`. Do đó toàn bộ các tác vụ phát hiện khuôn mặt phục vụ che mờ riêng tư (Privacy Redaction) đều tiêu tốn thêm 30ms - 80ms CPU per frame.

---

### 2.2. Overhead Mã Hóa/Giải Mã Ảnh và Giao Thức HTTP REST khi tách Vision Worker (Network & Serialization Overhead)

Khi triển khai `vision_worker` ở dạng dịch vụ độc lập (`backend/app/vision_worker.py`), kiến trúc hiện tại sử dụng giao thức HTTP REST `POST /v1/infer` truyền dữ liệu ảnh thô qua `multipart/form-data`.

1. **Chuỗi mã hóa / giải mã nối tiếp (Encoding/Decoding Pipeline):**
   - **Sender (Backend Client - `backend/app/integrations/remote_vision.py`):**
     Backend phải mã hóa khung hình OpenCV BGR (numpy array) thành mảng byte JPEG thô bằng `cv2.imencode('.jpg', frame)`.
   - **Transport (Network HTTP):**
     Dữ liệu JPEG thô (kích thước khoảng **200KB - 600KB/frame**) được đóng gói vào HTTP Multipart Form Request. Với tốc độ 15 FPS, dung lượng băng thông mạng tiêu tốn lên tới **3MB - 9MB/giây cho 1 camera**.
   - **Receiver (Vision Worker - `backend/app/vision_worker.py`):**
     ```python
     # backend/app/vision_worker.py (dòng 73-77)
     raw_image = image.file.read(MAX_IMAGE_BYTES + 1)
     frame = cv2.imdecode(np.frombuffer(raw_image, dtype=np.uint8), cv2.IMREAD_COLOR)
     ```
     Vision worker nhận HTTP request, đọc byte stream và giải mã ngược lại thành mảng BGR `cv2.imdecode()`.

2. **Chi phí thời gian tích lũy (Cumulative Latency):**
   - Quá trình Encode JPEG (Client) + HTTP Overhead/Network I/O + Decode JPEG (Worker) tiêu tốn khoảng **25ms – 50ms/frame**.
   - Đây là chi phí "lãng phí" (pure overhead) lặp đi lặp lại trên từng frame không đóng góp vào kết quả suy luận AI.

---

## 3. Tác Động Đến Môi Trường Sản Xuất (Production Impact)

| Yếu tố | Trạng thái hiện tại | Tác động sản xuất |
| :--- | :--- | :--- |
| **Inference Engine** | PyTorch CPU / OpenCV DNN CPU | Giới hạn xử lý 3 - 6 FPS/camera; CPU load 100% khi chạy 2 camera. |
| **Băng thông mạng** | HTTP REST Multipart (JPEG thô) | Tiêu tốn 5 - 10 MB/s/camera; nghẽn cổ chai I/O mạng khi scale nhiều camera. |
| **Serialization Overhead** | `cv2.imencode` $\rightarrow$ HTTP $\rightarrow$ `cv2.imdecode` | Mất 25 - 50ms/frame chỉ cho việc đóng/mở gói dữ liệu ảnh. |
| **Khả năng mở rộng (Scale)** | Giới hạn bởi năng lực CPU vật lý | Không thể nâng số lượng camera trên 1 nút tính toán (Node). |

---

## 4. Kiến Trúc Giải Pháp Đề Xuất (Architectural Solution & Action Plan)

Để giải quyết triệt để điểm nghẽn về Inference & Latency, hệ thống cần thực hiện nâng cấp kiến trúc theo 3 giai đoạn:

```
[Camera Stream / RTSP]
        │
        ▼ (Shared Memory / Unix Socket / gRPC Protobuf Stream)
┌─────────────────────────────────────────────────────────┐
│              Vision Inference Worker Node               │
│                                                         │
│   ┌─────────────────────────────────────────────────┐   │
│   │   NVIDIA TensorRT / ONNX Runtime (CUDA/GPU)     │   │
│   │   - YOLO11m Safety (FP16 / INT8)                │   │
│   │   - YuNet Face Detector (CUDA Target)           │   │
│   └─────────────────────────────────────────────────┘   │
│                           │                             │
│                           ▼ (Dynamic Frame Batching)    │
│            [Zero-Copy Frame Buffer Pipeline]            │
└─────────────────────────────────────────────────────────┘
```

### 4.1. Chuyển Đổi Inference Engine Sang TensorRT / ONNX Runtime GPU

1. **Xuất mô hình YOLO11m Safety sang TensorRT / ONNX FP16:**
   - Biên dịch mô hình `yolo11m_safety.pt` sang định dạng **TensorRT Engine (.engine)** hoặc **ONNX Runtime với CUDA Execution Provider**.
   - Tối ưu hóa định dạng số thực sang **FP16** hoặc **INT8 quantization**.
   - Kết quả dự kiến: Giảm latency suy luận YOLO từ **150-250ms xuống 8-15ms/frame** trên GPU (NVIDIA T4 / RTX 4060).

2. **Chuyển YuNet Face Detector sang CUDA Target:**
   - Cấu hình `target_id` của YuNet sang `cv2.dnn.DNN_TARGET_CUDA` hoặc chạy qua ONNX Runtime GPU.
   - Giảm latency che mặt riêng tư từ **50ms xuống 3-5ms/frame**.

### 4.2. Thay Thế HTTP REST Bằng gRPC Streaming / Unix Domain Socket (Zero-Copy Transfer)

1. **Giao thức gRPC Bất Đồng Bộ (HTTP/2 Multiplexing):**
   - Thay thế giao thức HTTP REST `POST /v1/infer` bằng **gRPC Bidirectional Streaming** truyền Protobuf binary.
   - Loại bỏ chi phí overhead HTTP headers và multipart form parsing.

2. **Bộ Nhớ Shared Memory (Zero-Copy IPC) khi cùng Host:**
   - Nếu `vision_worker` và backend chạy trên cùng một máy chủ physical/pod, truyền khung hình qua **Shared Memory (`posix_ipc` / SharedMemory buffer)**.
   - Client ghi mảng numpy vào Shared Memory, Worker chỉ đọc địa chỉ pointer. Loại bỏ hoàn toàn 100% chi phí Encode/Decode JPEG.

### 4.3. Áp Dụng Dynamic Frame Batching & Tối Ưu Kích Thước Đầu Vào (`imgsz`)

1. **Dynamic Batching:** Gom các frame từ nhiều camera thành 1 batch (ví dụ batch size = 4 hoặc 8) trước khi đưa vào GPU inference, tận dụng tối đa năng lực tính toán song song của Tensor Core.
2. **Kích thước đầu vào thích ứng (`imgsz=640`):** Đánh giá giảm `imgsz` từ 960 xuống 640 cho luồng quan sát chung, chỉ upscale lên 960 khi cần xác minh chi tiết vi phạm.
