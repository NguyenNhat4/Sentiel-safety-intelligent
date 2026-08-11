# User Story Backlog & Kế hoạch giao toàn bộ dự án

## 1. Quy ước đồng bộ

- `USER_STORIES_LIST.md` là backlog tổng và nguồn kế hoạch.
- Mỗi story chưa hoàn thành có một file `backlog/US-XX.md`.
- Nội dung từ heading `### US-XX` đến hết Task trong file riêng phải giống nguyên văn mục tương ứng ở tài liệu này.
- **P0:** bắt buộc để nghiệm thu giai đoạn; **P1:** cần hoàn thiện đầu ra nhưng có thể được Product Owner chấp thuận chuyển tiếp nếu có owner và deadline.
- Done yêu cầu: đạt acceptance criteria, có test/evidence, cập nhật tài liệu và không làm hỏng contract hiện hành.
- folder done chua cac US-XX da duoc trien khai va hoan thien. 

### US-01 — Tải và phát video mô phỏng

> Với vai trò cán bộ an toàn, tôi muốn tải và phát một video mô phỏng, để giám sát tình huống an toàn mà không cần camera nhà máy thật.

- Trạng thái: **Hoàn thành baseline; bắt buộc regression khi nghiệm thu MVP.**

### US-02 — Cấu hình vùng nguy hiểm bằng bốn điểm

> Với vai trò cán bộ an toàn, tôi muốn chấm bốn điểm trên video, để xác định vùng cấm cần giám sát.

- Trạng thái: **Hoàn thành baseline; bắt buộc regression khi nghiệm thu MVP.**

### US-03 — Phát hiện người gần realtime

> Với vai trò cán bộ an toàn, tôi muốn hệ thống phát hiện người trong video gần realtime, để quan sát vị trí của họ so với vùng nguy hiểm.

- Trạng thái: **Hoàn thành baseline; bắt buộc regression khi nghiệm thu MVP.**

### US-04 — Kết hợp vùng nguy hiểm với trạng thái máy

> Với vai trò cán bộ an toàn, tôi muốn cảnh báo xâm nhập chỉ kích hoạt khi máy đang chạy, để giảm cảnh báo sai khi khu vực an toàn.

- Trạng thái: **Hoàn thành baseline; bắt buộc regression khi nghiệm thu MVP.**

### US-05 — Nhận và review cảnh báo gần realtime

> Với vai trò cán bộ an toàn, tôi muốn nhận cảnh báo ngay khi phát hiện tình huống nguy hiểm, để đánh giá và phản ứng kịp thời.

- Trạng thái: **Hoàn thành baseline; bắt buộc regression khi nghiệm thu MVP.**

### US-06 — Lưu và xem nhật ký vi phạm

> Với vai trò cán bộ an toàn, tôi muốn lưu vi phạm đã xác nhận và xem lại trong nhật ký, để có bằng chứng phục vụ theo dõi an toàn.

- Trạng thái: **Hoàn thành baseline; bắt buộc regression khi nghiệm thu MVP.**


### US-07 — Phát hiện thiếu PPE bắt buộc bằng model

> Với vai trò cán bộ an toàn, tôi muốn hệ thống nhận biết từng người có thiếu mũ, kính hoặc găng bảo hộ hay không, để phát hiện đúng các vi phạm PPE trong problem statement.

- Ưu tiên / trạng thái: **P0 / Hoàn thành một phần**
- Phụ thuộc: US-03
- Acceptance criteria:
  - Model PPE đã huấn luyện được nạp từ cấu hình và nhận biết tối thiểu ba nhóm bắt buộc: mũ, kính và găng bảo hộ; heuristic màu/áo phản quang không còn là kết quả PPE chính.
  - Kết quả PPE được gắn đúng theo từng person/track, nêu rõ hạng mục có/thiếu và confidence mà không phá vỡ inference contract.
  - Giao diện có công tắc ON/OFF riêng cho yêu cầu mũ, kính và găng cùng nút **Lưu cấu hình**; trước lần lưu đầu tiên, cả ba yêu cầu mặc định OFF.
  - Cấu hình được lưu bền vững tại backend theo cặp camera–khu vực, tự khôi phục sau khi tải lại hoặc khởi động lại hệ thống và dùng chung giữa người dùng, trình duyệt và thiết bị. Trong MVP chỉ hỗ trợ một cặp camera–khu vực cố định.
  - Model vẫn phát hiện và trả kết quả cho cả ba nhóm PPE bất kể trạng thái công tắc. Hệ thống chỉ tạo cảnh báo thiếu một loại PPE khi yêu cầu tương ứng đang ON; trạng thái OFF không tạo cảnh báo cho loại đó.
  - Confidence threshold có thể cấu hình; có test class mapping, threshold, thiếu một/nhiều PPE, không phát hiện PPE, nhiều người, giá trị mặc định, lưu/khôi phục cấu hình và luật cảnh báo ON/OFF.
