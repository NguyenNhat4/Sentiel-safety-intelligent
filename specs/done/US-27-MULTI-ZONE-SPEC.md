# Spec: US-27 — Giám sát nhiều vùng nguy hiểm trên một video

> Trạng thái: Hoàn thành implementation; browser UAT nhiều vùng vẫn thuộc release gate cuối MVP.

## Trạng thái đặc tả

- Phase: **3 — Implemented, verification pending**.
- Trạng thái: **Đã triển khai backend/frontend và automated tests; chờ browser UAT cuối MVP**.
- Phạm vi owner khi triển khai: cross-cutting giữa `frontend` và `backend`; `vision` không đổi public facade trong lát cắt này.
- Runtime hiện tại vẫn chỉ hỗ trợ một `zone_01`. Nội dung dưới đây là target contract, không phải mô tả tính năng đã chạy.

## Objective

Cán bộ an toàn có thể giám sát nhiều máy hoặc khu vực nguy hiểm xuất hiện trong cùng một video mô phỏng. Mỗi vùng có polygon bốn điểm và trạng thái máy riêng. Hệ thống chạy detection/tracking hiện hành một lần trên mỗi frame, sau đó đánh giá foot point của từng người với mọi vùng active và yêu cầu Human-in-the-Loop khi một occurrence xâm nhập mới xuất hiện trong bất kỳ vùng đang chạy nào.

Thành công nghĩa là một video có thể theo dõi đồng thời nhiều vùng mà không trộn trạng thái máy, không tạo event lặp, không mất bằng chứng vùng khi nhiều vi phạm xảy ra cùng frame và không phá client một vùng hiện tại trong giai đoạn chuyển đổi.

## Quyết định đã duyệt

Product Owner đã duyệt:

1. Vẫn chỉ có một video/monitoring session tại một thời điểm; multi-camera và nhiều stream đồng thời ngoài phạm vi.
2. Không có giới hạn số vùng ở cấp sản phẩm. UI/backend không được hard-code `max_zones`; generic request/message-size và runtime safety controls vẫn áp dụng cho mọi payload, không riêng zone collection.
3. Mỗi vùng luôn là polygon đúng bốn điểm chuẩn hóa; polygon tự cắt hoặc có diện tích bằng 0 không hợp lệ.
4. Các polygon active phải rời nhau hoàn toàn. Giao cạnh, chạm biên/đỉnh hoặc polygon chứa polygon khác đều bị từ chối vì foot point trên biên hiện được tính là ở trong vùng.
5. Mỗi vùng có trạng thái máy mô phỏng độc lập. PLC và đồng bộ trạng thái máy thật ngoài phạm vi.
6. Cấu hình vùng được lưu tại backend theo `camera_id=uploaded_video`, dùng chung sau reload; video file vẫn chỉ tồn tại cục bộ trong browser.
7. Một review có thể gộp nhiều occurrence mới ở các vùng rời nhau, nhưng persistence tạo event riêng cho từng vùng để giữ filter/statistics theo `zone_id` chính xác.
8. US-27 chỉ sở hữu nhiều vùng cấm và zone intrusion. Model SH17, PPE profile toàn frame `uploaded_video/zone_01`, requirement mũ/kính/găng, suy luận `missing`, cảnh báo, UI và persistence PPE giữ nguyên behavior hiện hành; PPE theo zone không thuộc story này.
9. Tạo mới zone chỉ bắt đầu từ một nút **Tạo vùng** rõ ràng; Canvas không tự chuyển sang vẽ hoặc tạo zone từ click thông thường.

## Phạm vi chức năng

### Zone collection

Một zone có các field:

| Field | Quy tắc |
|---|---|
| `zone_id` | ID bất biến trong camera, 1–50 ký tự `[A-Za-z0-9_-]`, duy nhất không phân biệt hoa thường. |
| `display_name` | Tên cho người vận hành, 1–100 ký tự sau khi trim. |
| `points` | Đúng bốn `{x, y}` theo thứ tự vẽ; mỗi tọa độ thuộc `[0, 1]`. |
| `machine_state` | `running` hoặc `stopped`; mặc định khi tạo là `stopped` theo fail-safe vận hành. |
| `enabled` | Vùng tắt vẫn được lưu và hiển thị trong editor nhưng không tham gia inference/rule. |
| `order` | Số nguyên không âm dùng để hiển thị và chọn primary summary ổn định. |

Collection cho phép 0 zone để detection và PPE hiện hành tiếp tục chạy khi người dùng chưa cấu hình vùng. Không có hằng số giới hạn số zone; chỉ zone enabled tham gia geometry/rule. Generic HTTP/WebSocket payload-size limits vẫn có thể từ chối request quá lớn, nhưng error không được biểu diễn như giới hạn nghiệp vụ về số zone.

Zone đã lưu không bị hard-delete trong US-27. Người dùng có thể xóa draft chưa lưu hoặc chuyển `enabled=false`; event lịch sử tiếp tục tham chiếu `zone_id` cũ.

### UI editor

- Hiển thị danh sách vùng với màu ổn định, tên, trạng thái máy và trạng thái enabled.
- Chỉ một vùng được chọn để chỉnh sửa polygon tại một thời điểm; Canvas vẫn vẽ tất cả vùng.
- UI có đúng một nút **Tạo vùng** làm entrypoint tạo mới. Click Canvas khi chưa bấm nút chỉ thực hiện selection hiện hành và không thêm điểm/zone.
- Khi bấm **Tạo vùng**, UI tạo một draft với ID server-compatible, tên `Vùng N`, máy `stopped`, `enabled=true`, tự chọn draft đó và chuyển Canvas sang drawing mode `0/4`.
- Bốn click hợp lệ tiếp theo trên video lần lượt tạo bốn điểm chuẩn hóa và hiển thị tiến độ `1/4` đến `4/4`. Chỉ click trong vùng ảnh video thực, không tính letterbox/padding.
- Trong drawing mode chỉ tồn tại một draft chưa hoàn thành. Nút **Tạo vùng** bị disable cho đến khi draft đủ bốn điểm hoặc người dùng chọn **Hủy tạo vùng**.
- **Hủy tạo vùng** xóa draft chưa lưu và thoát drawing mode. Reset/undo chỉ sửa điểm của draft hiện tại, không ảnh hưởng các zone đã lưu.
- Sau điểm thứ tư, UI thoát drawing mode nhưng zone vẫn là draft được chọn để người dùng đổi tên, kéo/xóa/reset điểm, bật/tắt hoặc đổi machine state trước khi lưu.
- Thay đổi chỉ là draft cho đến khi **Lưu cấu hình vùng** thành công. Reload hoặc lỗi lưu không được giả vờ đã áp dụng.
- Khi server trả `409 revision_conflict`, UI giữ draft, tải revision mới và yêu cầu người dùng hòa giải thay vì ghi đè im lặng.
- Nếu polygon đang chỉnh giao, chạm hoặc chứa polygon active khác, UI chỉ rõ hai zone xung đột và không cho lưu; backend vẫn là boundary quyết định cuối cùng.
- Overlay dùng màu/label đủ phân biệt và không chỉ dựa vào màu; vùng `running` và `stopped` có kiểu đường hoặc nhãn khác nhau.

### Inference và rule

