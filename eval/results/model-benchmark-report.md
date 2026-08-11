# Model Inference Benchmark Report

## Scope

Đo tốc độ khi một frame đi qua tuần tự hai model giống flow inference hiện tại:

1. `models/yolo11n.pt` — detect người.
2. `models/ppe_yolov8n.pt` — detect PPE/object.

Input là `data/test.mp4`, kích thước frame `1280 × 720`.

## Command

```bash
PYTHONPATH=. .venv/bin/python scripts/benchmark_model.py \
  --pipeline \
  --warmup 5 \
  --iterations 30 \
  --frames 30
```

## Result

| Metric | Result |
|---|---:|
| Warmup | 5 frames |
| Measured | 30 frames |
| Mean latency | **94.25 ms/frame** |
| P50 latency | **93.92 ms/frame** |
| P95 latency | **96.30 ms/frame** |
| P99 latency | **105.75 ms/frame** |
| Throughput | **10.61 FPS** |
| Confidence threshold | `0.35` |

## Interpretation

- Model pipeline có khả năng xử lý khoảng `10.61 FPS` trong điều kiện benchmark hiện tại.
- Frontend hiện lấy mẫu khoảng `2 FPS` (`0.5 giây/frame`), vì vậy inference model chưa phải nút thắt tốc độ trong flow hiện tại.
- Một frame chạy qua cả hai model mất trung bình khoảng `94 ms`, chưa đến `0.1 giây`.

## Measurement boundary

Thời gian trên bao gồm preprocessing, inference và postprocessing của hai lệnh Ultralytics `predict()`.

Không bao gồm:

- Đọc/decode video.
- Mã hóa JPEG phía frontend.
- Truyền WebSocket.
- Xử lý và render Canvas trên trình duyệt.
- Database hoặc lưu snapshot.

Vì vậy đây là **model pipeline benchmark**, không phải end-to-end browser latency. Khi đổi máy,
GPU/CPU, video hoặc confidence threshold, cần chạy lại benchmark trước khi so sánh.