- Task:
  1. Chốt weights, class mapping cho mũ/kính/găng, giấy phép model và bộ dữ liệu demo có ground truth theo từng người.
  2. Tạo adapter PPE model và cấu hình weights/device/threshold.
  3. Tạo persistence và API đọc/lưu cấu hình yêu cầu PPE cho cặp camera–khu vực cố định, với giá trị mặc định OFF.
  4. Thêm ba công tắc và nút **Lưu cấu hình** trên giao diện; tải cấu hình dùng chung từ backend khi khởi tạo.
  5. Tích hợp kết quả PPE theo person/track vào REST và WebSocket, áp dụng cấu hình vào luật cảnh báo; chạy integration test và benchmark cho từng nhóm PPE.

### US-08 — Theo dõi người và chống tạo event trùng

> Với vai trò cán bộ an toàn, tôi muốn một vi phạm liên tục chỉ tạo một event, để nhật ký không bị lặp và cảnh báo không gây nhiễu.

- Ưu tiên / trạng thái: **P0 / Hoàn thành**
- Phụ thuộc: US-03, US-07
- Acceptance criteria:
  - Mỗi detection có `track_id` ổn định trong một phiên video.
  - Cùng người, cùng rule và cùng lần vi phạm chỉ có một event active.
  - Event mới chỉ được tạo sau khi vi phạm kết thúc rồi tái diễn hoặc hết cooldown; có test mất track ngắn, tái xâm nhập và nhiều người.
- Task hoàn thành:
  1. [x] ByteTrack/session tracking và mapping detection-to-track.
  2. [x] Dedup key, occurrence lifecycle, exit confirmation và cooldown.
  3. [x] Violation state theo track, idempotent event persistence và kiểm thử frame/database/browser.

### US-09 — Vòng đời review của cảnh báo

> Với vai trò cán bộ an toàn, tôi muốn acknowledge, xác nhận vi phạm hoặc đánh dấu cảnh báo sai, để hệ thống ghi đúng quyết định của con người.

- Ưu tiên / trạng thái: **P0 / Hoàn thành một phần**
- Phụ thuộc: US-06, US-08
- Acceptance criteria:
  - State machine `pending`, `acknowledged`, `confirmed`, `false_alarm` được tài liệu hóa.
  - False alarm được lưu để tính metric nhưng không xuất hiện như vi phạm chính thức.
  - API từ chối transition không hợp lệ, có timestamp/idempotency; refresh trang không làm mất event đang chờ.
- Task:
  1. Chốt state machine và migration schema.
  2. Bổ sung API transition, validation, audit timestamp và idempotency.
  3. Cập nhật review UI, filter lịch sử và test API/component/end-to-end.

### US-10 — Dashboard thống kê MVP

> Với vai trò cán bộ an toàn, tôi muốn xem thống kê sự kiện của phiên demo, để đánh giá tình hình tuân thủ và chất lượng cảnh báo.

- Ưu tiên / trạng thái: **P0 / Hoàn thành một phần**
- Phụ thuộc: US-09
- Acceptance criteria:
  - Hiển thị tổng cảnh báo, vi phạm xác nhận, false alarm, PPE violation và zone violation.
  - Dữ liệu lấy từ statistics API, có bộ lọc thời gian và timezone cấu hình.
  - Có loading, empty, error state; số liệu khớp event fixture trong integration test.
- Task:
  1. Hoàn thiện query và response contract của statistics API.
  2. Xây dashboard cards/charts tối thiểu và bộ lọc thời gian.
  3. Thêm test service, API, component và empty/error state.

### US-11 — Sinh và áp dụng rule từ mô tả

