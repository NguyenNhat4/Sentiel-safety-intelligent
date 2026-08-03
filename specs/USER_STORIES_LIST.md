# User Story Backlog & Kế hoạch giao MVP 5 tuần

Tài liệu này chuyển phạm vi prototype trong [`PRD.md`](PRD.md) và bối cảnh tại
[`project-problem-statement.md`](../docs/project-problem-statement.md) thành backlog để giao một MVP hoàn chỉnh trong 5 tuần.
Trạng thái hiện tại được đối chiếu với [`PROGRESS.md`](../PROGRESS.md) tại ngày 2026-08-03.

## 1. Ranh giới MVP dùng để lập kế hoạch

`PRD.md` là nguồn quyết định phạm vi cho kế hoạch 5 tuần này. MVP gồm:

- Một cán bộ an toàn sử dụng một video mô phỏng, một vùng nguy hiểm bốn điểm và một trạng thái máy ON/OFF.
- Phát hiện người, theo dõi người, phát hiện một loại PPE là áo phản quang và đánh giá xâm nhập vùng.
- Rule do cán bộ mô tả, cảnh báo gần realtime, người thật review, snapshot đã làm mờ và nhật ký sự kiện.
- Dashboard cơ bản cùng số liệu precision, recall, false-alarm rate và latency.
- Một vi phạm liên tục chỉ tạo một event; hệ thống không tự động dừng máy.

Các yêu cầu rộng hơn trong problem statement như camera nhà máy thật, nhiều camera/vùng, PLC, hai vai trò đăng nhập,
dashboard theo khu vực/ca và báo cáo định kỳ được giữ ở backlog sau MVP tại cuối tài liệu. Chúng không phải điều kiện giao MVP 5 tuần nếu PRD chưa được thay đổi.

## 2. Quy ước

- **Hoàn thành:** Luồng chính đã có bằng chứng triển khai trong `PROGRESS.md`.
- **Hoàn thành một phần:** Đã có baseline nhưng còn thiếu acceptance criteria của PRD.
- **Chưa làm:** Chưa có bằng chứng hoàn thành hoặc đang là known issue/next step.
- **P0:** Bắt buộc để nghiệm thu MVP; **P1:** cần cho chất lượng vận hành; **P2:** sau MVP.
- Mỗi user story chỉ được chuyển sang **Done** khi đạt toàn bộ acceptance criteria, có test phù hợp, tài liệu liên quan được cập nhật và không làm hỏng contract hiện có.

## 3. User story đã hoàn thành — cần regression trong đợt release

### US-01 — Tải và phát video mô phỏng

> Với vai trò cán bộ an toàn, tôi muốn tải và phát một video mô phỏng, để giám sát tình huống an toàn mà không cần camera nhà máy thật.

- Trạng thái: **Hoàn thành**
- Kết quả hiện có: Tải video cục bộ, preview, Play/Stop và lấy mẫu frame khi video đang phát.
- Regression bắt buộc: Kiểm tra video hợp lệ/không hợp lệ, Play/Stop và kết thúc video.

### US-02 — Cấu hình vùng nguy hiểm bằng bốn điểm

> Với vai trò cán bộ an toàn, tôi muốn chấm bốn điểm trên video, để xác định vùng cấm cần giám sát.

- Trạng thái: **Hoàn thành**
- Kết quả hiện có: Polygon theo tọa độ chuẩn hóa; hỗ trợ kéo, xóa, đặt lại và giữ đúng vị trí khi đổi kích thước.
- Regression bắt buộc: Không chạy giám sát đầy đủ khi chưa đủ bốn điểm; kiểm tra điểm nằm ở biên polygon.

### US-03 — Phát hiện người gần realtime

> Với vai trò cán bộ an toàn, tôi muốn hệ thống phát hiện người trong video gần realtime, để quan sát vị trí của họ so với vùng nguy hiểm.

- Trạng thái: **Hoàn thành**
- Kết quả hiện có: YOLO person detection, WebSocket 2 FPS, bounding box, foot point và chỉ một frame in flight.
- Regression bắt buộc: Kiểm tra không có người, một người, nhiều người và WebSocket reconnect/error.

### US-04 — Kết hợp vùng nguy hiểm với trạng thái máy

> Với vai trò cán bộ an toàn, tôi muốn cảnh báo xâm nhập chỉ kích hoạt khi máy đang chạy, để giảm cảnh báo sai khi khu vực ở trạng thái an toàn.

