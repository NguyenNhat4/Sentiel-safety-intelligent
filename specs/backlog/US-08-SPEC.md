# Spec: US-08 — Theo dõi người và chống tạo event trùng

## Trạng thái đặc tả

- Giai đoạn: **VERIFY — core implementation và browser validation với local fixture hoàn tất**
- Primary owner của tracking: `vision`
- Primary owner của violation lifecycle và dedup: `backend services`
- Phạm vi phát hành: đóng MVP
- Người dùng chính: cán bộ an toàn
- Phụ thuộc: US-03 person detection và contract PPE/rule của US-07

## Objective

Hệ thống gán một `track_id` ổn định cho mỗi người trong một phiên video và nhận biết vòng đời của từng vi phạm theo người và rule. Một vi phạm liên tục chỉ mở một occurrence và chỉ có thể tạo một event đã review; các frame tiếp theo vẫn hiển thị trạng thái vi phạm nhưng không yêu cầu review hoặc lưu event lặp.

Thành công nghĩa là cán bộ an toàn không bị video dừng liên tục vì cùng một người vẫn ở trong cùng trạng thái vi phạm. Khi người đó thực sự hết vi phạm rồi tái phạm sau thời gian re-arm, hệ thống tạo occurrence mới và cho phép một review/event mới.

## Bối cảnh runtime hiện tại

- Frontend gửi tối đa một frame mỗi `0.5` giây qua một WebSocket inference connection.
- Backend hiện xử lý từng frame độc lập; person detection chưa có `track_id`.
- `review_required=true` hiện làm frontend dừng video, đóng WebSocket và giữ một candidate trong bộ nhớ.
- Event chỉ được ghi bằng `POST /api/v1/events` sau khi cán bộ chọn vi phạm thực tế hoặc false alarm.
- `SafetyEvent.details` có thể chứa `track_id`, nhưng database chưa có dedup key hoặc unique constraint tương ứng.
- REST frame inference là fallback stateless; WebSocket là transport chính cho video/session tracking.

## Thuật ngữ

| Thuật ngữ | Ý nghĩa |
|---|---|
| Monitoring session | Một lần người dùng chọn và giám sát một video; giữ nguyên qua pause, review và reconnect ngắn. |
| Track | Chuỗi detection được vision xác định là cùng một người trong monitoring session. |
| Rule key | Định danh ổn định của một luật vi phạm, ví dụ `zone_intrusion` hoặc `missing_ppe:helmet`. |
| Occurrence | Một lần vi phạm liên tục của một `track_id` đối với một `rule_key`. |
| Active violation | Occurrence đang vi phạm hoặc đang trong lost-track grace period. |
| Cleared | Vi phạm đã hết đủ điều kiện xác nhận, sẵn sàng đi vào cooldown/re-arm. |
| Cooldown | Khoảng tối thiểu sau khi cleared mà tái xuất hiện chưa mở occurrence mới. |
| Event | Bản ghi review được lưu qua Events API; không đồng nghĩa với detection hoặc candidate. |

## Phạm vi chức năng

### Tracking theo phiên video

- Frontend tạo `monitoring_session_id` mới khi chọn một video mới.
- Cùng video giữ nguyên `monitoring_session_id` khi play/pause, mở review, tiếp tục phát hoặc WebSocket reconnect ngắn.
- Chọn video khác hoặc chủ động kết thúc phiên sẽ kết thúc tracking/dedup state cũ.
- Mỗi person detection trả một `track_id` số nguyên dương, duy nhất trong monitoring session.
- `track_id` không phải định danh sinh trắc học và không được dùng để nhận diện người xuyên phiên, xuyên video hoặc xuyên camera.
- Vision sở hữu detection-to-track association; frontend không tự ghép người bằng khoảng cách bounding box.
- Tracking state phải tách biệt theo `monitoring_session_id`; hai trình duyệt hoặc hai phiên không được dùng chung track counter/state.

### Violation occurrence

Backend tạo và cập nhật occurrence theo khóa logic:

```text
violation_key = monitoring_session_id + track_id + rule_key
```

`occurrence_id` là UUID do backend sinh khi một `violation_key` chuyển từ trạng thái có thể re-arm sang `active`. ID này giữ nguyên trong toàn bộ lần vi phạm liên tục và được dùng làm idempotency key khi lưu review event.

Các `rule_key` tối thiểu của US-08:

- `zone_intrusion`: foot point nằm trong zone khi máy đang `running`.
- `missing_ppe:helmet`.
- `missing_ppe:safety_glasses`.
- `missing_ppe:gloves`.

Một người có thể có nhiều rule active đồng thời. Một frame có nhiều occurrence mới vẫn mở một lần review tổng hợp; response và event details phải giữ đủ `occurrence_id`/`rule_key` để không làm mất chi tiết.

### State machine

```text
                 violation observed
REARMED ─────────────────────────────────> ACTIVE
   ^                                         │
   │                                         │ same violation or track temporarily lost
   │                                         └───────────────> ACTIVE
   │
   │ cooldown elapsed                violation absent for exit confirmation
COOLDOWN <────────────────────────────────── CLEARED_PENDING
   │                                             │
   └── violation during cooldown ────────────────┘ suppress new occurrence
```

Semantics bắt buộc:

- `REARMED → ACTIVE`: sinh một `occurrence_id`; chỉ transition này có `is_new=true`.
- `ACTIVE → ACTIVE`: giữ cùng occurrence; không yêu cầu review mới.
- Track mất ngắn hơn lost-track grace vẫn giữ occurrence active.
- Track ID đổi trong lost-track grace nhưng foot-point mới ở gần vị trí cuối của track cũ và cùng rule được coi là handoff, giữ nguyên occurrence đã review.
- Violation phải vắng mặt đủ exit-confirmation window mới được coi là cleared; một frame chập chờn không kết thúc occurrence.
- Tái phạm trong cooldown không tạo occurrence mới và quay lại occurrence hiện hành.
- Chỉ sau khi cleared và cooldown kết thúc, lần vi phạm tiếp theo mới sinh occurrence mới.
- Một vi phạm liên tục không được tạo occurrence mới chỉ vì thời gian trôi qua.
- Khi monitoring session hết TTL hoặc được kết thúc rõ ràng, tracker và active state được giải phóng.

### Default đề xuất cho MVP

Các giá trị phải nằm trong typed backend settings, không hard-code rải rác:

| Setting | Default đề xuất | Ý nghĩa |
|---|---:|---|
| `tracking_lost_grace_frames` | `3` | Giữ track qua tối đa 3 frame mẫu bị mất detection. |
| `violation_exit_confirm_frames` | `2` | Cần 2 frame liên tiếp không vi phạm để bắt đầu clear. |
| `violation_cooldown_seconds` | `2.0` | Khoảng re-arm sau khi clear. |
| `monitoring_session_ttl_seconds` | `300` | Giữ state qua reconnect/review; gia hạn khi có frame. |

Các default này phù hợp sampler hiện tại `2 FPS` nhưng phải có boundary tests và được Product Owner xác nhận trước implementation.

## Contract WebSocket

Thay đổi là cộng thêm. Không xóa hoặc đổi kiểu các field hiện hành.

### Configure

Frontend gửi `monitoring_session_id` trong message `configure`:

```json
{
  "type": "configure",
  "monitoring_session_id": "3cddfe85-9428-44d7-afbf-0cd9e5fc0640",
  "zone_points": [
    {"x": 0.1, "y": 0.1},
    {"x": 0.9, "y": 0.1},
    {"x": 0.9, "y": 0.9},
    {"x": 0.1, "y": 0.9}
  ],
  "machine_state": "running",
  "camera_id": "uploaded_video",
  "zone_id": "zone_01"
}
```

Validation:

- `monitoring_session_id` là UUID hợp lệ.
- Một connection chỉ gắn với một monitoring session; đổi session ID trên connection đang chạy trả error `session_mismatch`.
- Gửi lại configure với cùng session ID để đổi zone/machine state không reset tracker hoặc occurrence.
- Server trả acknowledgement cộng thêm session ID:

```json
{
  "type": "configured",
  "monitoring_session_id": "3cddfe85-9428-44d7-afbf-0cd9e5fc0640"
}
```

### Inference result

Mỗi person có `track_id` và danh sách violation occurrence của riêng người đó:

```json
{
  "type": "inference_result",
  "frame_id": 15,
  "video_time": 7.5,
  "result": "violate",
  "review_required": true,
  "has_active_violation": true,
  "people": [
    {
      "track_id": 4,
      "bbox": [420, 115, 535, 610],
      "confidence": 0.91,
      "foot_point": [477, 610],
      "inside_zone": true,
      "safety_shirt": false,
      "ppe": {
        "helmet": {"status": "missing", "confidence": 0.88},
        "safety_glasses": {"status": "unknown", "confidence": null},
        "gloves": {"status": "present", "confidence": 0.92}
      },
      "missing_required_ppe": ["helmet"],
      "active_violations": [
        {
          "occurrence_id": "7aedf540-36da-4cf8-bb9b-8cd7aeab460d",
          "rule_key": "zone_intrusion",
          "is_new": true
        },
        {
          "occurrence_id": "90494038-ea97-405b-830d-75d0b2613826",
          "rule_key": "missing_ppe:helmet",
          "is_new": true
        }
      ]
    }
  ],
  "snapshot_data": "data:image/jpeg;base64,...",
  "rule": {}
}
```

Field semantics:

- `track_id`: ổn định trong monitoring session; không tái sử dụng cho người khác trong cùng session.
- `active_violations`: occurrence đang active của person ở frame này; danh sách rỗng khi không vi phạm.
- `is_new=true`: chỉ ở response đầu tiên mở occurrence. Các frame sau trả cùng occurrence với `is_new=false`.
- `has_active_violation`: có ít nhất một occurrence active trong frame/session result.
- `review_required`: có ít nhất một occurrence `is_new=true` chưa được đưa vào review candidate.
- `result`: `violate` khi `has_active_violation=true`, nếu không là `normal`.
- `snapshot_data`: chỉ có khi `review_required=true`, giữ hành vi không gửi snapshot cho frame lặp.

Response vẫn giữ `inside_zone`, `ppe`, `missing_required_ppe`, `rule` và các field baseline hiện tại.

### Reconnect và ordering

- Backend registry khôi phục tracker/dedup state bằng `monitoring_session_id` trong TTL.
- `frame_id` vẫn phải tăng đơn điệu trong monitoring session, không reset khi reconnect hoặc resume sau review.
- Frame có `frame_id` nhỏ hơn hoặc bằng frame cuối đã xử lý trả error `stale_frame` và không thay đổi tracker/dedup state.
- Chỉ một connection inference active được phép ghi vào một monitoring session. Connection thứ hai trả `session_in_use` để tránh race condition.
- Disconnect giải phóng connection lease nhưng không xóa session state ngay; TTL cleanup phải có giới hạn bộ nhớ.

## REST frame inference

`POST /api/v1/analysis/frame` tiếp tục là fallback một-frame và giữ request hiện tại tương thích.

- Request có thể bổ sung optional `monitoring_session_id` và `frame_id` để tham gia tracking session.
- Khi thiếu hai field này, backend xử lý stateless và vẫn trả `track_id`, nhưng chỉ đảm bảo unique trong response, không cam kết ổn định qua nhiều REST calls.
- Khi client cần ổn định xuyên frame, cả `monitoring_session_id` và `frame_id` là bắt buộc cùng nhau; thiếu một trong hai trả `422`.
- REST và WebSocket dùng cùng response semantics cho `track_id`, `active_violations`, `result` và `review_required` khi REST chạy ở session mode.

## Event persistence và idempotency

US-08 không tự động persist event từ inference. Frontend vẫn chỉ gọi `POST /api/v1/events` sau HITL review.