> Với vai trò cán bộ an toàn, tôi muốn mô tả quy tắc và mức độ vi phạm bằng ngôn ngữ tự nhiên, để hệ thống biết khi nào cảnh báo hoặc bỏ qua.

- Ưu tiên / trạng thái: **P0 / Hoàn thành một phần**
- Phụ thuộc: US-04, US-07
- Acceptance criteria:
  - Mô tả được chuyển thành cấu trúc rule gồm loại vi phạm, điều kiện máy/vùng/PPE và severity.
  - Rule được validate, preview và người dùng xác nhận trước khi áp dụng.
  - Inference chỉ thực thi rule có schema hợp lệ; có fallback deterministic khi thiếu API key và lý do giải thích quyết định.
- Task:
  1. Chốt JSON schema và danh sách điều kiện/severity được phép.
  2. Hoàn thiện Safety Agent structured output, validation và fallback.
  3. Xây UI nhập/preview/confirm, lưu rule phiên và nối rule engine vào inference.

### US-12 — Làm mờ danh tính trước khi lưu snapshot

> Với vai trò người lao động, tôi muốn danh tính của mình được làm mờ trong snapshot, để quyền riêng tư được bảo vệ khi sự kiện được lưu.

- Ưu tiên / trạng thái: **P0 / Hoàn thành**
- Phụ thuộc: US-06
- Acceptance criteria:
  - Ảnh được làm mờ mặt hoặc vùng nhận dạng trước khi ghi xuống storage.
  - `privacy_blurred=true` chỉ được lưu khi xử lý thành công; không tồn tại snapshot gốc sau pipeline.
  - Khi privacy processing lỗi, event không được xác nhận/lưu ảnh; có test không mặt, một/nhiều mặt và lỗi xử lý.
- Task:
  1. Chọn detector và chính sách fallback khi không nhận ra mặt.
  2. Xây privacy pipeline xử lý in-memory trước persistence.
  3. Bảo đảm transaction/file cleanup, metadata và test fixture không chứa dữ liệu cá nhân thật.

### US-13 — Đo precision, recall, false alarm và latency

> Với vai trò nhóm phát triển, tôi muốn đo các chỉ số chất lượng của prototype, để chứng minh MVP đáp ứng tiêu chí thành công và nêu rõ giới hạn.

- Ưu tiên / trạng thái: **P0 / Chưa làm**
- Phụ thuộc: US-07, US-08, US-09
- Acceptance criteria:
  - Bộ demo có ground truth phiên bản hóa cho person, PPE và zone violation.
  - Báo cáo có precision, recall, false-alarm rate, latency p50/p95 và nêu hardware, model, threshold, kích thước mẫu.
  - Latency được đo xuyên suốt từ gửi frame đến hiển thị cảnh báo; ngưỡng nghiệm thu được Product Owner chốt trong tuần hiện tại.
- Task:
  1. Chuẩn hóa dataset/ground truth và script đánh giá có thể chạy lại.
  2. Instrument timestamp/correlation ID xuyên frontend–backend–vision.
  3. Chạy baseline/final, đối chiếu review data và xuất báo cáo.

### US-24 — Phân tích ảnh mô phỏng

> Với vai trò cán bộ an toàn, tôi muốn tải một ảnh mô phỏng để phân tích theo cùng rule PPE và vùng nguy hiểm, để kiểm tra nhanh tình huống không cần phát video.

- Ưu tiên / trạng thái: **P0 / Chưa làm**
- Phụ thuộc: US-07, US-11, US-12
- Acceptance criteria:
  - Chấp nhận định dạng ảnh/giới hạn dung lượng được cấu hình và từ chối input không hợp lệ.
  - Kết quả dùng cùng detection/rule contract với video và hiển thị bounding box, PPE có/thiếu, confidence và severity.
  - Chỉ lưu event khi người dùng xác nhận; snapshot lưu trữ phải được làm mờ.
  - Có test ảnh không người, một/nhiều người, thiếu mũ/kính/găng, zone violation và file lỗi.
- Task:
  1. Tái sử dụng frame inference pipeline cho image endpoint.
  2. Xây upload/result/review UI và contract validation.
  3. Kiểm thử privacy, event lifecycle và parity với video.

### US-16 — Lưu memory và audit của phiên giám sát