- Trạng thái: **Hoàn thành**
- Kết quả hiện có: Vẫn vẽ người khi máy dừng; chỉ mở review khi foot point vào vùng và máy đang chạy.
- Regression bắt buộc: Kiểm tra ON/OFF, vào/ra vùng và thay đổi trạng thái máy trong lúc video phát.

### US-05 — Nhận và review cảnh báo gần realtime

> Với vai trò cán bộ an toàn, tôi muốn nhận cảnh báo ngay khi phát hiện tình huống nguy hiểm, để đánh giá và phản ứng kịp thời.

- Trạng thái: **Hoàn thành** cho baseline xâm nhập vùng
- Kết quả hiện có: Kết quả qua WebSocket, video tạm dừng khi cần review và monitor tiếp tục hoạt động sau review.
- Regression bắt buộc: Critical alert phải xuất hiện trong ngân sách latency được chốt ở US-13.

### US-06 — Lưu và xem nhật ký vi phạm

> Với vai trò cán bộ an toàn, tôi muốn lưu vi phạm đã xác nhận và xem lại trong nhật ký, để có bằng chứng phục vụ theo dõi an toàn.

- Trạng thái: **Hoàn thành** cho baseline
- Kết quả hiện có: REST event persistence, snapshot, SQLite cục bộ và màn hình nhật ký.
- Regression bắt buộc: Event và snapshot khớp nhau; lỗi transaction không để lại file rác; false alarm không hiện như vi phạm chính thức.

## 4. User story phải hoàn thiện trong 5 tuần

### US-07 — Phát hiện áo phản quang bằng model PPE

> Với vai trò cán bộ an toàn, tôi muốn hệ thống nhận biết người có mặc áo phản quang hay không, để phát hiện vi phạm PPE đáng tin cậy.

- Ưu tiên / trạng thái: **P0 / Hoàn thành một phần**
- Phụ thuộc: US-03
- Acceptance criteria:
  - Model PPE đã huấn luyện được nạp từ cấu hình; heuristic màu không còn là kết quả chính.
  - Kết quả có/không có áo và confidence được trả về mà không phá vỡ inference contract.
  - Confidence threshold có thể cấu hình; trường hợp mơ hồ được chuyển sang review theo US-15.
  - Có test mapping class, threshold, không phát hiện PPE và nhiều người.
- Task:
  1. Chốt weights, class mapping, giấy phép model và bộ video/ảnh demo có ground truth.
  2. Tạo adapter PPE model, cấu hình weights/device/threshold và cơ chế fail-fast khi thiếu model.
  3. Tích hợp kết quả PPE theo từng person/track vào REST và WebSocket inference.
  4. Bổ sung unit, integration và benchmark trên bộ demo.

### US-08 — Theo dõi người và chống tạo event trùng

> Với vai trò cán bộ an toàn, tôi muốn một vi phạm liên tục chỉ tạo một event, để nhật ký không bị lặp và cảnh báo không gây nhiễu.

- Ưu tiên / trạng thái: **P0 / Hoàn thành một phần, cần xác minh**
- Phụ thuộc: US-03, US-07
- Acceptance criteria:
  - Mỗi detection có `track_id` ổn định trong một phiên video.
  - Cùng người, cùng rule và cùng lần vi phạm chỉ có một event active.
  - Event mới chỉ được phép tạo sau khi người đã rời trạng thái vi phạm và tái vi phạm, hoặc sau cooldown đã định nghĩa.
  - Nhiều người vi phạm đồng thời được tách đúng; có test frame lặp, mất track ngắn, tái xâm nhập và nhiều người.
- Task:
  1. Hoàn thiện ByteTrack/session tracking và mapping detection-to-track.
  2. Định nghĩa dedup key, thời điểm bắt đầu/kết thúc vi phạm và cooldown.
  3. Lưu trạng thái violation theo track ở backend thay vì chỉ dựa vào pending state frontend.
  4. Thêm test chuỗi frame và kiểm tra database không sinh event trùng.

### US-09 — Vòng đời review của cảnh báo

> Với vai trò cán bộ an toàn, tôi muốn acknowledge, xác nhận vi phạm hoặc đánh dấu cảnh báo sai, để hệ thống ghi đúng quyết định của con người.

