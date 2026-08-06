# API Contract — Nền Tảng và Quy Ước Chung

> Chỉ mục: [`README.md`](README.md) · Endpoint: [`02-endpoint-catalog.md`](02-endpoint-catalog.md)

## 1. Mục tiêu và nguồn sự thật

Tài liệu này giúp các nhóm thống nhất tên resource, payload, trạng thái, quyền truy cập và lỗi trước khi triển khai. Nó không thay thế nguồn sự thật có thể kiểm thử:

| Boundary | Nguồn sự thật khi triển khai | Vai trò của tài liệu này |
|---|---|---|
| REST | Pydantic schema + FastAPI route của module owner | Thiết kế chung và review checklist |
| WebSocket inference | `contracts/schemas/inference-message.schema.json` | Mô tả trình tự message và semantics |
| Backend ↔ Vision | `vision-observation.schema.json` | Giải thích mapping, không để Vision quyết định nghiệp vụ |
| Frontend types | Sinh từ `contracts/generated/openapi.json` | Không duy trì type wire viết tay thứ hai |

Khi code khác tài liệu: route đã phát hành phải giữ backward compatibility; thay đổi breaking phải tạo version mới, migration path và contract test. Không sửa tay OpenAPI/generated types.

## 2. Quy ước chung

- Base URL REST: `/api/v1`.
- WebSocket: `/api/v1/ws/inference`.
- JSON dùng `snake_case`; thời gian dùng ISO 8601 UTC, ví dụ `2026-08-06T08:30:00Z`.
- ID công khai là UUID dạng chuỗi; client coi ID là opaque.
- Tọa độ ảnh chuẩn hóa trong `[0,1]`; bounding box là `[x_min, y_min, x_max, y_max]`; polygon không tự cắt.
- Mọi request có thể nhận `X-Correlation-ID`; backend sinh nếu thiếu và trả lại header này. ID đi xuyên frontend → backend → vision → event/audit.
- Request tạo/transition/retry nhận `Idempotency-Key`; cùng key và cùng actor phải trả cùng kết quả, không tạo side effect lần hai.
- Danh sách dùng `limit` (mặc định 50, tối đa 200) và `cursor`; response gồm `items` và `next_cursor`.
- Content type mặc định `application/json`; upload ảnh dùng `multipart/form-data`; frame WS dùng binary JPEG.
- Production dùng HTTPS/WSS. Không gửi Base64 ảnh trong log, query string hoặc error response.

### 2.1 Authentication và authorization

REST dùng `Authorization: Bearer <access_token>`. WebSocket gửi access token bằng cơ chế handshake được backend hỗ trợ an toàn; không đặt token trong log. Hai role chuẩn:

| Role | Quyền chính |
|---|---|
| `safety_officer` | monitor, phân tích ảnh/video, quản lý rule phiên, review/acknowledge/confirm/false alarm, xem event được phân công |
| `zone_manager` | xem dashboard/report theo phạm vi; quản lý zone, shift, assignment và lịch báo cáo |

Backend bắt buộc enforce quyền và scope zone; ẩn nút trên frontend không phải authorization. `401` là chưa/xác thực sai, `403` là đã xác thực nhưng không đủ quyền hoặc ngoài scope.

### 2.2 Error envelope

```json
{
  "error": {
    "code": "invalid_state_transition",
    "message": "Cannot transition event from confirmed to false_alarm",
    "details": {"current_status": "confirmed", "requested_status": "false_alarm"},
    "correlation_id": "01J4..."
  }
}
```

Mã HTTP chuẩn: `400` dữ liệu/nghiệp vụ sai; `401`; `403`; `404`; `409` conflict/dedup/transition; `413` file quá lớn; `415` sai MIME; `422` schema sai; `429`; `500`; `503` dependency tạm lỗi. `message` không chứa secret, raw image hoặc stack trace.

## 3. Kiểu dữ liệu dùng chung

```json
{
  "point": {"x": 0.25, "y": 0.75},
  "machine_state": "running",
  "severity": "low | medium | high | critical",
  "event_status": "pending | acknowledged | confirmed | false_alarm",
  "ppe_item": {
    "item": "helmet | glasses | gloves",
    "state": "present | missing | unknown",
    "confidence": 0.93
  }
}
```

Quy tắc semantics:

- `zone_intrusion` khi máy `running` luôn `critical`; khi máy `stopped`, observation vẫn được trả nhưng không tạo cảnh báo xâm nhập.
- PPE severity lấy từ rule đã validate, không do Vision hoặc LLM tự quyết định.
- Confidence dưới ngưỡng thấp: bỏ qua; giữa hai ngưỡng: `requires_review=true`; từ ngưỡng cao: áp rule. Giá trị ngưỡng thuộc rule version.
- `privacy_blurred=true` chỉ khi redact thành công. Nếu privacy processing thất bại, không được persist snapshot hoặc xác nhận event theo policy US-12.
