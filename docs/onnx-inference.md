# ONNX inference cho Safety detector

## Mục đích

P-047 dùng một model để phát hiện `person`, `hat` và `vest` trên mỗi frame. Model
được lưu ở định dạng ONNX để runtime có thể dùng ONNX Runtime trên CPU thay vì nạp
checkpoint PyTorch `.pt` làm model inference. Thay đổi này không sửa REST API,
WebSocket message, rule PPE, zone, hay cách người vận hành review cảnh báo.

Người dùng cuối vẫn thấy cùng bounding box, track ID theo session và kết quả PPE.
Thay đổi nằm dưới lớp `vision`: `PpeVisionFacade` chỉ chấp nhận `.onnx`; Ultralytics
chọn ONNX Runtime (`CPUExecutionProvider`) để chạy model và vẫn cung cấp kết quả
YOLO/ByteTrack tương thích với boundary hiện có.

## Thành phần và trách nhiệm

| Thành phần | Vai trò |
|---|---|
| `models/yolo11m_safety.pt` | Source checkpoint đã phê duyệt; chỉ dùng để tái xuất artifact có kiểm soát. Không phải runtime fallback. |
| `scripts/export_safety_model_to_onnx.py` | Export cố định source → output, 640px, NMS trong graph, rồi in SHA-256. |
| `models/yolo11m_safety.onnx` | Artifact runtime được Git LFS quản lý và kiểm tra checksum lúc startup. |
| `PPE_MODEL_PATH` | Phải trỏ tới `models/yolo11m_safety.onnx`; default/template mới đã đặt giá trị này. |
| `vision/api.py` | Từ chối `.pt` ở runtime, giữ mapping `{hat, nohat, novest, person, vest}` và chỉ phát hành `person`, `hat`, `vest`. |

ONNX Runtime là engine chạy graph; Ultralytics chỉ giữ adapter YOLO/ByteTrack để không
phải sao chép preprocess, NMS và tracking sang một implementation thứ hai. Facade luôn
truyền `device="cpu"` cho cả predict và track: khi máy có CUDA, điều này ngăn Ultralytics
tự chọn GPU và cố AutoUpdate `onnxruntime-gpu` thay vì dùng dependency `onnxruntime` CPU.

## Cách tái tạo artifact

Chỉ tái tạo khi source checkpoint được Product Owner phê duyệt lại. Không chạy exporter
trên weight tùy ý và không sửa checksum để bỏ qua validation.

```bash
make setup
PYTHONPATH=. .venv/bin/python scripts/export_safety_model_to_onnx.py
```

Ghi SHA-256 mà script in ra vào cả `backend/app/core/startup_validation.py` và
`models/README.md`, sau đó chạy kiểm tra và benchmark. Artifact mới phải được theo dõi
bằng Git LFS; không commit trực tiếp file binary thường.

Với clone cũ đã có `.env.development`, sửa một dòng trước `make run`:

```dotenv
PPE_MODEL_PATH=models/yolo11m_safety.onnx
```

Clone mới chỉ cần `make setup` rồi `make run`; template môi trường đã có giá trị ONNX.

## Kiểm tra thực tế

```bash
PYTHONPATH=. .venv/bin/python - <<'PY'
import numpy as np
from ultralytics import YOLO

model = YOLO("models/yolo11m_safety.onnx")
result = model.predict(np.zeros((640, 640, 3), dtype=np.uint8), classes=[0, 3, 4], conf=0.35, verbose=False)[0]
print(result.names)
PY
```

Log phải ghi `Loading ... for ONNX Runtime inference` và `CPUExecutionProvider`; mapping
phải đúng năm class. Sau đó chạy `make check`. Nếu test local đang trỏ `DATABASE_URL`
tới Railway TCP proxy, hãy đổi sang SQLite/local DB trước: lỗi DNS database xảy ra trước
khi test ONNX được collection, nên không phải lỗi model.

## Giới hạn và rollback

- ONNX giúp tính di động của inference, không tự chứng minh chính xác hơn hay nhanh hơn.
  Cần benchmark trên đúng CPU/host trước production.
- Artifact có input cố định 640px và NMS đã nhúng để giữ output YOLO hiện có. Muốn đổi
  image size, dynamic shapes, INT8 hay postprocess là một quyết định/benchmark mới.
- Runtime fail đóng: thiếu file, sai checksum hoặc đặt `.pt` sẽ làm startup không ready.
  Rollback an toàn là deploy lại revision đã xác minh có cặp code, artifact và checksum
  khớp nhau; không đổi `PPE_MODEL_PATH` về `.pt` trong revision ONNX.

Nguồn kỹ thuật: [Ultralytics ONNX export](https://docs.ultralytics.com/modes/export) và
[ONNX Runtime Python API](https://onnxruntime.ai/docs/api/python/api_summary.html).