Event create request bổ sung:

```json
{
  "monitoring_session_id": "3cddfe85-9428-44d7-afbf-0cd9e5fc0640",
  "occurrence_ids": [
    "7aedf540-36da-4cf8-bb9b-8cd7aeab460d",
    "90494038-ea97-405b-830d-75d0b2613826"
  ]
}
```

Persistence rules:

- Ít nhất một `occurrence_id` là bắt buộc cho event được tạo từ inference US-08.
- Backend xác minh occurrence thuộc monitoring session và đang/đã được review candidate hợp lệ.
- Mỗi `occurrence_id` chỉ liên kết với tối đa một `SafetyEvent`.
- Retry cùng tập occurrence và cùng review payload trả event đã tạo, không tạo row/snapshot thứ hai.
- Payload cố dùng occurrence đã gắn với event khác nhưng có nội dung xung đột trả `409`.
- Idempotency phải được enforce bằng database constraint/transaction, không chỉ kiểm tra trong bộ nhớ.
- Event response trả lại `monitoring_session_id` và `occurrence_ids`.
- Migration phải tương thích record cũ: các field mới nullable đối với historical events; contract mới chỉ bắt buộc chúng cho candidate phát sinh từ session-aware inference.

Việc hoàn thiện toàn bộ event transition `pending/acknowledged/confirmed/false_alarm` thuộc US-09. US-08 chỉ bảo đảm một occurrence không tạo nhiều row khi retry hoặc review lặp.

## Frontend behavior

- Tạo UUID session khi người dùng chọn video mới; không dùng filename làm session ID.
- Không reset `frameSequence` khi pause/resume, review hoặc reconnect cùng video.
- Dùng `review_required`, không dùng riêng `result`, để quyết định dừng video.
- Hiển thị `track_id` trên overlay/debug label để kiểm chứng MVP; không trình bày như định danh cá nhân.
- Pending review giữ toàn bộ occurrence mới trong frame và gửi chúng trong event payload.
- Sau review, cùng occurrence còn active không được mở lại dialog hoặc tạo event khác.
- Chọn video khác, kết thúc video hoặc thao tác reset session rõ ràng tạo monitoring session mới.
- Network reconnect trong TTL giữ nguyên session ID và tiếp tục frame sequence.

## Ownership và project structure

```text
vision/api.py                         # Public tracking facade/DTO
vision/pipeline.py                    # Detection + ByteTrack association khi cần tách
vision/tests/                         # Tracking sequence và lost-track tests
backend/app/integrations/             # Adapter từ vision track observation
backend/app/schemas/analysis.py       # Additive session/track/occurrence wire types
backend/app/services/                  # Session registry và deterministic dedup lifecycle
backend/app/models/event.py            # Event idempotency persistence fields
backend/app/api/v1/                    # REST/WS validation và response mapping
backend/migrations/                    # Reversible event idempotency migration
backend/tests/                         # Domain, WS, REST, DB concurrency tests
frontend/src/api/                      # Session-aware transport
frontend/src/features/monitor/         # Session/review state
frontend/src/types/                    # Additive wire types
```

Không tạo top-level directory mới, không thêm production code vào legacy `src/`, và không đưa event lifecycle vào `vision` hoặc frontend.

## Tech stack

- Vision: Ultralytics YOLO tracking/ByteTrack qua facade độc lập HTTP/database.
- Backend: Python, FastAPI, Pydantic, SQLAlchemy, Alembic.
- Frontend: React 19, TypeScript 5.7, Vite 6, Vitest.
- Persistence: SQLite local/test; PostgreSQL production target.
- ID: UUID chuẩn cho monitoring session và occurrence; integer cho track ID nội bộ phiên.

Không thêm tracking dependency mới trước khi xác minh Ultralytics/ByteTrack hiện có đáp ứng yêu cầu và license phù hợp.

## Code style

Domain types phải diễn đạt rõ state và không dùng boolean rời rạc để mô phỏng state machine:

```python
class ViolationState(StrEnum):
    REARMED = "rearmed"
    ACTIVE = "active"
    CLEARED_PENDING = "cleared_pending"
    COOLDOWN = "cooldown"


@dataclass(frozen=True)
class ViolationKey:
    monitoring_session_id: UUID
    track_id: int
    rule_key: str
```

- API/Pydantic/TypeScript wire fields dùng `snake_case` theo contract hiện tại.
- State transition nằm trong backend service thuần và có unit test; route không tự quyết dedup.
- Vision chỉ trả track observation; không biết `rule_key`, occurrence, event hoặc database.
- Không dùng `utils`, `helpers`, `common` để chứa tracking/dedup.

## Testing strategy

### Vision/unit

- Một người qua chuỗi frame giữ cùng `track_id`.
- Hai người cắt ngang hoặc overlap ngắn không ghi đè ID trong fixture đã chốt.
- Track mất 1–3 frame rồi xuất hiện lại giữ ID theo grace window.
- Track mất quá grace tạo ID mới.
- Track ID handoff gần biên zone không tạo review mới; track mới ở xa vẫn tạo occurrence độc lập.
- Hai monitoring sessions dùng state/counter độc lập.
- Empty frame, low-confidence detection và end-of-session cleanup.

### Backend domain

- `REARMED → ACTIVE` chỉ sinh một occurrence.
- Frame lặp active giữ occurrence và `is_new=false`.
- Exit confirmation chống flicker một frame.
- Mất track ngắn không clear violation.
- Clear, cooldown, tái phạm trong cooldown và tái phạm sau cooldown.
- Cùng track với nhiều rule có occurrence độc lập.
- Nhiều track cùng rule không dùng chung occurrence.
- Machine chuyển stopped clear/suppress zone rule đúng semantics.
- PPE requirement chuyển OFF không để occurrence PPE active vô hạn.

### REST/WebSocket contract

- Configure nhận UUID hợp lệ và trả session ID.
- Reconfigure cùng session không reset tracking.
- Session mismatch, session in use và stale frame trả structured error.
- `track_id`/occurrence fields cộng thêm mà field baseline vẫn nguyên kiểu.
- Reconnect trong TTL giữ ID; reconnect sau TTL bắt đầu state mới có kiểm soát.
- REST stateless behavior và session-mode validation.

### Persistence

- Retry event create với cùng occurrence trả cùng event.
- Concurrent insert cùng occurrence chỉ tạo một row và một snapshot.
- Payload xung đột trả `409`.
- Migration upgrade/downgrade; record lịch sử nullable vẫn đọc được.
- Transaction failure không đánh dấu occurrence đã persisted và cleanup snapshot đúng contract hiện tại.

### Frontend/component

- Video mới tạo session UUID; pause/review/resume không đổi UUID hoặc reset frame sequence.
- Active occurrence lặp không mở review lần hai.
- Occurrence mới của track/rule khác vẫn mở review.
- Event payload chứa đầy đủ occurrence IDs.
- Reconnect dùng lại session ID; stale result bị bỏ qua.
- Overlay hiển thị đúng track ID cho nhiều người.

### End-to-end

- Một người đứng liên tục trong zone khi máy chạy chỉ tạo một review/event.
- Người rời zone rồi tái nhập sau cooldown tạo event mới.
- Mất detection ngắn không tạo event mới.
- Hai người vi phạm độc lập tạo occurrence đúng người.
- Cùng người thiếu nhiều PPE và xâm nhập zone tạo một review tổng hợp, không mất rule detail.

## Commands

```bash
# Vision tracking tests
PYTHONPATH=. .venv/bin/pytest vision/tests -v -k "track or association"

# Backend lifecycle, transport và persistence
PYTHONPATH=. .venv/bin/pytest backend/tests -v -k "track or dedup or occurrence or session"

# Frontend transport/session tests
npm --prefix frontend run test -- --run

# Full repository gate
make check

# Integrated runtime
make run
```