- Ưu tiên / trạng thái: **P0 / Hoàn thành một phần**
- Phụ thuộc: US-06, US-08
- Acceptance criteria:
  - State machine và ý nghĩa `pending`, `acknowledged`, `confirmed`, `false_alarm` được tài liệu hóa.
  - Acknowledge ghi nhận đã tiếp nhận; confirm ghi nhận vi phạm thực; false alarm vẫn được lưu để tính metric nhưng không xuất hiện như vi phạm chính thức.
  - API từ chối transition không hợp lệ và lưu timestamp cho từng quyết định.
  - UI hiển thị hành động/trạng thái nhất quán; refresh trang không làm mất event đang chờ xử lý.
- Task:
  1. Chốt event state machine và migration dữ liệu/schema.
  2. Bổ sung API transition, validation, audit timestamp và idempotency.
  3. Cập nhật review UI, event history filter và error/loading state.
  4. Viết test API, component và end-to-end cho mọi transition.

### US-10 — Dashboard thống kê cơ bản

> Với vai trò cán bộ an toàn, tôi muốn xem thống kê sự kiện của phiên demo, để đánh giá mức độ tuân thủ và chất lượng cảnh báo.

- Ưu tiên / trạng thái: **P0 / Hoàn thành một phần**
- Phụ thuộc: US-09
- Acceptance criteria:
  - Hiển thị tổng cảnh báo, vi phạm đã xác nhận, false alarm, PPE violation và zone violation.
  - Dữ liệu lấy từ statistics API và có bộ lọc thời gian phù hợp với một phiên demo.
  - Có loading, empty, error state và định dạng thời gian theo timezone cấu hình.
  - Số liệu dashboard khớp dữ liệu event fixture trong integration test.
- Task:
  1. Hoàn thiện query/response contract của statistics API.
  2. Xây dashboard cards/charts tối thiểu và bộ lọc thời gian.
  3. Thêm test service, API, component và empty/error state.

### US-11 — Sinh và áp dụng rule từ mô tả

> Với vai trò cán bộ an toàn, tôi muốn mô tả quy tắc và mức độ vi phạm bằng ngôn ngữ tự nhiên, để hệ thống biết khi nào cảnh báo hoặc bỏ qua.

- Ưu tiên / trạng thái: **P0 / Hoàn thành một phần**
- Phụ thuộc: US-04, US-07, US-14
- Acceptance criteria:
  - Người dùng nhập được mô tả rule; hệ thống trả về cấu trúc rule có loại vi phạm, điều kiện máy/vùng/PPE và severity.
  - Rule được validate, preview và yêu cầu người dùng xác nhận trước khi áp dụng.
  - Inference chỉ thực thi cấu trúc rule đã validate, không thực thi trực tiếp nội dung LLM tự do.
  - Có fallback deterministic khi không có API key và có lý do giải thích cho quyết định cảnh báo/bỏ qua.
- Task:
  1. Chốt JSON schema và danh sách điều kiện/severity được phép trong MVP.
  2. Hoàn thiện Safety Agent structured output, validation và fallback.
  3. Xây UI nhập/preview/confirm rule và lưu rule hiện hành cho phiên demo.
  4. Nối rule engine vào inference, cảnh báo và test các rule hợp lệ/không hợp lệ.

### US-12 — Làm mờ danh tính trước khi lưu snapshot

> Với vai trò người lao động, tôi muốn danh tính của mình được làm mờ trong snapshot, để quyền riêng tư được bảo vệ khi sự kiện được lưu.

- Ưu tiên / trạng thái: **P0 / Chưa làm**
- Phụ thuộc: US-06
- Acceptance criteria:
  - Ảnh được làm mờ mặt hoặc vùng nhận dạng đã chọn trước khi ghi xuống storage.
  - `privacy_blurred=true` chỉ được lưu khi xử lý thành công; không có snapshot gốc tồn tại sau pipeline.
  - Khi privacy processing lỗi, event không được xác nhận/lưu snapshot và UI báo lỗi có thể xử lý.
  - Có test ảnh có mặt, không tìm thấy mặt, nhiều mặt và lỗi xử lý/storage.
- Task:
  1. Chọn detector và chính sách fallback khi không nhận ra mặt.
  2. Xây privacy pipeline xử lý in-memory trước persistence.
  3. Bảo đảm transaction/file cleanup và metadata phản ánh đúng kết quả.
  4. Viết test bằng fixture không chứa dữ liệu cá nhân thật.

### US-13 — Đo precision, recall, false alarm và latency

> Với vai trò nhóm phát triển, tôi muốn đo các chỉ số chất lượng của prototype, để chứng minh MVP đáp ứng tiêu chí thành công và nêu rõ giới hạn.

