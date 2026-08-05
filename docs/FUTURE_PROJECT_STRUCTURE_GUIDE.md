# Hướng Dẫn Đọc Cấu Trúc Dự Án Tương Lai

Tài liệu này giải thích ý nghĩa của cây thư mục đã chốt trong [`FUTURE_PROJECT_STRUCTURE.md`](FUTURE_PROJECT_STRUCTURE.md), giúp contributor và AI xác định đúng nơi đặt code mà không suy luận chỉ từ tên file/folder.

## 1. Vai trò của tài liệu

- `FUTURE_PROJECT_STRUCTURE.md` là **baseline cấu trúc đích bất biến** và là nguồn sự thật về boundary đã phê duyệt.
- File này là **hướng dẫn diễn giải**, không bổ sung, xóa hoặc thay đổi boundary trong baseline.
- `PROJECT_STRUCTURE.md` mô tả filesystem đang tồn tại; không được giả định mọi đường dẫn trong cấu trúc tương lai đã được tạo.
- Khi nội dung hướng dẫn này mâu thuẫn với baseline, baseline được ưu tiên và agent phải báo người dùng.

## 2. Cách hiểu cây cấu trúc

Mỗi dòng trong cây cấu trúc tương lai trả lời một trong bốn câu hỏi:

1. **Owner:** Module nào chịu trách nhiệm chính?
2. **Responsibility:** Code tại đây được phép làm gì?
3. **Boundary:** Code tại đây không được làm gì?
4. **Contract:** Module khác tương tác với nó bằng cách nào?

Cây cấu trúc **không có nghĩa** là:

- Phải tạo toàn bộ folder/file ngay lập tức.
- Mỗi story phải chạm tất cả các layer được liệt kê.
- Code cũ phải được di chuyển hàng loạt trước khi phát triển tiếp.
- Tên folder cho phép bỏ qua public contract hoặc ownership.

Agent chỉ tạo đường dẫn khi task hiện tại cần behavior thật tại đó. Không tạo placeholder rỗng.

## 3. Bản đồ thư mục cấp cao

| Đường dẫn | Sở hữu | Không sở hữu | Khi đặt code vào đây |
|---|---|---|---|
| `backend/` | API, nghiệp vụ, persistence, orchestration và adapter server-side | Thuật toán CV chi tiết, React UI, model weights | Behavior chạy phía server hoặc quản lý business state |
| `vision/` | Detection, tracking, association, geometry và privacy pixel processing | HTTP, database, user, event lifecycle, severity/routing | Logic biến frame/image thành observation hoặc ảnh đã redact |
| `frontend/` | UI, browser state, transport client và visualization | Business enforcement, database query, inference implementation | Behavior người dùng nhìn thấy hoặc tương tác trong trình duyệt |
| `contracts/` | Wire schema, version, generated artifacts và compatibility fixtures | Business implementation, runtime mutable state | Dữ liệu đi qua boundary giữa frontend/backend/vision |
| `models/` | Weights, registry, checksum, license và model cards | Loader/inference Python code | Artifact ML cần version và xác minh nguồn |
| `data/` | Demo fixtures, edge cases, ground truth và blurred runtime snapshots | Production code, raw snapshot lâu dài | Dữ liệu đầu vào/đối chiếu được phép sử dụng |
| `evaluation/` | Đánh giá offline precision, recall, false alarm và latency | Dashboard query, request-time inference | Đo chất lượng có thể chạy lại theo release |
| `tests/` | End-to-end test xuyên các phân hệ | Unit test nội bộ module | Một test cần chạy qua frontend–backend–vision |
| `infra/` | Container, cloud và observability configuration | Business logic | Cấu hình deploy/vận hành có thể version hóa |
| `docs/` | Tài liệu kiến trúc, hướng dẫn, runbook và evidence | Product requirement canonical | Giải thích cách hệ thống được thiết kế/vận hành |
| `specs/` | PRD, user stories, acceptance criteria và backlog | Implementation details thay đổi thường xuyên | Mô tả sản phẩm phải làm gì và thế nào là Done |

## 4. Cách đọc `backend/`

### `backend/app/api/`

Đây là vùng composition của transport:

- Gắn route, API version prefix, dependency và middleware dùng chung.
- Chuyển HTTP/WebSocket input vào module owner.
- Không query database, không gọi YOLO và không quyết định nghiệp vụ.

Business endpoint cụ thể vẫn thuộc module tương ứng qua `modules/<capability>/router.py`; `api/router.py` chỉ lắp chúng vào application.

### `backend/app/core/`

Chỉ chứa hạ tầng thực sự dùng toàn backend:

- Settings/environment.
- Database engine/session factory.
- Security primitives.
- Logging và technical error mapping.

Không đặt use case, event rule, dashboard metric hoặc code provider tại đây. `core/` không phải tên khác của `common/`.

### `backend/app/modules/`

Đây là nơi business capability sở hữu code và dữ liệu:

| Module | Câu hỏi module trả lời |
|---|---|
| `auth/` | Người dùng là ai và được phép làm gì? |
| `monitoring/` | Phiên phân tích video/ảnh được cấu hình và điều phối thế nào? |
| `rules/` | Observation nào thỏa rule nào, với severity/confidence policy nào? |
| `events/` | Event được tạo, dedup, review, audit và lưu snapshot theo vòng đời nào? |
| `organization/` | Zone, shift, timezone và người phụ trách được cấu hình thế nào? |
| `analytics/` | Metric/dashboard được định nghĩa và truy vấn thế nào? |
| `escalation/` | Critical event được route, retry và acknowledge thế nào? |
| `reporting/` | Báo cáo được lên lịch, tổng hợp, render và lưu lịch sử thế nào? |

Một task chạm nhiều module vẫn phải chọn đúng một module primary owner. Module khác chỉ hỗ trợ qua public service/contract.

### Ý nghĩa file chuẩn trong business module

| File | Được phép chứa | Không được chứa |
|---|---|---|
| `README.md` | Scope, owner, public API, data, dependency, test command, related stories | Progress/decision log riêng |
| `router.py` | Parse request, dependency injection, status/response mapping | SQL query hoặc business decision |
| `schemas.py` | Request/response DTO và validation hình dạng dữ liệu | ORM behavior hoặc use-case orchestration |
| `service.py` | Application use case và transaction orchestration | FastAPI request/response primitive |
| `domain.py` | Entity, value object, policy và state transition thuần | Provider SDK hoặc HTTP serialization |
| `repository.py` | Persistence/query của chính module | Policy quyết định severity/review |
| `models.py` | SQLAlchemy models do module sở hữu | API DTO hoặc logic gọi module khác |
| `errors.py` | Lỗi có nghĩa trong capability | Generic catch-all technical errors |

Không bắt buộc tạo đủ tám file. Chỉ tạo file khi capability có responsibility tương ứng.

### `backend/app/integrations/`

Chứa adapter tới implementation nằm ngoài business domain:

- `vision/`: map request/observation khi backend gọi vision facade.
- `llm/`: provider LLM, structured output và deterministic fallback.
- `notifications/`: email/chat provider SDK.
- `storage/`: local/object-storage implementation cho snapshot/report.

Adapter không được tự quyết định severity, event state hoặc permission. Module business đưa ra quyết định; adapter chỉ thực hiện contract.

### `backend/app/jobs/`

Chỉ chứa process/entrypoint chạy background job đã được module định nghĩa, ví dụ report schedule hoặc escalation retry. Business logic vẫn nằm trong `reporting` hoặc `escalation`.

### `backend/app/main.py`

Đây là composition root:

- Tạo FastAPI application.
- Wiring dependency/adapter.
- Đăng ký router và lifespan.

Không thêm endpoint implementation hoặc business logic trực tiếp vào `main.py`.

## 5. Cách đọc `vision/`

`vision/` biến ảnh/frame thành observation. Backend chỉ gọi `vision/api.py`; không import sâu implementation.

| Đường dẫn | Trách nhiệm duy nhất |
|---|---|
| `api.py` | Public facade ổn định cho caller |
| `types.py` | Observation types nội bộ và mapping contract |
| `pipeline.py` | Điều phối thứ tự các bước CV, không tự implement detector |
| `person/` | Person detection |
| `ppe/` | Helmet/glasses/gloves detection, threshold và class mapping |
| `tracking/` | Track identity/lifecycle |
| `association/` | Gắn PPE observation với person/track |
| `zones/` | Foot point, polygon và geometry observation |
| `privacy/` | Blur/redact pixel in-memory |

`vision/` không tạo safety event, không lưu database, không biết user/role và không gửi notification. Giá trị `inside_zone=true` là observation; quyết định cảnh báo khi máy chạy thuộc backend `rules/` và `events/`.

## 6. Cách đọc `frontend/`

### `frontend/src/app/`

Lắp router, provider và application shell. Không sở hữu business feature state chi tiết.

### `frontend/src/api/`

Sở hữu HTTP/WebSocket transport, auth header, URL resolution và generated contract types. Không render UI hoặc vẽ Canvas.

### `frontend/src/features/`

Mỗi feature sở hữu UI và browser state của một capability:

- `auth/`: login/session UI.
- `monitor/`: video/image, zone editing, sampling và Canvas.
- `rules/`: nhập, preview và confirm rule.
- `alerts/`: pending alert và HITL controls.
- `events/`: event history/detail.
- `organization/`: zone/shift/assignment configuration UI.
- `dashboard/`: metric filters/cards/charts.
- `escalations/`: delivery/acknowledgement state UI.
- `reports/`: schedule/history/download UI.

Feature không import file nội bộ của feature khác. Nếu cần phối hợp, dùng app composition hoặc public export đã ghi trong README feature.

### `frontend/src/shared/`

