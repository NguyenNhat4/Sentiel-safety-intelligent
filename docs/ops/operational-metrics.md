# Operational Metrics

## Mục đích

Operational Metrics cho biết sức khỏe vận hành của backend sau khi hệ thống chạy: request có thành công không, latency ra sao, inference có kết quả gì và WebSocket lỗi ở đâu. Đây là monitoring nhẹ cho MVP; không thay thế benchmark chất lượng model của US-13.

Nó không dùng Prometheus, Grafana hay bảng database mới. Dữ liệu được lưu trong JSONL để vẫn tồn tại sau khi backend restart.

## Luồng hoạt động

```text
HTTP request / WebSocket inference
        ↓
privacy-safe operational event
        ↓
rotated data/operational-metrics.jsonl
        ↓
GET /api/v1/operational-metrics
        ↓
Trang “Quan sát hệ thống”
```

Mỗi event là một dòng JSON hoàn chỉnh. Backend chỉ ghi event có schema hữu hạn:

- `http_request_completed`: method, route template, status class và duration.
- `websocket_connection_opened` / `websocket_connection_closed`.
- `inference_completed`: outcome và duration.
- `inference_failed`: error kind đã chuẩn hóa.
- `privacy_redaction_completed`: outcome face/fallback; lỗi YuNet chỉ ghi `yunet_inference_failed`, không ghi ảnh, box hoặc ID.

## Privacy boundary

JSONL chỉ phục vụ aggregate vận hành. Nó không ghi hoặc trả về:

- JPEG, Base64 frame, snapshot hoặc nội dung video.
- Camera ID, zone ID, session ID, frame ID hay track ID.
- Raw URL, query string, IP/client address, authorization/cookie.
- Exception text hoặc stack trace.

HTTP routes được ghi theo route template, ví dụ `/api/v1/events/{event_id}`, thay vì path thực tế. Endpoint metrics tự loại trừ chính nó để không tự tăng request count.

## Lưu trữ và retention

Mặc định file là `data/operational-metrics.jsonl`.

| Biến môi trường | Mặc định | Ý nghĩa |
|---|---:|---|
| `OPERATIONAL_METRICS_LOG_PATH` | `data/operational-metrics.jsonl` | File JSONL hiện hành |
| `OPERATIONAL_METRICS_LOG_MAX_BYTES` | 5 MiB | Kích thước trước khi rotate |
| `OPERATIONAL_METRICS_LOG_BACKUP_COUNT` | 6 | Số file backup giữ lại |
| `OPERATIONAL_METRICS_MAX_SCAN_BYTES` | 10 MiB | Giới hạn đọc cho một request aggregate |
| `OPERATIONAL_METRICS_MAX_SCAN_LINES` | 100,000 | Giới hạn số dòng quét |

Rotation tạo các file `.1`, `.2`, …; mặc định giữ tối đa khoảng 35 MiB gồm file hiện hành và sáu backup. Reader bỏ qua dòng JSON hỏng hoặc dòng cuối chưa hoàn chỉnh. Nếu chạm giới hạn scan hoặc không đọc được file, response có `partial: true` cùng `partial_reasons` thay vì trả số liệu sai mà không báo.

## API

```text
GET /api/v1/operational-metrics?window_minutes=60
```

`window_minutes` nhận từ 1 đến 1440 phút. Response chỉ gồm aggregate:

- `requests`: count và min/mean/P50/P95/max latency theo method, route, status class.
- `inference_outcomes`: tổng outcome inference.
- `errors_by_kind`: tổng lỗi theo loại ổn định.
- `records_scanned`, `skipped_malformed_records`, `partial` và thời gian window.

P50/P95 dùng nearest-rank. Với bốn mẫu `[10, 20, 30, 40]`, P50 là `20` và P95 là `40` ms.

## UI riêng

Trong frontend, chọn **Quan sát hệ thống** ở sidebar. Đây là trang read-only tách khỏi Live Monitor và Nhật ký vi phạm. Trang có:

- Window 5 phút, 1 giờ, 6 giờ hoặc 24 giờ.
- Refresh thủ công.
- KPI request, P95 latency, inference và lỗi.
- Bảng route/method/status với P50/P95.
- Breakdown inference outcome, error kind, loading/error/partial-data state.

UI không hiển thị raw log record.

Phần **WebSocket connections** hiển thị riêng số lần opened/closed cho `/api/v1/ws/inference` và `/api/v1/ws/alerts`. WebSocket không xuất hiện trong bảng HTTP vì không có HTTP method, status class hoặc request-response latency tương đương.

## Vận hành local

```bash
make setup
make run
```

Tạo traffic rồi mở UI hoặc gọi API:

```bash
curl -s http://localhost:8000/health >/dev/null
curl -s "http://localhost:8000/api/v1/operational-metrics?window_minutes=5" | jq
```

`make setup` và `make run` chạy `alembic upgrade head` để database mới có schema hiện hành. Database legacy không có `alembic_version` được bootstrap trước khi upgrade; không chỉnh schema trực tiếp từ model khi runtime.

## Giới hạn hiện tại

- Chỉ hỗ trợ một process ghi file. Không chạy nhiều Uvicorn/Gunicorn workers cùng ghi hoặc rotate JSONL.
- Metrics phù hợp operational visibility, không tính precision/recall/false-alarm hay browser-to-render end-to-end latency của US-13.
- Khi cần scale nhiều worker/cloud, thay JSONL bằng centralized logging/metrics sink trước.
