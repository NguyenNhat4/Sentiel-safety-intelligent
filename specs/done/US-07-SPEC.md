# Spec: US-07 — Phát hiện và cấu hình cảnh báo thiếu PPE

## Trạng thái đặc tả

- Giai đoạn: **DONE — cấu hình, observation và UI PPE hoàn tất; production model gate được ghi nhận riêng**
- Primary owner: `backend services`
- Phạm vi phát hành: đóng MVP
- Người dùng chính: cán bộ an toàn

## Objective

Hệ thống phát hiện theo từng người trạng thái mũ, kính và găng bảo hộ, đồng thời cho phép cán bộ an toàn cấu hình loại PPE nào bắt buộc đối với cặp camera–khu vực đang giám sát. Model luôn thực hiện detection; cấu hình chỉ quyết định detection thiếu PPE nào được chuyển thành cảnh báo.

Thành công nghĩa là người dùng cấu hình một lần, bấm **Lưu cấu hình**, và mọi phiên truy cập sau đó dùng cùng cấu hình đã lưu từ backend. Trước lần lưu đầu tiên, cả ba yêu cầu đều OFF.

## Phạm vi chức năng

### Detection theo từng người

- Model PPE được nạp từ cấu hình và thay thế heuristic màu/áo phản quang trong vai trò kết quả PPE chính.
- Mỗi person/track có kết quả riêng cho `helmet`, `safety_glasses` và `gloves`.
- Mỗi hạng mục có trạng thái `present`, `missing` hoặc `unknown` và confidence tương ứng khi model cung cấp được quyết định.
- `missing` chỉ được phát ra khi class mapping của model biểu diễn được bằng chứng thiếu PPE đạt threshold; không tự suy diễn `missing` chỉ từ việc không thấy PPE.
- `unknown` không tạo cảnh báo. Với găng, thiếu ít nhất một bên được xem là `missing` nếu model/dataset phân biệt được trạng thái đó.
- Nhiều người trong cùng frame không được dùng chung hoặc ghi đè kết quả PPE của nhau.

### Cấu hình yêu cầu PPE

- Giao diện có ba công tắc độc lập: **Yêu cầu mũ**, **Yêu cầu kính**, **Yêu cầu găng**.
- Khi chưa có bản ghi cấu hình, cả ba công tắc hiển thị OFF.
- Thay đổi trên giao diện là bản nháp và chưa ảnh hưởng luật cảnh báo.
- Chỉ khi bấm **Lưu cấu hình** và backend phản hồi thành công, cấu hình mới có hiệu lực.
- Cấu hình được lưu bền vững theo `camera_id` và `zone_id`, là nguồn dùng chung cho mọi người dùng, trình duyệt và thiết bị.
- MVP chỉ vận hành một cặp camera–khu vực cố định nhưng contract không dùng singleton ẩn; hai định danh vẫn xuất hiện rõ trong API và persistence.

### Luật cảnh báo

Với mỗi person/track và mỗi loại PPE:

```text
missing_required_ppe = requirement_is_on
                       AND detection_status == "missing"
                       AND detection_confidence >= configured_threshold
```

- OFF không tắt model và không xóa observation; nó chỉ ngăn loại PPE đó tạo cảnh báo.
- ON + `present` không tạo cảnh báo.
- ON + `unknown` không tạo cảnh báo thiếu PPE.
- ON + `missing` đạt threshold tạo cảnh báo và đưa loại PPE vào `missing_required_ppe`.
- Một người thiếu nhiều loại đang ON nhận một quyết định tổng hợp chứa đầy đủ các loại thiếu, không làm mất chi tiết từng loại.

## Trạng thái giao diện

| Trạng thái | Hành vi |
|---|---|
| Loading | Vô hiệu hóa công tắc và nút lưu trong khi tải cấu hình từ backend. |
| Loaded | Hiển thị đúng cấu hình backend; nút lưu chỉ khả dụng khi có thay đổi. |
| Dirty | Cho phép chỉnh nhiều công tắc; inference vẫn dùng cấu hình đã lưu gần nhất. |
| Saving | Vô hiệu hóa thao tác lặp và hiển thị đang lưu. |
| Saved | Đồng bộ bản nháp với response backend và hiển thị **Đã lưu cấu hình**. |
| Load error | Hiển thị lỗi, không giả vờ rằng giá trị mặc định đã được lưu; cho phép thử lại. |
| Save error | Giữ bản nháp để người dùng thử lại; backend và inference tiếp tục dùng cấu hình đã lưu trước đó. |