Chỉ dùng cho UI primitive, hook hoặc library thuần đã có ít nhất hai consumer thật. Không chứa event state, monitoring orchestration hoặc API logic đặc thù feature.

## 7. Cách đọc các vùng contract, artifact và evidence

### `contracts/`

- `schemas/`: wire schema có version.
- `generated/`: artifact sinh tự động; không sửa tay.
- `fixtures/`: payload mẫu dùng kiểm tra compatibility.

REST lấy Pydantic/FastAPI route làm nguồn sự thật. WebSocket và Backend–Vision dùng JSON Schema đã chỉ định trong baseline. Không viết lại cùng một contract thủ công ở nhiều nơi.

### `models/`

`weights/` chỉ chứa artifact. Logic load model thuộc `vision/`. Mỗi model cần registry entry, checksum, model card, license/source và class mapping.

### `data/`

- `demo/`: input mô phỏng hợp lệ.
- `edge-cases/`: input khó/lỗi được lựa chọn rõ ràng.
- `ground-truth/`: nhãn kỳ vọng để evaluation.
- `snapshots/`: runtime output đã blur và mặc định không commit.

Không lưu raw video liên tục hoặc snapshot chưa blur.

### `evaluation/` và `tests/`

- Evaluation trả lời “model/hệ thống tốt đến đâu?”.
- Unit/integration/contract tests trả lời “implementation có đúng contract/behavior không?”.
- Root `tests/e2e/` trả lời “core flow có chạy xuyên các phân hệ không?”.

Không đặt offline metric calculation vào `backend/app/modules/analytics/`; analytics chỉ phục vụ metric sản phẩm/dashboard.

### `infra/`

- `docker/`: image/container entrypoints.
- `cloud/`: IaC và environment config sau khi cloud target được chốt.
- `observability/`: dashboard, alert và logging configuration.

Secret và environment-specific value không được commit vào đây.

## 8. Ví dụ định tuyến task

| Task | Primary owner | Supporting boundary | Không đặt vào |
|---|---|---|---|
| Thêm PPE helmet/glasses/gloves | `vision/ppe/` | `contracts/` và backend `monitoring/` adapter | `backend/core/` |
| Làm mờ snapshot trước khi lưu | Backend `events/` sở hữu policy | `vision/privacy/` xử lý pixel; `integrations/storage/` lưu | `router.py` |
| Sinh rule từ mô tả | Backend `rules/` | `integrations/llm/`; frontend `features/rules/` | `vision/` |
| Chống event trùng | Backend `events/` | Track observation từ `vision/tracking/` | `analytics/` |
| Đăng nhập hai vai trò | Backend `auth/` | Frontend `features/auth/` | `organization/` |
| Escalate critical event | Backend `escalation/` | `events` public contract và notification adapter | `events/repository.py` |
| Dashboard theo ca/khu vực | Backend `analytics/` | `organization` public contract; frontend dashboard | `evaluation/` |
| Báo cáo định kỳ | Backend `reporting/` | jobs + notification/storage adapter | `analytics/router.py` |
| Phân tích một ảnh | Backend `monitoring/` | Vision facade, rules và events public services | Tạo pipeline CV thứ hai |

## 9. Các hiểu nhầm phải tránh

| Hiểu nhầm | Cách hiểu đúng |
|---|---|
| Có folder trong cây nên phải tạo ngay | Chỉ tạo khi task có behavior thật |
| `vision/rules` nên quyết định cảnh báo | Vision trả observation; backend `rules` quyết định |
| Module cần dữ liệu module khác nên import repository | Gọi public service/port/contract |
| `core/` hoặc `shared/` dùng được cho mọi code | Chỉ chứa abstraction dùng chung có responsibility cụ thể |
| Generated types có thể sửa nhanh | Phải sửa nguồn contract rồi regenerate |
| Refactor story là dịp chuyển toàn repo | Chỉ migration phần task chạm tới |
| Cây tương lai mô tả filesystem hiện tại | Xem `PROJECT_STRUCTURE.md` để biết filesystem thật |
| Hướng dẫn này có thể thay baseline | Chỉ baseline và quyết định kiến trúc mới xác định boundary |

## 10. Checklist trước khi agent sửa code

Agent phải trả lời được các câu sau:

1. Task/story nào đang được thực hiện?
2. Primary owning module là module nào?
3. README nào phải đọc trước?
4. Input/output contract nào bị ảnh hưởng?
5. Module hỗ trợ nào cần gọi qua public boundary?
6. Test thuộc unit, integration, contract, evaluation hay E2E?
7. Có tạo folder/file mới không, và `PROJECT_STRUCTURE.md` phải cập nhật gì?
8. Có đang vô tình mở rộng scope hoặc refactor ngoài task không?

Nếu không xác định được một primary owner, hoặc cần đường dẫn không có trong baseline, agent phải dừng thay đổi cấu trúc và xin quyết định từ người dùng. Agent không được sửa `FUTURE_PROJECT_STRUCTURE.md`.