- Ưu tiên / trạng thái: **P0 / Chưa làm**
- Phụ thuộc: US-07, US-08, US-09
- Acceptance criteria:
  - Bộ demo có ground truth phiên bản hóa cho person, PPE và zone violation.
  - Báo cáo có precision, recall, false-alarm rate và latency p50/p95; nêu hardware, model, threshold và kích thước mẫu.
  - Latency đo từ lúc frame được gửi đến lúc kết quả/cảnh báo hiển thị.
  - Ngưỡng nghiệm thu cụ thể được Product Owner chốt trước cuối tuần 1; kết quả dưới ngưỡng phải được ghi là giới hạn, không được che giấu.
- Task:
  1. Chuẩn hóa dataset/ground truth và script đánh giá có thể chạy lại.
  2. Instrument timestamp/correlation ID xuyên suốt frontend–backend–vision.
  3. Tính metric, đối chiếu dữ liệu review và xuất báo cáo baseline/final.

### US-14 — Phân mức cảnh báo và escalate sự cố nghiêm trọng

> Với vai trò cán bộ an toàn, tôi muốn sự cố xâm nhập vùng khi máy chạy được đánh dấu critical và ưu tiên ngay, để tôi can thiệp kịp thời.

- Ưu tiên / trạng thái: **P0 / Chưa hoàn thiện end-to-end**
- Phụ thuộc: US-04, US-05
- Acceptance criteria:
  - Severity là tập giá trị hữu hạn và được xác định bởi rule đã validate.
  - Xâm nhập vùng khi máy chạy luôn là critical trong MVP; PPE violation dùng severity theo rule.
  - Critical alert có tín hiệu hình ảnh rõ ràng, không bị chặn bởi cảnh báo mức thấp và luôn yêu cầu HITL review.
  - Escalate trong MVP là ưu tiên trên giao diện/queue cho một cán bộ an toàn; không gửi ra hệ thống ngoài nếu chưa được cấu hình.
- Task:
  1. Định nghĩa severity matrix, precedence và escalation state.
  2. Thêm severity vào inference/event contract và persistence.
  3. Xây critical UI/queue behavior và test thứ tự nhiều cảnh báo.

### US-15 — Chuyển trường hợp mơ hồ cho con người

> Với vai trò cán bộ an toàn, tôi muốn các detection có độ tin cậy mơ hồ được chuyển cho tôi xác minh, để hệ thống cân bằng bỏ sót với cảnh báo sai.

- Ưu tiên / trạng thái: **P1 / Chưa làm**
- Phụ thuộc: US-07, US-09
- Acceptance criteria:
  - Có hai ngưỡng cấu hình: dưới ngưỡng thấp thì bỏ qua, vùng mơ hồ thì review, trên ngưỡng cao thì áp dụng rule bình thường.
  - UI nêu detection confidence và lý do cần review mà không khẳng định chắc chắn vi phạm.
  - Quyết định của người dùng được lưu để tính false-alarm rate và phục vụ đánh giá sau này.
  - Có test đúng tại hai biên threshold.
- Task:
  1. Chốt threshold policy và cấu hình mặc định từ dữ liệu tuần 1.
  2. Tích hợp triage vào rule engine/event lifecycle.
  3. Cập nhật review UI, logging và test boundary.

### US-16 — Lưu memory/audit của phiên giám sát

> Với vai trò cán bộ an toàn, tôi muốn hệ thống ghi nhớ rule hiện hành, cảnh báo và quyết định review trong phiên, để có thể truy vết vì sao một sự kiện được tạo.

- Ưu tiên / trạng thái: **P1 / Hoàn thành một phần**
- Phụ thuộc: US-06, US-09, US-11
- Acceptance criteria:
  - Mỗi event liên kết được với rule version, machine state, zone, confidence, severity và quyết định HITL tại thời điểm tạo.
  - Reload trang vẫn xem được audit data đã lưu; không yêu cầu lưu raw video liên tục.
  - Chỉ snapshot vi phạm/review được lưu, đúng nguyên tắc giảm thiểu dữ liệu.
  - Có API/test truy xuất event detail và giải thích quyết định.
- Task:
  1. Chốt audit schema và retention mặc định cho demo.
  2. Lưu immutable decision context cùng event.
  3. Hiển thị event detail và lý do cảnh báo trong nhật ký.

### US-17 — Bảo mật dữ liệu demo

> Với vai trò người vận hành hệ thống, tôi muốn API, cấu hình bí mật và snapshot được bảo vệ, để dữ liệu an toàn không bị truy cập hoặc rò rỉ ngoài ý muốn.