Rời trang khi đang Dirty không tự động lưu. Khi quay lại hoặc tải lại trang, giao diện lấy bản đã lưu từ backend.

## REST contract

### Đọc cấu hình

```http
GET /api/v1/ppe-requirements/{camera_id}/{zone_id}
```

Response `200 OK` khi chưa từng lưu:

```json
{
  "camera_id": "cam_01",
  "zone_id": "zone_01",
  "helmet_required": false,
  "safety_glasses_required": false,
  "gloves_required": false,
  "is_configured": false,
  "updated_at": null
}
```

Backend trả resource mặc định thay vì `404`, giúp mọi client dùng cùng một hành vi khởi tạo.

### Lưu toàn bộ cấu hình

```http
PUT /api/v1/ppe-requirements/{camera_id}/{zone_id}
Content-Type: application/json
```

```json
{
  "helmet_required": true,
  "safety_glasses_required": false,
  "gloves_required": true
}
```

Response `200 OK` trả toàn bộ resource đã lưu với `is_configured=true` và `updated_at`. `PUT` là idempotent: gửi lại cùng payload không tạo thêm resource hoặc thay đổi ý nghĩa cấu hình.

### Validation và lỗi

- `camera_id` và `zone_id` phải là chuỗi không rỗng, tối đa 50 ký tự để tương thích định danh event hiện tại.
- Ba trường request là boolean bắt buộc; không chấp nhận payload thiếu trường hoặc giá trị ép kiểu mơ hồ.
- `422` cho input không hợp lệ, theo error body `detail` hiện hành của FastAPI.
- `503` khi persistence thất bại; response không được chứa chi tiết nội bộ.
- Save là atomic: hoặc cả ba trạng thái được lưu, hoặc cấu hình cũ được giữ nguyên.

Không bổ sung endpoint xóa trong US-07. Người dùng có thể đặt cả ba trường thành `false` để vô hiệu hóa mọi cảnh báo PPE.

## Inference contract

Thay đổi phải mang tính cộng thêm và không xóa hoặc đổi kiểu các field REST/WebSocket đang tồn tại.

Mỗi person/track bổ sung observation PPE có cấu trúc ổn định:

```json
{
  "track_id": 17,
  "ppe": {
    "helmet": {"status": "present", "confidence": 0.94},
    "safety_glasses": {"status": "unknown", "confidence": null},
    "gloves": {"status": "missing", "confidence": 0.88}
  },
  "missing_required_ppe": ["gloves"]
}
```

- `track_id` tuân theo US-08; trước khi tracking hoàn chỉnh, association vẫn phải đúng trong phạm vi frame.
- `missing_required_ppe` là kết quả rule backend, không phải output trực tiếp của vision.
- REST frame inference và WebSocket inference trả cùng semantics PPE cốt lõi.
- `rule` echo lại `camera_id`, `zone_id`, `ppe_requirements` và `ppe_alert`, để client biết chính xác ba requirement đã được dùng cho frame.
- Field baseline `safety_shirt` được giữ trong wire contract tương thích, nhưng UI không còn dùng để đánh giá hoặc hiển thị PPE.

Ví dụ rule trả về khi chỉ yêu cầu mũ:

```json
{
  "camera_id": "uploaded_video",
  "zone_id": "zone_01",
  "ppe_requirements": {
    "helmet_required": true,
    "safety_glasses_required": false,
    "gloves_required": false
  },
  "ppe_alert": false
}
```

### Hiển thị PPE trên box người

- Chỉ loại PPE đang được bật requirement mới xuất hiện trên box người.
- `present` hiển thị badge xanh, ví dụ **✓ MŨ**.
- `missing` hiển thị badge đỏ, ví dụ **✕ MŨ**.
- `unknown` hiển thị badge trung tính, ví dụ **? MŨ**; trạng thái này không bị trình bày như thiếu PPE.
- Overlay dùng nhãn `PERSON · <confidence>` và không còn hiển thị nhãn legacy `SHIRT`.

## Tech stack

- Frontend: React 19, TypeScript 5.7, Vite 6, Vitest và Testing Library.
- Backend: FastAPI, Pydantic, SQLAlchemy, Alembic và pytest.
- Vision: Ultralytics YOLO và OpenCV qua facade độc lập với HTTP/database.
- Persistence: SQLite cho local/test; PostgreSQL là production target.

## Commands

```bash
# Chạy ứng dụng tích hợp
make run

# Backend tests tập trung cho US-07
PYTHONPATH=. .venv/bin/pytest backend/tests -v -k "ppe or requirement"

# Frontend tests tập trung cho US-07
npm --prefix frontend run test -- --run ppe

# Toàn bộ quality gate
make check
```