> Với vai trò cán bộ an toàn, tôi muốn hệ thống ghi nhớ rule, cảnh báo và quyết định review trong phiên, để truy vết vì sao một sự kiện được tạo.

- Ưu tiên / trạng thái: **P0 / Hoàn thành một phần**
- Phụ thuộc: US-06, US-09, US-11
- Acceptance criteria:
  - Mỗi event liên kết rule version, machine state, zone, confidence, severity và quyết định HITL tại thời điểm tạo.
  - Reload trang vẫn truy xuất được audit data; không lưu raw video liên tục.
  - Chỉ snapshot vi phạm/review được lưu; event detail giải thích được quyết định.
  - Có thể sinh bản tóm tắt sự việc bằng ngôn ngữ tự nhiên từ decision context đã lưu; nội dung sinh phải bám dữ liệu nguồn, có fallback deterministic và không thay thế audit data có cấu trúc.
- Task:
  1. Chốt audit schema và retention mặc định.
  2. Lưu immutable decision context cùng event.
  3. Hoàn thiện event-detail API/UI, bản tóm tắt sự việc tùy chọn và test truy xuất/fallback.

### US-17 — Bảo mật dữ liệu MVP

> Với vai trò người vận hành hệ thống, tôi muốn API, cấu hình bí mật và snapshot được bảo vệ, để dữ liệu an toàn không bị truy cập hoặc rò rỉ ngoài ý muốn.

- Ưu tiên / trạng thái: **P1 / Chưa được nghiệm thu**
- Phụ thuộc: US-12, US-16
- Acceptance criteria:
  - Secret lấy từ environment; production không bật debug hoặc CORS wildcard.
  - Upload có giới hạn type/size; snapshot access chống path traversal; log không chứa ảnh thô, secret hoặc danh tính chưa làm mờ.
  - Security checklist và test quan trọng đạt; không còn lỗi high/critical thuộc code dự án.
- Task:
  1. Threat-model upload, WebSocket, snapshot và configuration.
  2. Harden validation, file access, CORS, headers và logging.
  3. Chạy dependency/static scan và xử lý phát hiện high/critical.

### US-20 — Đăng nhập và phân quyền hai vai trò

> Với vai trò người dùng hệ thống, tôi muốn đăng nhập theo vai trò cán bộ an toàn hoặc quản lý khu vực, để chỉ truy cập đúng chức năng và dữ liệu được phép.

- Ưu tiên / trạng thái: **P0 / Chưa làm**
- Phụ thuộc: US-17
- Acceptance criteria:
  - Có login/logout, password hashing, session/token expiry và tài khoản seed an toàn cho môi trường demo.
  - Cán bộ an toàn được monitor, review, acknowledge; quản lý khu vực được xem dashboard/báo cáo theo phạm vi.
  - Backend thực thi authorization cho API và WebSocket; ẩn nút trên UI không được xem là đủ bảo mật.
  - Audit event lưu actor; có test matrix cho allowed, forbidden và unauthenticated.
- Task:
  1. Chốt permission matrix và authentication flow.
  2. Tạo user/role schema, migration, auth API/middleware và WebSocket authorization.
  3. Xây login/session UI, route guard, audit actor và security tests.

### US-18 — Triển khai bản web MVP có thể tái lập

> Với vai trò người đánh giá sản phẩm, tôi muốn mở một bản web MVP ổn định, để chạy trọn luồng PRD mà không phải cấu hình thủ công từng dịch vụ.

- Ưu tiên / trạng thái: **P0 / Hoàn thành một phần**
- Phụ thuộc: US-07 đến US-13, US-16, US-17, US-20, US-24
- Acceptance criteria:
  - Docker build tạo artifact chạy FastAPI, React production build, model config và database demo.
  - Có health check, startup validation, migration và hướng dẫn deploy/rollback/backup tối thiểu.
  - Bản deploy chạy core flow bằng video mẫu, có fallback khi thiếu API key và smoke test có thể chạy lại.
- Task:
  1. Hoàn thiện Docker Compose/image, production env template và migration.
  2. Cấu hình persistent volume, model artifact, health check và log vận hành.
  3. Deploy môi trường MVP, chạy smoke/UAT và ghi phiên bản release.

### US-19 — Nghiệm thu và bàn giao MVP