1. Vision chạy SH17/person tracking đúng một lần cho frame.
2. Backend chuyển bốn điểm của từng zone active sang pixel và đánh giá foot point của từng person với từng polygon. Model/tracker cost không nhân theo số zone; geometry có độ phức tạp `O(person_count × zone_count)` trên mỗi frame.
3. Mỗi person nhận `zone_memberships`; `inside=true` tính cả biên polygon như contract hiện tại.
4. Một zone vi phạm khi có person bên trong và chính zone đó có `machine_state=running`.
5. Occurrence key của xâm nhập là `zone_intrusion:{zone_id}`. State đầy đủ vẫn là `(monitoring_session_id, track_id, rule_key)`.
6. US-27 thêm `review_required=true` khi có ít nhất một occurrence `zone_intrusion:{zone_id}` mới. Nhánh PPE hiện hành vẫn hoạt động theo US-07/US-08 nhưng không được sửa bởi US-27; violation đã review không mở popup lại.
7. Reconfigure trong cùng session không reset tracker. Vùng bị tắt/xóa khỏi configure hoặc chuyển `stopped` làm observation rule của vùng đó clear theo exit-confirmation hiện hành; các vùng khác không bị ảnh hưởng.
8. Vùng mới hoặc polygon vừa thay đổi có thể mở occurrence mới nếu person đang nằm trong vùng đang chạy. UI phải cảnh báo người vận hành trước khi lưu thay đổi `running` có person hiện diện.

Trước khi persist hoặc accept WebSocket configure, backend kiểm tra mọi cặp polygon active. Nếu hai polygon giao/chạm hoặc một polygon chứa polygon khác, toàn bộ collection bị từ chối với `zone_geometry_conflict` kèm hai `zone_id`; không lưu/apply một phần. Kiểm tra pairwise `O(zone_count²)` chỉ chạy khi cấu hình thay đổi, không chạy lại cho mỗi frame. Với collection hợp lệ, một foot point chỉ thuộc tối đa một zone active.

## REST configuration contract đề xuất

Sử dụng một collection resource nguyên tử cho camera cố định:

```http
GET /api/v1/cameras/{camera_id}/monitoring-zones
PUT /api/v1/cameras/{camera_id}/monitoring-zones
```

GET response:

```json
{
  "camera_id": "uploaded_video",
  "revision": 4,
  "zones": [
    {
      "zone_id": "press_01",
      "display_name": "Máy dập 01",
      "points": [
        {"x": 0.08, "y": 0.20},
        {"x": 0.42, "y": 0.20},
        {"x": 0.44, "y": 0.88},
        {"x": 0.06, "y": 0.88}
      ],
      "machine_state": "running",
      "enabled": true,
      "order": 0
    }
  ],
  "updated_at": "2026-08-11T10:00:00Z"
}
```

PUT nhận full collection cùng `expected_revision`:

```json
{
  "expected_revision": 4,
  "zones": [
    {
      "zone_id": "press_01",
      "display_name": "Máy dập 01",
      "points": [
        {"x": 0.08, "y": 0.20},
        {"x": 0.42, "y": 0.20},
        {"x": 0.44, "y": 0.88},
        {"x": 0.06, "y": 0.88}
      ],
      "machine_state": "running",
      "enabled": true,
      "order": 0
    }
  ]
}
```

Response thành công dùng cùng schema với GET. Save là atomic và idempotent; thành công tăng revision đúng một lần khi nội dung thay đổi, request retry cùng nội dung trả state hiện hành. Revision cũ trả `409` với code `revision_conflict`; polygon giao/chạm/chứa nhau trả `422` với code `zone_geometry_conflict`; database lỗi trả `503`. Mọi lỗi giữ nguyên collection cũ.

Không có record trả `revision=0`, `zones=[]`. REST error giữ response convention của FastAPI hiện hành với `detail` có code máy đọc được; WebSocket giữ `{type:"error", code, message}`. Authorization được backend bổ sung theo US-20; UI ẩn nút không thay thế permission check. API dùng naming `snake_case` để khớp contract hiện hành.

## WebSocket và REST inference contract đề xuất

### Configure đa vùng

Client mới gửi `zones`; mỗi item dùng cùng shape đã lưu:

```json
{
  "type": "configure",
  "monitoring_session_id": "3cddfe85-9428-44d7-afbf-0cd9e5fc0640",
  "camera_id": "uploaded_video",
  "zone_revision": 4,
  "zones": [
    {
      "zone_id": "press_01",
      "display_name": "Máy dập 01",
      "points": [
        {"x": 0.08, "y": 0.20},
        {"x": 0.42, "y": 0.20},
        {"x": 0.44, "y": 0.88},
        {"x": 0.06, "y": 0.88}
      ],
      "machine_state": "running",
      "enabled": true,
      "order": 0
    },
    {
      "zone_id": "forklift_lane",
      "display_name": "Làn xe nâng",
      "points": [
        {"x": 0.50, "y": 0.10},
        {"x": 0.82, "y": 0.12},
        {"x": 0.94, "y": 0.92},
        {"x": 0.62, "y": 0.90}
      ],
      "machine_state": "stopped",
      "enabled": true,
      "order": 1
    }
  ]
}
```

Boundary chấp nhận đúng một mode:

- Legacy mode: `zone_points`, `machine_state`, `zone_id` như hiện tại.
- Multi-zone mode: `zones` và optional `zone_revision`.
- Gửi đồng thời hai mode trả `validation_error` để không có hai nguồn sự thật.

Legacy mode được normalize nội bộ thành một zone và tiếp tục chạy trong thời gian deprecation. US-27 không xóa field hiện hành. Với multi-zone mode, `zone_revision` phải khớp collection đã lưu; revision cũ trả WebSocket error `zone_revision_conflict`, collection giao/chạm/chứa nhau trả `zone_geometry_conflict`, còn ack thành công echo `zone_revision` đã chấp nhận. Như vậy draft chưa lưu không thể âm thầm trở thành cấu hình inference.

### Inference result đa vùng

Các field mới là additive:

```json
{
  "people": [
    {
      "track_id": 7,
      "inside_zone": true,
      "zone_memberships": [
        {"zone_id": "press_01", "inside": true},
        {"zone_id": "forklift_lane", "inside": false}
      ],
      "active_violations": [
        {
          "occurrence_id": "cd6296d8-28d1-4aac-bca7-a6fcfc20f41c",
          "rule_key": "zone_intrusion:press_01",
          "zone_id": "press_01",
          "is_new": true
        }
      ]
    }
  ],
  "rule": {
    "person_inside_zone": true,
    "zone_results": [
      {
        "zone_id": "press_01",
        "machine_state": "running",
        "person_inside_zone": true,
        "violation": true
      },
      {
        "zone_id": "forklift_lane",
        "machine_state": "stopped",
        "person_inside_zone": false,
        "violation": false
      }
    ]
  }
}
```

Compatibility summary:

- `people[].inside_zone` vẫn là boolean và bằng `any(zone_memberships[].inside)`.
- `rule.person_inside_zone` bằng `any(zone_results[].person_inside_zone)`.
- Scalar `rule.zone_id` và `rule.machine_state` được giữ cho legacy client. Trong multi-zone mode chúng mô tả primary zone: zone có occurrence mới đầu tiên theo `order`, nếu không có thì zone active đầu tiên; client mới không được dùng hai field này để quyết định an toàn.
- `result`, `review_required`, `has_active_violation`, detection/PPE fields và binary-frame sequence không đổi nghĩa.
- REST fallback nhận cùng union legacy/multi-zone và trả cùng core response.

## Grouped review và event persistence

Một frame có occurrence mới ở nhiều zone chỉ mở một popup để tránh nhiều lần pause. Popup liệt kê từng zone, machine state, person/track và rule occurrence. Người dùng confirm hoặc false-alarm cho toàn bộ candidate trong popup ở US-27; review từng item độc lập là enhancement sau.

Client đa vùng dùng resource mới:

```http
POST /api/v1/event-batches
```

Request chứa review context/snapshot dùng chung và `events[]`; mỗi item có đúng một `zone_id` cùng occurrence IDs thuộc zone đó, và một batch không được lặp `zone_id`:

```json
{
  "monitoring_session_id": "3cddfe85-9428-44d7-afbf-0cd9e5fc0640",
  "camera_id": "uploaded_video",
  "status": "acknowledged",
  "acknowledged_by": "Safety Officer",
  "snapshot_data": "data:image/jpeg;base64,...",
  "snapshot_people": [],
  "snapshot_detections": [],
  "events": [
    {
      "zone_id": "press_01",
      "event_type": "zone_intrusion",
      "severity": "critical",
      "occurrence_ids": ["cd6296d8-28d1-4aac-bca7-a6fcfc20f41c"],
      "details": {"machine_state": "running", "video_timestamp_seconds": 7.5}
    },
    {
      "zone_id": "forklift_lane",
      "event_type": "zone_intrusion",
      "severity": "critical",
      "occurrence_ids": ["e561a2bb-2279-49ea-8488-09f93e1c1d1c"],
      "details": {"machine_state": "running", "video_timestamp_seconds": 7.5}
    }
  ]
}
```

Response `201` trả một `batch_id`, snapshot path đã redact và `events[]` theo `EventResponse` hiện hành. Backend phải:

1. Validate mọi occurrence thuộc đúng session/zone và chưa gắn event khác.
2. Redact và annotate snapshot đúng một lần trong memory.
3. Lưu một snapshot đã redact có thể được nhiều event trong batch tham chiếu.
4. Commit toàn bộ event, occurrence link và snapshot reference trong một database transaction với compensating file cleanup; lỗi bất kỳ không để lại partial event hoặc file mồ côi.
5. Retry cùng tập occurrence và cùng outcome trả batch cũ; reuse xung đột trả `409`.

Mỗi event vẫn có một `zone_id`, nên statistics/filter hiện hành không phải suy diễn từ mảng zone. `POST /api/v1/events` hiện tại tiếp tục phục vụ legacy client một vùng. Event batch của US-27 chỉ partition occurrence `zone_intrusion:{zone_id}`; PPE occurrence, event type và review semantics tiếp tục theo contract US-07/US-08 và không được gán sang zone mới.

## State và dữ liệu bền vững

Implementation dự kiến cần resource zone collection có optimistic revision. Migration phải tương thích SQLite local/test và PostgreSQL production, có downgrade, unique constraint trên `(camera_id, normalized_zone_id)` và không đọc/ghi/migrate PPE configuration hiện có.

Event batch có thể cần batch identifier và snapshot reference dùng chung. Thiết kế schema chi tiết thuộc Phase 2; không được đổi `safety_events.zone_id` thành array vì điều đó phá filter, statistics và US-21.

## Ownership và project structure

| Owner/layer | Trách nhiệm dự kiến |
|---|---|
| `frontend/features/monitor` | Zone editor, draft/applied state, selected zone, overlay và grouped review orchestration. |
| `frontend/api` / `frontend/types` | REST zone collection, WebSocket union và event-batch typed contracts. |
| `backend/api` | Boundary validation, REST collection, WebSocket configure union và event-batch transport. |
| `backend/schemas` | Zone, membership, zone result, batch request/response DTO. |
| `backend/models` | Zone persistence/revision và batch/snapshot reference nếu Phase 2 duyệt. |
| `backend/services` | Atomic zone save, multi-polygon rule evaluation, dedup orchestration và batch persistence. |
| `backend/integrations` | Không đổi; vẫn gọi vision facade một lần mỗi frame. |
| `vision` | Không đổi public contract cho US-27; chỉ trả detection/tracking observation. |

Không tạo top-level directory, `backend/app/modules`, generic `utils/helpers` hoặc chuyển geometry sang frontend. Mỗi task triển khai phải thuộc một owner/layer rõ ràng và cập nhật `docs/PROJECT_STRUCTURE.md` nếu filesystem đổi.

## Tech stack và code style

- Backend: FastAPI, Pydantic, SQLAlchemy, Alembic, OpenCV geometry.
- Frontend: React 19, TypeScript, Vite, Canvas.
- Tracking/vision: facade hiện hành, không chạy model theo số zone.