## Project structure và ownership

```text
backend/app/services/            # Cấu hình, transaction và quyết định PPE
backend/app/models/              # ORM PPE requirement
backend/app/schemas/             # Request/response và inference DTO
backend/app/api/v1/              # GET/PUT transport
backend/app/integrations/        # Adapter gọi vision facade và mapping provider
backend/app/api/                 # REST/WS transport, validation và response mapping
backend/migrations/              # Lịch sử schema cấu hình
backend/tests/                   # Unit, persistence, REST và contract tests
frontend/src/features/rules/     # Công tắc, draft state và trạng thái lưu
frontend/src/api/                # REST client, không chứa UI state
frontend/src/types/              # Wire types đồng bộ Pydantic
vision/                          # Observation PPE; không đọc DB hoặc quyết định alert
vision/tests/                    # Class mapping, threshold và association tests
```

Không tạo `backend/app/modules` cho US-07. Không thêm production code vào root `src/` và không đặt rule trong vision hoặc frontend.

## Code style

Contract dùng `snake_case` để tương thích API hiện hành; domain đặt tên theo ý nghĩa an toàn thay vì tên widget:

```python
class PpeRequirementUpdate(BaseModel):
    helmet_required: bool
    safety_glasses_required: bool
    gloves_required: bool


def should_alert(*, required: bool, status: PpeStatus, confidence: float | None, threshold: float) -> bool:
    return required and status == PpeStatus.MISSING and confidence is not None and confidence >= threshold
```

- Python được format/lint bằng Ruff; type và schema rõ ràng tại boundary.
- TypeScript dùng typed props/state; transport không render UI và feature không tự gọi database.
- Không dùng tên chung như `utils`, `helpers`, `common` để chứa rule PPE.

## Testing strategy

### Vision/unit

- Mapping class của weights sang mũ, kính, găng và trạng thái present/missing/unknown.
- Confidence đúng bằng, thấp hơn và cao hơn threshold.
- Association PPE với một người, nhiều người và không có person.
- Thiếu một loại, nhiều loại, không có detection và găng thiếu một bên nếu dataset hỗ trợ.

### Backend/domain và persistence

- Truth table ON/OFF × present/missing/unknown × threshold.
- Cả ba mặc định OFF khi chưa có record.
- Upsert theo đúng cặp camera–khu vực và không tạo record trùng.
- Persistence tồn tại qua session/database restart trong integration test.
- Save atomic và giữ cấu hình cũ khi transaction thất bại.

### REST/contract

- GET mặc định, GET đã cấu hình, PUT thành công, PUT idempotent và validation `422`.
- Persistence failure trả `503` mà không rò rỉ chi tiết nội bộ.
- REST và WebSocket giữ field cũ, đồng thời trả semantics PPE mới nhất quán.

### Frontend/component

- Loading, default OFF, hydrated values, Dirty, Saving, Saved, load error và save error.
- Thay đổi công tắc chưa gọi API và chưa đổi cấu hình active.
- Một lần bấm lưu gửi đủ ba boolean và định danh camera–khu vực hiện hành.
- Reload lấy lại cấu hình backend; không phụ thuộc `localStorage`.
- Kiểm tra label, keyboard focus, trạng thái disabled và thông báo lưu bằng accessible queries.

### E2E/benchmark

- Video ground truth có một và nhiều người cho từng loại PPE.
- Cùng một detection thiếu PPE: OFF không cảnh báo, ON có cảnh báo.
- Báo cáo precision, recall, false alarm và latency theo từng nhóm PPE trên bộ demo đã chốt.

## Boundaries

### Always do

- Giữ database là nguồn cấu hình chính thức và validate ở REST boundary.
- Giữ vision thuần observation; backend service quyết định cảnh báo.
- Lưu toàn bộ ba boolean trong một transaction.
- Bảo toàn REST/WebSocket fields hiện có bằng thay đổi cộng thêm.
- Chạy test tập trung và `make check` trước khi đánh dấu hoàn thành.

### Ask first

- Thay đổi endpoint hoặc field đã mô tả trong spec này.
- Thay đổi schema ngoài bảng/configuration PPE.
- Thêm dependency hoặc thay model/weights sau khi nguồn và giấy phép đã được chốt.
- Mở rộng từ một cặp cố định sang quản trị nhiều camera/khu vực.
- Cho `unknown` tạo cảnh báo hoặc review bắt buộc.

