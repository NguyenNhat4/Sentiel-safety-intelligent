# Model Inference Benchmark Report

> Kết quả bên dưới là bằng chứng lịch sử của checkpoint YOLO11m cũ. Runtime
> `yolo11n_safety_kd_best.pt` được chọn ngày 2026-08-25 và chưa có benchmark
> tương đương; không dùng số liệu này để đánh giá checkpoint KD.

## Scope

Baseline lịch sử: đo smoke latency khi một frame đi qua tuần tự hai model theo flow US-28 trước cutover single-model:

1. `models/yolo11n.pt` — detect người.
2. `models/yolo11m_safety.pt` — chạy source class `[0, 3, 4]` tương ứng `hat`, `person`, `vest`.

Input là ảnh regression local `640 × 640`; thiết bị CPU, Python 3.14, Ultralytics 8.4.115 và PyTorch 2.13.0. Đây là smoke benchmark của cutover, không thay thế final evaluation US-13.

## Command

```bash
PYTHONPATH=. .venv/bin/python scripts/benchmark_model.py \
  --pipeline \
  --source runs/detect/predict/0_jpg.rf.645d920fa4e6fea3a11538f2e809d7d7.jpg \
  --warmup 2 \
  --iterations 5 \
  --frames 1 \
  --device cpu
```

## Result

| Metric | Result |
|---|---:|
| Warmup | 2 frames |
| Measured | 5 frames |
| Mean latency | **477.46 ms/frame** |
| P50 latency | **472.20 ms/frame** |
| P95 latency | **504.02 ms/frame** |
| P99 latency | **504.60 ms/frame** |
| Throughput | **2.09 FPS** |
| Confidence threshold | `0.35` |

## Interpretation

- Smoke run đạt khoảng `2.09 FPS` trên CPU và xấp xỉ cadence frontend `2 FPS`; CPU là ranh giới hiệu năng chặt, không có headroom đáng kể.
- Kết quả xác nhận pipeline chỉ gọi mỗi model một lần/frame với class filter runtime, nhưng mẫu 5 lần không đủ để đặt SLO.
- Trước pilot phải chạy lại trên video calibration/final US-13, đủ sample và đúng CPU/GPU mục tiêu để chốt P50/P95, throughput, precision/recall và false alarm.

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