- Ưu tiên / trạng thái: **P1 / Chưa được nghiệm thu**
- Phụ thuộc: US-12, US-16
- Acceptance criteria:
  - Secret lấy từ environment, không commit; cấu hình production không bật CORS wildcard hoặc debug.
  - Snapshot không được phục vụ bằng đường dẫn tùy ý; input upload có giới hạn type/size và chống path traversal.
  - Log không chứa raw image, secret hoặc dữ liệu nhận dạng chưa làm mờ.
  - Có security checklist và test cho input/file access quan trọng trong phạm vi MVP một người dùng.
- Task:
  1. Threat-model luồng upload, WebSocket, snapshot và configuration.
  2. Harden validation, file access, CORS, headers và logging.
  3. Chạy dependency/static scan phù hợp và xử lý lỗi mức high/critical trong code thuộc dự án.

### US-18 — Triển khai bản web demo có thể tái lập

> Với vai trò người đánh giá sản phẩm, tôi muốn mở một bản web demo ổn định, để chạy trọn luồng MVP mà không phải cấu hình thủ công từng dịch vụ.

- Ưu tiên / trạng thái: **P0 / Hoàn thành một phần**
- Phụ thuộc: US-07 đến US-17
- Acceptance criteria:
  - Docker build tạo một artifact chạy FastAPI, React production build, model config và database đã chọn cho môi trường demo.
  - Có health check, startup validation, migration và hướng dẫn deploy/rollback/backup tối thiểu.
  - Bản deploy chạy được core flow bằng video mẫu và không phụ thuộc API key để có quyết định fallback.
  - Smoke test sau deploy và checklist nghiệm thu có thể được một thành viên khác chạy lại.
- Task:
  1. Hoàn thiện Docker Compose/image, production env template và database migration.
  2. Cấu hình persistent volume, model artifact, health check và log vận hành.
  3. Deploy môi trường demo, chạy smoke/UAT và ghi lại phiên bản release.

### US-19 — Nghiệm thu end-to-end và bàn giao MVP

> Với vai trò Product Owner, tôi muốn một bộ kiểm thử và tài liệu bàn giao bao phủ toàn bộ core flow, để quyết định MVP có sẵn sàng demo và phát triển tiếp hay không.

- Ưu tiên / trạng thái: **P0 / Chưa làm đầy đủ**
- Phụ thuộc: US-01 đến US-18
- Acceptance criteria:
  - UAT bao phủ happy path, no-PPE, zone-entry khi máy ON/OFF, false alarm, dedup, privacy failure và reconnect.
  - `make check`, migration test, production build và deploy smoke test đều đạt trên phiên bản release.
  - PRD traceability matrix chỉ ra mỗi tiêu chí thành công được chứng minh bởi test/metric nào.
  - Known limitations, runbook demo, rollback và hướng dẫn vận hành được bàn giao.
- Task:
  1. Viết traceability matrix và UAT script từ acceptance criteria.
  2. Chạy full regression, sửa defect P0/P1 và ghi evidence.
  3. Chốt release candidate, demo rehearsal và biên bản nghiệm thu.

## 5. Kế hoạch delivery 5 tuần

Giả định một squad có thể làm song song Backend, Frontend, Vision/ML và QA/DevOps. Các story đã hoàn thành vẫn phải qua regression;
không tính là hoàn tất release chỉ vì đã có code baseline.

| Tuần | Mục tiêu | Story / task chính | Exit criteria cuối tuần |
|---|---|---|---|
| **Tuần 1 — Model và tiêu chí nghiệm thu** | Chốt baseline đo được và thay heuristic | Regression US-01→US-06; US-07 task 1–3; US-13 ground truth/instrumentation; chốt threshold/metric; thiết kế US-08/US-09 | PPE model chạy qua contract hiện có; dataset và ngưỡng nghiệm thu được chốt; baseline metric đầu tiên có thể chạy lại |
| **Tuần 2 — Tracking và event lifecycle** | Bảo đảm một vi phạm = một event | Hoàn tất US-07; US-08; US-09 backend/API; bắt đầu US-15 | Test track/dedup đạt; event state machine và API transition hoạt động; false alarm được lưu để tính metric |
| **Tuần 3 — Safety, HITL và privacy** | Hoàn thiện cảnh báo an toàn và bảo vệ danh tính | US-12; US-14; US-15; US-09 UI; bắt đầu US-11 | Critical zone alert được ưu tiên; ambiguous case vào review; không lưu snapshot chưa làm mờ; review end-to-end đạt |
| **Tuần 4 — Rule, memory, dashboard và hardening** | Hoàn thiện trải nghiệm vận hành MVP | US-10; US-11; US-16; US-17; chuẩn bị US-18 | Rule mô tả được validate và thực thi; dashboard khớp event data; audit truy vết được; security checklist không còn lỗi high/critical thuộc scope |
| **Tuần 5 — Deploy, đo lường và nghiệm thu** | Tạo release candidate có evidence | Hoàn tất US-13; US-18; US-19; full regression, UAT, sửa defect và demo rehearsal | Bản web demo chạy core flow; metric report và traceability đầy đủ; P0 = 0, P1 được xử lý hoặc có chấp thuận; Product Owner ký nghiệm thu |

