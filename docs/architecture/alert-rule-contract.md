# Contract rule alert theo khung hình

## Trạng thái

Đây là business contract bắt buộc đọc trước khi sửa `SafetyRuleEngine`,
`FrameInferenceService`, camera configuration PPE hoặc các payload inference.
Không được tự ý thay đổi các quy tắc dưới đây chỉ để làm xanh một test; mọi
thay đổi cần xác nhận sản phẩm, decision record và regression tests.

Bản chốt theo `DECISIONS.md` (2026-08-21):
- **Zone Intrusion (`zone_intrusion_enabled=true`)**: Xâm nhập vùng nguy hiểm luôn báo vi phạm (`violate`), bất kể trạng thái máy `running` hay `stopped`.
- **PPE Requirements (`hat_required`, `vest_required`)**: Thiếu PPE chỉ báo vi phạm khi người nằm trong zone có yêu cầu PPE và trạng thái máy đang hoạt động (`machine_state=running`). Trạng thái `stopped` chỉ là ngữ cảnh vận hành và không gate cảnh báo PPE.

## Rule sau khi triển khai

Một frame là `violate` khi có ít nhất một điều kiện sau:

- Có ít nhất một người nằm trong zone có `zone_intrusion_enabled=true` (bất kể máy `running` hay `stopped`).
- Có ít nhất một người nằm trong zone khi máy `running` mà thiếu PPE bắt buộc (`hat_required` hoặc `vest_required`).
- Có ít nhất một người thuộc vùng nguy hiểm bị kích hoạt `restricted_area_detection_enabled=true`.

Không có người thì frame luôn `normal`; không đánh giá thiếu PPE khi không có person detection.

## Ma trận hành vi

| Có người | Trong zone intrusion | Thiếu PPE bắt buộc | Trạng thái máy | Kết quả frame |
|---|---:|---:|---|---|
| Không | — | — | ON / OFF | `normal` |
| Có | Không | Không | ON / OFF | `normal` |
| Có | Có (`intrusion=true`) | Không | ON / OFF | `violate` |
| Có | Không | Có | OFF | `normal` |
| Có | Không | Có | ON | `violate` |
| Có | Có (`intrusion=true`) | Có | OFF | `violate` (bởi zone intrusion) |
| Có | Có (`intrusion=true`) | Có | ON | `violate` |

Với nhiều người, chỉ cần một người vi phạm là toàn frame `violate` và UI mở một review popup. Backend vẫn giữ `track_id`, `occurrence_id` và `zone_id` riêng để dedup, audit, thống kê và persist event theo zone.

## Luồng runtime

```mermaid
flowchart LR
    A[Frame JPEG] --> B[Vision facade]
    B --> C[People + PPE observations + foot points]
    C --> D[Backend SafetyRuleEngine]
    D --> E{Any person in enabled zone?}
    D --> F{Any required PPE missing?}
    E --> G[Aggregate frame decision]
    F --> G
    G -->|No| H[NORMAL\nno review snapshot]
    G -->|Yes| I[VIOLATE\nreview_required]
    I --> J[One UI review popup]
    I --> K[Per-track occurrences\nper-zone event persistence]
```

## Boundary không thay đổi

- Vision chỉ phát hiện/track/đo foot point và trả observation; không quyết định alert.
- Backend service là nơi quyết định `result`, `review_required` và occurrence.
- REST/WebSocket payload hiện hành giữ nguyên; không tạo schema frame-event mới.
- Review được gộp ở UI theo frame, nhưng persistence vẫn tạo event riêng theo zone.
- Privacy snapshot vẫn fail-closed và chỉ persist sau khi operator xác nhận.

## Team checklist

- [ ] Unit rule test cho machine `running` và `stopped` có cùng kết quả khi người ở zone.
- [ ] REST/WebSocket test cho stopped-zone trả `violate` và `review_required=true`.
- [ ] Test không có người trả `normal` dù PPE requirement bật.
- [ ] Test nhiều người chỉ cần một người vi phạm thì aggregate frame là `violate`.
- [ ] Kiểm tra occurrence/dedup và event theo zone không bị thay đổi.
- [ ] Cập nhật `DECISIONS.md`, `PROGRESS.md`, `ARCHITECTURE.md` và `backend/README.md` sau khi implementation hoàn tất.