Contract dùng model có tên và collection rõ nghĩa, không dùng các list song song:

```python
class MonitoringZone(BaseModel):
    zone_id: str
    display_name: str
    points: list[ZonePoint] = Field(min_length=4, max_length=4)
    machine_state: Literal["running", "stopped"] = "stopped"
    enabled: bool = True
    order: int = Field(ge=0)
```

Rule key luôn chứa zone ID (`zone_intrusion:{zone_id}`); không ghép theo display name vì tên được phép thay đổi.

## Testing strategy

### Backend unit/domain

- Validate ID/name/coordinate, đúng bốn điểm, polygon tự cắt/zero-area, duplicate ID/order và xác nhận không có validation lỗi chỉ vì zone count.
- 0/1/n zones; machine state hỗn hợp; person ngoài/trong vùng; từ chối giao cạnh, chạm biên, chạm đỉnh và containment theo mọi thứ tự input.
- Rule result không phụ thuộc thứ tự zones; key và occurrence độc lập theo zone.
- Reconfigure chỉ clear/re-arm zone bị ảnh hưởng và không reset tracker/session.
- Vision facade/model inference được gọi số lần cố định theo frame, không nhân với số zone; PPE regression hiện hành không đổi.

### Contract/integration

- Legacy configure/response regression.
- Multi-zone configure, REST fallback parity, structured validation errors và session/reconnect ordering.
- Zone collection GET/PUT default, idempotent save, revision conflict, rollback và SQLite/PostgreSQL-compatible migration.
- Event batch success, retry, conflict, privacy failure, DB failure, file cleanup và không partial commit.

### Frontend/component

- Nút **Tạo vùng** là entrypoint duy nhất; click Canvas trước khi bấm nút không tạo điểm/zone.
- Bấm nút tạo đúng một draft `0/4`, disable nút khi draft chưa hoàn thành, nhận đúng bốn click, hỗ trợ hủy/reset và không có `max_zones`.
- Select/edit/disable zones, draft versus applied state và conflict UI hoạt động độc lập với creation mode.
- Canvas coordinate correctness cho nhiều polygon, label không chỉ dựa vào màu, selection/hit target đúng zone.
- Trạng thái máy độc lập; WebSocket gửi collection mới sau save/reconfigure.
- Grouped review hiển thị đủ candidate và tạo batch payload partition occurrence đúng `zone_id`.

### End-to-end

- Bấm **Tạo vùng**, chấm bốn điểm, lưu; lặp lại để tạo vùng thứ hai. Chỉ vùng running tạo review.
- Hai người ở hai vùng running cùng frame: một popup, hai event zone-specific sau confirm.
- Lưu collection có hai polygon giao/chạm/chứa nhau bị từ chối, revision cũ vẫn nguyên và inference tiếp tục dùng collection hợp lệ trước đó.
- Tắt/bật lại zone, exit/cooldown/re-entry và WebSocket reconnect không reset session ngoài semantics đã duyệt.
- Không zone vẫn hiển thị detection/PPE hiện hành và không có zone event; PPE behavior không đổi.

## Commands

```bash
# Setup và integrated runtime bắt buộc giữ nguyên cho team member
make setup
make run

# Full repository gate
make check

# Focused backend tests
PYTHONPATH=. .venv/bin/pytest backend/tests -v

# Frontend checks
npm --prefix frontend run lint
npm --prefix frontend run type-check
npm --prefix frontend run test
npm --prefix frontend run build
```

Python 3.11–3.13 là môi trường test được hỗ trợ; known stall của Python 3.14 không được dùng để bỏ qua focused tests và runtime smoke evidence.

## Boundaries

### Always do