> Với vai trò Product Owner, tôi muốn bộ kiểm thử và tài liệu bàn giao bao phủ core flow, để xác nhận MVP hoàn thành trong tuần hiện tại.

- Ưu tiên / trạng thái: **P0 / Chưa làm đầy đủ**
- Phụ thuộc: US-01 đến US-13, US-16 đến US-18, US-20, US-24
- Acceptance criteria:
  - UAT bao phủ đăng nhập/phân quyền, video/ảnh, thiếu mũ/kính/găng, zone-entry khi máy ON/OFF, false alarm, dedup, privacy failure và reconnect.
  - `make check`, migration test, production build và deploy smoke test đạt trên cùng release commit.
  - PRD traceability matrix, metric evidence, known limitations, runbook demo và rollback được bàn giao.
  - Không còn defect P0; defect P1 phải có quyết định chấp thuận bằng văn bản.
- Task:
  1. Viết traceability matrix và UAT script.
  2. Chạy full regression, sửa defect release-blocking và ghi evidence.
  3. Chốt release candidate, demo rehearsal và biên bản nghiệm thu MVP.

### Cổng nghiệm thu MVP cuối tuần hiện tại

- Core flow chạy trọn vẹn sau đăng nhập đúng vai trò: tải video hoặc ảnh → mô tả/confirm rule → vẽ vùng → person + mũ/kính/găng + track → áp trạng thái máy/vùng → HITL → snapshot blur → event/audit → dashboard.
- Một vi phạm liên tục chỉ tạo một event; false alarm được lưu để đo; không lưu snapshot chưa làm mờ.
- Precision, recall, false-alarm rate và latency có báo cáo tái lập.
- `make check`, production build, migration, deploy smoke test và UAT đạt trên cùng release commit.
- US-20 và US-24 đạt acceptance criteria trong MVP; US-19 được Product Owner nghiệm thu và là điểm bắt đầu kế hoạch nâng cao 5 tuần.

## 4. User story nâng cao trong 5 tuần tiếp theo

### US-14 — Tự động escalate sự cố nghiêm trọng

> Với vai trò cán bộ an toàn phụ trách, tôi muốn sự cố critical được tự động chuyển đến đúng người và theo dõi trạng thái tiếp nhận, để phản ứng kịp thời khi có người trong vùng nguy hiểm.

- Ưu tiên / trạng thái: **P0 nâng cao / Chưa hoàn thiện end-to-end**
- Phụ thuộc: US-04, US-09, US-20, US-21
- Acceptance criteria:
  - Xâm nhập vùng khi máy chạy luôn là critical; PPE violation lấy severity từ rule đã validate.
  - Critical alert được ưu tiên trên UI và gửi qua ít nhất một kênh ngoài hệ thống đến người phụ trách khu vực.
  - Escalation có delivery status, retry có giới hạn, acknowledge và audit; không gửi trùng cho cùng event.
  - Khi kênh ngoài lỗi, cảnh báo trong ứng dụng vẫn hoạt động và hiển thị lỗi cho người vận hành.
  - Cảnh báo có thể kèm diễn giải sự việc ngắn bằng ngôn ngữ tự nhiên từ event context; diễn giải là enhancement, có fallback deterministic và không quyết định severity/routing.
- Task:
  1. Định nghĩa severity matrix, routing theo khu vực và escalation state machine.
  2. Xây notification adapter, retry/idempotency và cấu hình người nhận.
  3. Tích hợp UI/queue, delivery audit, diễn giải tùy chọn và test success/failure/duplicate/fallback.

### US-15 — Chuyển trường hợp mơ hồ cho con người

> Với vai trò cán bộ an toàn, tôi muốn detection có độ tin cậy mơ hồ được chuyển cho tôi xác minh, để cân bằng nguy cơ bỏ sót với cảnh báo sai.

- Ưu tiên / trạng thái: **P0 nâng cao / Chưa làm**
- Phụ thuộc: US-07, US-09
- Acceptance criteria:
  - Có hai ngưỡng cấu hình: dưới ngưỡng thấp thì bỏ qua, vùng mơ hồ thì review, trên ngưỡng cao thì áp rule.
  - UI hiển thị confidence và lý do cần review mà không khẳng định chắc chắn vi phạm.
  - Quyết định HITL được lưu để tính false-alarm rate và có test đúng tại hai biên threshold.