`make check` phải được cập nhật để collect `vision/tests` trước khi US-08 được đánh dấu hoàn thành.

## Boundaries

### Always do

- Giữ tracking theo session và không biến `track_id` thành định danh con người.
- Giữ vision thuần observation; backend sở hữu occurrence/dedup/event idempotency.
- Giữ event creation sau HITL và database-enforced idempotency.
- Mở rộng REST/WebSocket theo hướng cộng thêm và giữ contract regression tests.
- Cleanup session registry theo TTL và giới hạn memory.
- Dùng monotonic time cho grace/cooldown runtime; dùng UTC timestamp cho persistence/audit.

### Ask first

- Thay đổi bốn default grace/exit/cooldown/TTL trong spec.
- Cho vi phạm liên tục tự mở event định kỳ dù chưa kết thúc.
- Persist toàn bộ per-frame tracking state vào database.
- Thay ByteTrack hoặc thêm tracking dependency/provider mới.
- Cho phép nhiều connection đồng thời ghi vào cùng monitoring session.
- Thay đổi event lifecycle ngoài idempotency tối thiểu của US-08.

### Never do

- Dùng nhận diện khuôn mặt hoặc đặc trưng sinh trắc học để duy trì track ID.
- Dedup chỉ ở frontend hoặc chỉ bằng một boolean latch toàn cục.
- Dùng bbox/index của frame làm track ID ổn định.
- Reset tracker khi machine state, zone hoặc PPE requirement được reconfigure trong cùng session.
- Tạo event database tự động cho mọi frame vi phạm.
- Cho vision đọc database, requirement hoặc quyết định event state.
- Giữ session registry không TTL/không giới hạn.

## Success criteria

1. Mọi person detection trong video session có `track_id` ổn định và không lẫn giữa nhiều người trong các fixture nghiệm thu.
2. Cùng `session + track + rule + occurrence` chỉ có một lần `is_new=true`, một review candidate và tối đa một persisted event.
3. Frame lặp, pause/review/resume, reconnect ngắn và lost track trong grace không tạo occurrence mới.
4. Vi phạm đã clear và tái diễn sau cooldown tạo occurrence mới; tái diễn trong cooldown không tạo mới.
5. Zone và từng PPE rule được dedup độc lập nhưng có thể gộp vào một review mà không mất chi tiết.
6. REST/WebSocket giữ các field hiện hành và trả semantics tracking/occurrence nhất quán ở session mode.
7. Database constraint bảo vệ duplicate event kể cả concurrent retry.
8. Tests vision, backend, frontend, migration và E2E nêu trên vượt qua; `make check` collect cả `vision/tests`.
9. `make setup` và `make run` vẫn là hai lệnh duy nhất đồng đội cần để chạy repository.

## Quyết định đã duyệt

1. Dùng lost-track `3` frame, exit-confirm `2` frame, cooldown `2s`, session TTL `300s` làm default MVP.
2. Khi cùng frame có nhiều người/occurrence mới, UI dùng một review tổng hợp theo snapshot.
3. False alarm khóa occurrence hiện tại đến khi clear để tránh review lặp.
4. Tracking/session state chỉ in-memory có TTL trong MVP; event idempotency được persist và bảo vệ bằng database constraint.
5. REST fallback hỗ trợ session mode để giữ contract parity; WebSocket vẫn là đường video chính.

## Kế hoạch triển khai

1. Chốt contract/session defaults và viết contract tests thất bại trước.
2. Thêm vision tracker facade với sequence tests, chưa nối event lifecycle.
3. Thêm backend monitoring-session registry và violation state machine thuần.
4. Nối tracking + occurrence vào WebSocket/REST response theo hướng cộng thêm.
5. Thêm event idempotency schema/migration/service và concurrency tests.
6. Cập nhật frontend session lifecycle, review payload và overlay track ID.
7. Chạy E2E sequence, browser verification, `make check`, cập nhật tài liệu và chuyển spec sang `done` khi toàn bộ gate đạt.