- Chạy model/tracker một lần mỗi frame, sau đó fan out geometry/rule theo zone.
- Giữ `zone_id` ổn định xuyên config, rule, occurrence, review, event và audit.
- Validate tại REST/WebSocket boundary và để backend sở hữu quyết định violation.
- Persist snapshot chỉ sau redaction thành công; batch lỗi phải fail toàn bộ.
- Duy trì `make setup` và `make run` là hai lệnh duy nhất team member cần để cài/chạy.

### Ask first

- Thêm giới hạn số vùng ở cấp sản phẩm hoặc cho phép polygon giao/chạm/chứa nhau.
- Mọi thay đổi model, requirement, alert, UI, event hoặc semantics PPE; công việc đó cần story/decision riêng.
- Migration thay shape `safety_events`, chính sách hard-delete zone hoặc review từng candidate độc lập.
- Xóa/deprecate scalar contract cũ hoặc tạo API version mới.

### Never do

- Chạy detector một lần cho mỗi zone.
- Dùng frontend `inside_zone` để quyết định violation hoặc severity.
- Dùng display name làm dedup/rule key.
- Chấp nhận hoặc chỉ cảnh báo frontend khi zone collection có polygon giao/chạm/chứa nhau.
- Thay đổi profile PPE toàn frame, gắn PPE theo zone hoặc sửa logic `present`/`missing`/`unknown` trong US-27.
- Gộp nhiều zone vào một `safety_events.zone_id` giả như `multiple`.
- Reset monitoring session/tracker chỉ vì đổi polygon hoặc machine state.
- Persist raw frame/snapshot chưa redact.

## Success criteria

1. Nút **Tạo vùng** là entrypoint duy nhất để tạo một draft bốn điểm; người dùng lặp workflow này để lưu và khôi phục nhiều vùng trên `uploaded_video` mà UI/API không có hằng số giới hạn số zone, chỉnh machine state từng vùng và thấy overlay rõ ràng.
2. Backend từ chối nguyên tử mọi collection có polygon giao/chạm/chứa nhau; với collection hợp lệ, mỗi person có membership đúng và zone stopped không tạo zone occurrence.
3. Dedup hoạt động độc lập theo zone và giữ nguyên qua pause/review/reconnect/reconfigure theo state machine đã chốt.
4. Nhiều zone vi phạm trong một frame tạo một grouped review và đúng một event cho mỗi zone bị ảnh hưởng sau confirm; event đó chứa toàn bộ occurrence mới của zone, không partial save.
5. Legacy one-zone transport và `POST /events` tiếp tục vượt contract regression trong thời gian tương thích.
6. Detection/PPE hiện hành vẫn hoạt động không đổi khi có hoặc không có zone; thời gian model inference không tăng theo số zone. Load test với các fixture 0, 1, 10, 25 và 100 zone rời nhau xác nhận không có lỗi do zone count, đồng thời báo cáo riêng geometry latency p50/p95 để Product Owner đánh giá vận hành.
7. Migration SQLite/PostgreSQL, focused tests, frontend checks, `make check` trên supported Python và `make run` smoke test đạt trước khi story được chuyển sang done.

## Ngoài phạm vi

- Nhiều video/camera chạy đồng thời, RTSP production hoặc PLC.
- Tự động dừng máy.
- Polygon khác bốn điểm, hình tròn/line/geofence 3D.
- Mọi thay đổi PPE: model, requirement theo zone, profile toàn frame, association, `missing`, alert, review UI hoặc event semantics.
- CRUD zone/shift/owner đầy đủ của US-21, phân quyền nâng cao, escalation và reporting.
- Review từng occurrence độc lập trong cùng popup.

## Điều kiện qua Phase 2

US-27 đã được triển khai theo phạm vi duyệt: không có giới hạn số zone ở cấp sản phẩm; polygon giao/chạm/chứa nhau bị từ chối; grouped review dùng một quyết định chung và persistence tạo event riêng theo zone trong một batch atomic; US-27 không thay đổi behavior PPE. Browser UAT bằng video nhiều vùng vẫn thuộc release gate cuối MVP.