- Task:
  1. Chốt threshold policy từ kết quả US-13.
  2. Tích hợp triage vào rule engine và event lifecycle.
  3. Cập nhật review UI, audit và boundary test.

### US-21 — Quản lý khu vực và ca làm việc

> Với vai trò quản lý khu vực, tôi muốn cấu hình khu vực, người phụ trách và ca làm việc, để sự kiện được thống kê và chuyển đúng ngữ cảnh vận hành.

- Ưu tiên / trạng thái: **P0 nâng cao / Chưa làm**
- Phụ thuộc: US-20
- Acceptance criteria:
  - Có CRUD tối thiểu cho khu vực và ca; mỗi khu vực có người phụ trách escalation.
  - Mỗi monitoring session/event gắn `zone_id`, `shift_id` và timezone hợp lệ.
  - Không xóa cứng cấu hình đã được event tham chiếu; có validation thời gian ca giao nhau.
  - Có migration, API/UI và test phân quyền theo US-20.
- Task:
  1. Thiết kế zone/shift/assignment schema và migration.
  2. Xây service/API/UI cấu hình với validation và soft-delete.
  3. Gắn context vào session, event, audit và test timezone/overlap.

### US-22 — Dashboard tuân thủ theo khu vực và ca

> Với vai trò quản lý khu vực, tôi muốn xem tỷ lệ tuân thủ theo khu vực và ca, để xác định nơi và thời điểm có rủi ro an toàn cao.

- Ưu tiên / trạng thái: **P0 nâng cao / Chưa làm**
- Phụ thuộc: US-09, US-20, US-21
- Acceptance criteria:
  - Dashboard lọc theo thời gian, khu vực, ca, loại vi phạm và severity.
  - Hiển thị tổng quan, tỷ lệ tuân thủ, xu hướng, false-alarm rate và top khu vực/ca rủi ro.
  - Metric có công thức và mẫu số rõ ràng; dữ liệu tuân thủ phân quyền và khớp fixture backend.
  - Có loading, empty, error, timezone và export CSV tối thiểu.
- Task:
  1. Chốt metric definitions và query contract.
  2. Tối ưu statistics service/index cần thiết và phân quyền dữ liệu.
  3. Xây dashboard filter/chart/table/export và test đối soát số liệu.

### US-23 — Báo cáo an toàn định kỳ

> Với vai trò quản lý khu vực, tôi muốn nhận báo cáo an toàn định kỳ, để theo dõi xu hướng tuân thủ và hành động cần ưu tiên.

- Ưu tiên / trạng thái: **P0 nâng cao / Chưa làm**
- Phụ thuộc: US-20, US-21, US-22
- Acceptance criteria:
  - Cho phép cấu hình lịch ngày/tuần, timezone, phạm vi khu vực/ca và danh sách người nhận.
  - Báo cáo chứa KPI, xu hướng, sự cố critical, false alarm và link về dashboard; không đính kèm ảnh chưa làm mờ.
  - Có thể sinh phần diễn giải xu hướng và sự cố bằng ngôn ngữ tự nhiên từ KPI/event đã tổng hợp; nội dung phải truy vết được về dữ liệu nguồn, có fallback deterministic và không tự suy đoán metric.
  - Job chạy idempotent, có retry, delivery status và lịch sử tải lại.
  - Template có HTML/PDF hoặc CSV theo lựa chọn đã chốt; test scheduler không phụ thuộc thời gian thực.
- Task:
  1. Chốt report template, schedule schema và retention.
  2. Xây aggregation snapshot, scheduler/worker, renderer và phần diễn giải tùy chọn.
  3. Tích hợp delivery adapter, lịch sử báo cáo, UI cấu hình và test timezone/retry.

### US-25 — Triển khai cloud và khả năng vận hành

> Với vai trò người vận hành hệ thống, tôi muốn triển khai ứng dụng lên cloud với giám sát và sao lưu, để bản nâng cao hoạt động ổn định và có thể phục hồi.

- Ưu tiên / trạng thái: **P0 nâng cao / Chưa làm**
- Phụ thuộc: US-14, US-20 đến US-24
- Acceptance criteria:
  - Infrastructure/config của môi trường được tài liệu hóa; HTTPS, secret management, database migration và persistent storage hoạt động.
  - Có application/error metrics, structured logs, health/readiness, alert vận hành và correlation ID.
  - Backup/restore database và snapshot đã làm mờ được diễn tập; có retention và rollback release.
  - Smoke/load test theo tải demo đạt ngân sách latency/cost được chốt; không còn lỗ hổng high/critical thuộc scope.