### Never do

- Lưu cấu hình chỉ bằng `localStorage`.
- Tắt model detection khi công tắc OFF.
- Suy diễn `missing` từ absence nếu model/class mapping không chứng minh trạng thái thiếu.
- Cho frontend hoặc vision tự quyết định luật cảnh báo chính thức.
- Persist ảnh chưa được làm mờ hoặc đưa secret/model license không hợp lệ vào repository.

## Success criteria

1. Ba công tắc mặc định OFF và chỉ có hiệu lực sau response lưu thành công.
2. Cấu hình được dùng chung và khôi phục từ backend theo cặp camera–khu vực sau reload/restart.
3. Mỗi người có kết quả present/missing/unknown và confidence cho mũ, kính, găng mà không lẫn người.
4. Chỉ tổ hợp ON + missing đạt threshold tạo cảnh báo cho loại PPE tương ứng.
5. REST và WebSocket giữ tương thích với consumer hiện tại và trả semantics PPE nhất quán.
6. Mỗi frame trả lại `rule.ppe_requirements` đang active; badge trên box chỉ phản ánh PPE được require.
7. UI không quyết định hoặc hiển thị PPE dựa trên heuristic `safety_shirt`.
8. Các test vision, domain, persistence, API, frontend và integration nêu trên đều vượt qua.

## Open questions và implementation gates

Các điểm sau là production gate sau khi MVP implementation đã hoàn tất:

1. Weights/version/checksum, giấy phép sử dụng và class names thực tế của model PPE.
2. Class mapping chính xác để phân biệt `present`, `missing` và `unknown` cho từng loại PPE.
3. Confidence threshold mặc định và threshold có dùng chung hay riêng theo từng loại PPE.
4. Giá trị `camera_id` và `zone_id` cố định của demo runtime.
5. Dataset ground truth và ngưỡng benchmark chấp nhận cho precision, recall, false alarm và latency.

## Implementation plan

Kế hoạch tuân theo dependency `domain rule → persistence → REST contract → frontend transport → UI → model adapter → inference integration`. Không tạo top-level `tasks/` vì cấu trúc đích của repository cấm top-level directory mới khi chưa có quyết định kiến trúc; checklist được giữ ngay trong spec sở hữu US-07.

### Task 1 — Rule semantics và service boundary

**Description:** Tạo service PPE tối thiểu và hàm quyết định cảnh báo PPE thuần, không phụ thuộc vision provider.

**Acceptance:**

- [ ] Truth table ON/OFF × present/missing/unknown × threshold đúng với spec.
- [ ] Capability có README nêu owner, public entrypoint, dependency và non-goals.
- [ ] Không đưa rule vào frontend, vision hoặc legacy `src/`.

**Verify:** `PYTHONPATH=. .venv/bin/pytest backend/tests/test_ppe_rules.py -v`

**Likely files:** `backend/app/services/ppe_requirement_service.py`, `backend/tests/test_ppe_requirements.py`.

**Dependencies:** None. **Scope:** Medium, 4 files.

### Task 2 — Persistent camera–zone configuration

**Description:** Thêm model, repository/service và Alembic migration để lưu atomic ba boolean theo unique camera–zone pair.

**Acceptance:**

- [ ] Chưa có record trả defaults OFF; save tạo hoặc cập nhật đúng một record.
- [ ] Config dùng chung qua database session và rollback giữ config cũ khi save lỗi.
- [ ] SQLite test và PostgreSQL target dùng cùng SQLAlchemy contract.

**Verify:** `PYTHONPATH=. .venv/bin/pytest backend/tests/test_ppe_requirements.py -v -k "service or repository"`

**Likely files:** `backend/app/models/ppe_requirement.py`, `backend/app/services/ppe_requirement_service.py`, `backend/migrations/versions/*_add_ppe_requirements.py`, `backend/tests/test_ppe_requirements.py`.

**Dependencies:** Task 1. **Scope:** Medium, 5 files.

### Checkpoint A

- [ ] Task 1–2 focused tests pass.
- [ ] Migration upgrade/downgrade is reviewable.
- [ ] No current event or inference contract changes.

### Task 3 — GET/PUT REST contract

**Description:** Expose typed read and idempotent full-save endpoints, preserving current FastAPI error semantics.

**Acceptance:**

- [ ] GET returns default resource with `is_configured=false` instead of `404`.
- [ ] PUT validates all three booleans and returns saved resource.
- [ ] Invalid input returns `422`; persistence failure returns safe `503`.