### Milestone và cổng kiểm soát

- **M1 — Cuối tuần 1:** Model, dataset, metric target và contracts được khóa.
- **M2 — Cuối tuần 2:** Detection → tracking → dedup → event lifecycle ổn định.
- **M3 — Cuối tuần 3:** HITL và privacy đạt điều kiện an toàn bắt buộc.
- **M4 — Cuối tuần 4:** Feature complete; từ đây chỉ nhận sửa lỗi release-blocking.
- **M5 — Cuối tuần 5:** Release candidate được deploy, đo, UAT và bàn giao.

## 6. Definition of Done cho toàn MVP

MVP chỉ được xem là hoàn thành khi:

1. US-01 đến US-19 đạt acceptance criteria P0; P1 chưa đạt phải có quyết định chấp thuận bằng văn bản.
2. Core flow chạy trọn vẹn: mô tả/confirm rule → vẽ vùng → phát video → person/PPE/track → áp rule máy/vùng → alert/HITL → snapshot blur → event/audit → dashboard.
3. Một vi phạm liên tục chỉ tạo một event; critical alert gần realtime; false alarm đo được.
4. Không lưu snapshot chưa làm mờ và không lưu raw video liên tục.
5. Precision, recall, false-alarm rate và latency có số liệu tái lập; giới hạn của video mô phỏng được nêu rõ.
6. `make check`, production build, migration, deploy smoke test và UAT đều đạt trên cùng release commit.

## 7. Backlog sau MVP — không cam kết trong 5 tuần

### EPIC-P2-01 — Đăng nhập và phân quyền hai vai trò

> Với vai trò quản trị hệ thống, tôi muốn người dùng đăng nhập theo vai trò cán bộ an toàn hoặc quản lý khu vực, để mỗi người chỉ sử dụng đúng chức năng và dữ liệu được phép.

Bao gồm authentication, authorization, audit identity và phân quyền API/UI. Mục này mâu thuẫn với giới hạn “một người dùng” của PRD hiện tại nên cần Product Owner mở scope trước khi làm.

### EPIC-P2-02 — Nhiều camera, khu vực và ca làm việc

> Với vai trò quản lý khu vực, tôi muốn xem dữ liệu theo camera, khu vực và ca, để so sánh mức độ tuân thủ trong nhà máy.

Bao gồm quản lý camera/zone/shift, stream thật, dashboard theo khu vực/ca và khả năng scale inference.

### EPIC-P2-03 — Báo cáo và thông báo định kỳ

> Với vai trò quản lý khu vực, tôi muốn nhận báo cáo an toàn định kỳ và thông báo sự cố nghiêm trọng, để theo dõi xu hướng và điều phối xử lý.

Bao gồm lịch báo cáo, template, kênh email/chat/SMS, delivery status và retry.

### EPIC-P2-04 — Tích hợp PLC và quy trình nhà máy

> Với vai trò cán bộ an toàn, tôi muốn hệ thống nhận trạng thái máy từ nguồn tin cậy và tích hợp quy trình ứng cứu, để giảm thao tác thủ công khi triển khai thực tế.

MVP không tự động dừng máy; mọi hành động tác động thiết bị phải qua đánh giá an toàn, phân quyền và fail-safe riêng.

### EPIC-P2-05 — Field validation và vận hành production

> Với vai trò chủ sản phẩm, tôi muốn đánh giá hệ thống trên dữ liệu nhà máy thật, để biết mô hình có đủ tin cậy trước khi đưa vào vận hành production.

Bao gồm phê duyệt quyền riêng tư, retention, monitoring/drift, model versioning, incident response, capacity/cost và kiểm định tại hiện trường.