- Task:
  1. Chốt cloud target, sizing, SLO, cost ceiling và architecture deployment.
  2. Thiết lập CI/CD, secret, managed database/storage, HTTPS và observability.
  3. Diễn tập migration, backup/restore, rollback; chạy smoke/load/security test.

### US-26 — Nghiệm thu và bàn giao phiên bản nâng cao

> Với vai trò Product Owner, tôi muốn nghiệm thu toàn bộ yêu cầu nâng cao trên môi trường cloud, để xác nhận dự án sẵn sàng trình diễn và pilot có kiểm soát.

- Ưu tiên / trạng thái: **P0 nâng cao / Chưa làm**
- Phụ thuộc: US-14, US-15, US-20 đến US-25
- Acceptance criteria:
  - UAT bao phủ hai vai trò, khu vực/ca, threshold HITL, auto-escalation, dashboard, báo cáo, ảnh và video.
  - Traceability matrix liên kết từng yêu cầu problem statement với story, test và evidence.
  - Metric chất lượng/latency, security checklist, runbook, incident response và known limitations được bàn giao.
  - Không còn defect P0; defect P1 có owner, deadline và chấp thuận; release tag/rollback đã được diễn tập.
- Task:
  1. Viết advanced UAT và traceability matrix.
  2. Chạy full regression, security/performance test và sửa defect release-blocking.
  3. Chốt release candidate, demo rehearsal, tài liệu vận hành và biên bản nghiệm thu.

## 5. Kế hoạch delivery nâng cao 5 tuần

| Tuần | Mục tiêu | Story / task chính | Exit criteria |
|---|---|---|---|
| **Tuần 1 — Context vận hành** | Bổ sung dữ liệu khu vực/ca trên nền đăng nhập và RBAC đã đạt cổng MVP | US-21; thiết kế routing US-14 | Event mới gắn đúng zone/shift/actor; người phụ trách escalation cấu hình được; regression RBAC đạt |
| **Tuần 2 — HITL theo confidence** | Xử lý detection mơ hồ và chuẩn bị escalation | US-15; baseline notification adapter US-14 | Threshold triage đạt boundary test; escalation gửi được trên môi trường test; video/ảnh tiếp tục đạt regression parity |
| **Tuần 3 — Escalation tự động** | Critical incident đến đúng người và truy vết được | Hoàn tất US-14; chuẩn bị aggregation US-22 | Critical event gửi đúng người, retry/idempotent, acknowledge và audit đầy đủ; lỗi kênh ngoài không làm mất in-app alert |
| **Tuần 4 — Phân tích quản trị và báo cáo** | Quản lý theo dõi tuân thủ theo khu vực/ca | US-22, US-23 | Dashboard đối soát đúng fixture; báo cáo định kỳ chạy đúng timezone, idempotent và không lộ ảnh chưa làm mờ |
| **Tuần 5 — Cloud release và bàn giao** | Vận hành, đo, UAT và nghiệm thu toàn dự án | US-25, US-26; full regression và sửa defect | Cloud release đạt smoke/security/performance; backup/restore/rollback diễn tập; advanced UAT và traceability được ký nghiệm thu |

### Milestone

- **A1 — Cuối tuần 1:** Zone/shift context và routing owner được khóa trên nền authorization của MVP.
- **A2 — Cuối tuần 2:** Confidence-based HITL và notification adapter baseline hoàn tất.
- **A3 — Cuối tuần 3:** Auto-escalation production-ready trong phạm vi một notification provider.
- **A4 — Cuối tuần 4:** Dashboard và periodic report feature-complete.
- **A5 — Cuối tuần 5:** Cloud release, evidence, runbook và nghiệm thu toàn dự án hoàn tất.

## 6. Ngoài phạm vi cam kết 5 tuần

Camera nhà máy thật, tích hợp PLC, tự động dừng máy và scale nhiều stream đồng thời cần discovery, đánh giá an toàn hiện trường và thay đổi scope riêng. Chúng không được ngầm đưa vào release 5 tuần.