**Verify:** `PYTHONPATH=. .venv/bin/pytest backend/tests/test_ppe_requirements.py -v -k "api"`

**Likely files:** `backend/app/schemas/ppe_requirement.py`, `backend/app/api/v1/ppe_requirements.py`, `backend/app/api/router.py`, `backend/tests/test_ppe_requirements.py`.

**Dependencies:** Task 2. **Scope:** Medium, 4 files.

### Task 4 — Typed frontend transport

**Description:** Add wire types and REST client for loading/saving the shared configuration without `localStorage`.

**Acceptance:**

- [ ] Load/save payloads match Pydantic snake_case contract.
- [ ] Client reports backend `detail` errors consistently.
- [ ] Tests cover GET, PUT body and failed response.

**Verify:** `npm --prefix frontend run test -- --run src/api/ppe-requirements.test.ts`

**Likely files:** `frontend/src/types/index.ts`, `frontend/src/api/ppe-requirements.ts`, `frontend/src/api/ppe-requirements.test.ts`.

**Dependencies:** Task 3. **Scope:** Small, 3 files.

### Task 5 — Accessible PPE requirement controls

**Description:** Add the three switches and explicit Save flow to the current monitor using the established Sentinel visual language.

**Acceptance:**

- [ ] Loading, Loaded, Dirty, Saving, Saved, load-error và save-error states match spec.
- [ ] Switches have accessible labels, keyboard operation and non-color status text.
- [ ] Reload reads backend values; changes are not effective or persisted until Save succeeds.

**Verify:** `npm --prefix frontend run test -- --run src/features/monitor/PpeRequirementsPanel.test.tsx && npm --prefix frontend run type-check && npm --prefix frontend run build`

**Likely files:** `frontend/src/features/monitor/PpeRequirementsPanel.tsx`, `PpeRequirementsPanel.test.tsx`, `MonitorPage.tsx`, `frontend/src/styles/monitor.css`.

**Dependencies:** Task 4. **Scope:** Medium, 4 files.

### Checkpoint B

- [ ] Backend and frontend focused suites pass.
- [ ] Browser runtime shows correct GET/PUT network flow and clean console.
- [ ] UI works at 320px, 768px, 1024px and 1440px with accessible names/focus order.

### Task 6 — PPE model adapter and person association

**Description:** Load licensed/configured PPE weights, map provider classes into stable observations and associate results per person/track.

**Acceptance:**

- [ ] Helmet, safety glasses and gloves map to present/missing/unknown with confidence.
- [ ] One/many-person ground-truth cases associate correctly.
- [ ] Model/device/threshold are configurable and provider details do not leak past the vision facade.

**Verify:** focused `vision/tests/` class-mapping, threshold and association tests plus demo benchmark.

**Likely files:** determined after weights/classes are supplied; all new vision folders require README.

**Dependencies:** Approved weights/version/checksum, license, class mapping and ground-truth dataset. **Status:** Blocked by missing model artifacts and metadata in the workspace.

### Task 7 — Inference and alert integration

**Description:** Add PPE observations and backend rule results to REST/WebSocket responses without breaking existing fields.

**Acceptance:**

- [ ] REST/WS return identical PPE semantics per person/track.
- [ ] Only configured ON + missing above threshold contributes to `missing_required_ppe` and review.
- [ ] Existing zone-intrusion flow and baseline response fields remain compatible.

**Verify:** backend REST/WS contract tests, frontend transport tests, end-to-end videos and `make check`.

**Dependencies:** Tasks 1–6. **Status:** Blocked until Task 6 is complete.

### Final checkpoint

- [ ] `make check` passes or every environment-specific failure is evidenced and documented.
- [ ] Real browser verification passes with clean console/network and accessible controls.
- [ ] US-07 acceptance criteria, benchmark and model-license gates are satisfied.
- [ ] Root progress and structure documents reflect the final filesystem and status.

## Plan risks

| Risk | Impact | Mitigation |
|---|---|---|
| PPE weights are absent from `models/` | Tasks 6–7 cannot be completed honestly | Complete Tasks 1–5; request licensed artifact, mapping and ground truth before model integration. |
| Current Python 3.14 TestClient stalls | Full backend verification may hang | Run focused unit/service checks first; use bounded live API smoke tests and document the known environment issue. |
| Adding fields breaks frontend assumptions | Existing monitor can regress | Add response fields only; keep current fields and add contract regression tests. |
| Unsaved UI state is mistaken for active policy | Alerts use unexpected config | Keep draft and persisted state separate; show Dirty/Saved/error states explicitly. |
