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

- Ưu tiên / trạng thái: **P0 / Hoàn thành**
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

- Ưu tiên / trạng thái: **P0 / Đã chốt custom dataset, chưa triển khai**
- Phụ thuộc: US-07, US-08, US-09
- Acceptance criteria:
  - Nguồn nghiệm thu chính là custom dataset do dự án tự tạo trong bối cảnh mô phỏng có sự đồng ý của người tham gia; public dataset chỉ được dùng bổ sung để regression hoặc tham khảo, không thay thế final evaluation set.
  - Custom dataset bao phủ người không vi phạm, thiếu riêng/tổ hợp mũ bảo hộ và áo phản quang, zone entry khi máy ON/OFF, ra khỏi zone rồi tái xâm nhập, mất track ngắn/che khuất và nhiều người có trạng thái khác nhau.
  - Ground truth được phiên bản hóa bằng manifest và checksum, gồm video/scenario ID, split, person bbox/track, trạng thái PPE `present`/`missing`/`unknown` theo người, polygon zone, machine-state timeline, khoảng violation occurrence và expected review outcome; raw media không được commit trực tiếp nếu chưa có storage/quyền truy cập phù hợp.
  - Dataset được chia theo video/scenario thành calibration và final evaluation; final evaluation được khóa trước benchmark và không được dùng để chọn model, threshold hoặc chỉnh rule.
  - Báo cáo có precision/recall cho person, từng loại PPE và zone occurrence; false-alarm rate theo định nghĩa đã duyệt; latency end-to-end p50/p95; đồng thời nêu hardware, model/checksum, threshold, dataset version, kích thước mẫu, failure cases và giới hạn của prototype.
  - Latency được correlate xuyên frontend–backend–vision và đo từ lúc browser gửi frame đến khi cảnh báo được render; metric definition, sample size và ngưỡng nghiệm thu được Product Owner chốt trước khi khóa final evaluation.
- Task:
  1. Chốt metric protocol, scenario matrix, annotation guide, quyền sử dụng/đồng ý của người tham gia, sample size và ngưỡng nghiệm thu với Product Owner.
  2. Quay custom dataset, gán ground truth, kiểm tra chéo annotation, tạo manifest/checksum và khóa calibration/final split theo video/scenario.
  3. Xây script đánh giá có thể chạy lại cho person/PPE/zone occurrence, dedup và false alarm; thêm fixture/test cho matching, zero-denominator và duplicate occurrence.
  4. Instrument correlation ID cùng timestamp xuyên frontend–backend–vision, đo thời điểm alert render và kiểm thử contract theo hướng additive.
  5. Chạy baseline, chỉ tune trên calibration set, khóa model/threshold/rule rồi chạy final evaluation; đối chiếu review data và xuất báo cáo tái lập được.

### US-24 — Phân tích ảnh mô phỏng

> Với vai trò cán bộ an toàn, tôi muốn tải một ảnh mô phỏng để phân tích theo cùng rule PPE và vùng nguy hiểm, để kiểm tra nhanh tình huống không cần phát video.

- Ưu tiên / trạng thái: **P0 / Chưa làm**
- Phụ thuộc: US-07, US-11, US-12
- Acceptance criteria:
  - Chấp nhận định dạng ảnh/giới hạn dung lượng được cấu hình và từ chối input không hợp lệ.
  - Kết quả dùng cùng detection/rule contract với video và hiển thị bounding box, PPE có/thiếu, confidence và severity.
  - Chỉ lưu event khi người dùng xác nhận; snapshot lưu trữ phải được làm mờ.
  - Có test ảnh không người, một/nhiều người, thiếu mũ/áo phản quang, zone violation và file lỗi.
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

### US-20 — Đăng nhập và phân quyền ba vai trò

> Với vai trò người dùng hệ thống, tôi muốn đăng nhập theo vai trò quản trị hệ thống, cán bộ an toàn hoặc quản lý khu vực, để truy cập đúng workspace và dữ liệu được phép.

- Ưu tiên / trạng thái: **P0 / Hoàn thành một phần**
- Phụ thuộc: US-17
- Acceptance criteria:
  - Có login/logout, password hashing, session/token expiry và tài khoản seed an toàn cho môi trường demo.
  - Cán bộ an toàn được monitor, review, acknowledge; quản lý khu vực có dashboard riêng; quản trị hệ thống có chức năng của cán bộ an toàn và thêm quản trị tài khoản.
  - Tài khoản mới/reset dùng mật khẩu tạm và bắt buộc thay ở lần đăng nhập tiếp theo.
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
  - UAT bao phủ đăng nhập/phân quyền, video/ảnh, thiếu mũ/áo phản quang, zone-entry khi máy ON/OFF, false alarm, dedup, privacy failure và reconnect.
  - `make check`, migration test, production build và deploy smoke test đạt trên cùng release commit.
  - PRD traceability matrix, metric evidence, known limitations, runbook demo và rollback được bàn giao.
  - Không còn defect P0; defect P1 phải có quyết định chấp thuận bằng văn bản.
- Task:
  1. Viết traceability matrix và UAT script.
  2. Chạy full regression, sửa defect release-blocking và ghi evidence.
  3. Chốt release candidate, demo rehearsal và biên bản nghiệm thu MVP.

### US-27 — Giám sát nhiều vùng nguy hiểm trên một video

> Với vai trò cán bộ an toàn, tôi muốn cấu hình và theo dõi nhiều vùng nguy hiểm trên cùng một video, mỗi vùng có trạng thái máy riêng, để giám sát đồng thời nhiều máy hoặc khu vực trong một khung hình.

- Ưu tiên / trạng thái: **P0 / Đã triển khai, chờ browser UAT cuối MVP**
- Phụ thuộc: US-02, US-04, US-08, US-09
- Acceptance criteria:
  - Một monitoring session của video `uploaded_video` hỗ trợ số lượng vùng không có giới hạn nghiệp vụ cố định; mỗi vùng có `zone_id` ổn định, tên hiển thị, đúng bốn điểm chuẩn hóa, trạng thái `running`/`stopped` và cờ bật/tắt.
  - UI có đúng một nút **Tạo vùng** làm entrypoint tạo mới. Chỉ sau khi bấm nút, Canvas mới vào chế độ vẽ và nhận bốn click tạo polygon draft; click Canvas ở trạng thái bình thường không được tự tạo vùng. Draft chỉ có hiệu lực sau khi lưu thành công và được khôi phục từ backend khi tải lại trang.
  - Các polygon active không được giao nhau, chạm biên/đỉnh hoặc chứa nhau; backend từ chối toàn bộ cấu hình không hợp lệ. Mỗi person trả membership theo từng vùng và `review_required=true` khi có ít nhất một occurrence mới của `zone_intrusion:{zone_id}` trong vùng đang chạy.
  - Tracking không reset khi cấu hình vùng thay đổi trong cùng monitoring session; dedup và re-arm được quản lý độc lập theo session, track và `zone_id`.
  - Một frame có vi phạm mới tại nhiều vùng mở một review tổng hợp; xác nhận được lưu nguyên tử thành event riêng cho từng vùng, dùng chung snapshot đã làm mờ và không làm mất occurrence nào.
  - Contract mới là additive: client một vùng hiện tại tiếp tục hoạt động trong giai đoạn tương thích; field scalar cũ chỉ là summary và client đa vùng dùng `zones`, `zone_memberships` và `zone_results`.
  - Existing person/PPE inference tiếp tục chạy đúng một lần cho mỗi frame bất kể số vùng; US-27 không thay đổi model, cấu hình, rule, cảnh báo, UI hoặc persistence PPE hiện hành.
  - Có unit, contract, component và end-to-end test cho 0/1/nhiều vùng không giới hạn bằng hằng số, vùng stopped/running hỗn hợp, từ chối giao/chạm/chứa polygon, nhiều người, reconfigure, reconnect, dedup, batch review và payload không hợp lệ.
- Task:
  1. [x] Khóa phạm vi: không giới hạn số vùng ở cấp sản phẩm, cấm vùng giao/chạm/chứa nhau, grouped review/event theo vùng và không thay đổi PPE.
  2. [x] Thiết kế persistence/migration và REST collection cho cấu hình vùng theo `camera_id`, có revision để chống ghi đè cấu hình mới hơn.
  3. [x] Mở rộng WebSocket/REST inference, rule engine và occurrence key để trả kết quả theo từng vùng mà chỉ chạy model một lần mỗi frame.
  4. [x] Xây zone editor đa vùng với nút **Tạo vùng**, drawing mode bốn điểm, Canvas overlay, trạng thái draft/lưu và typed transport trên frontend.
  5. [x] Thêm atomic event-batch persistence, regression contract cũ và automated contract/component tests; browser UAT bằng video nhiều vùng nằm ở release gate.

### US-28 — Thay SH17 bằng `wesjos/Yolo-hard-hat-safety-vest`

> Cập nhật sau implementation (2026-08-13): quyết định Product Owner mới hơn đã chọn `yolo11m_safety.pt` làm detector runtime duy nhất. Class `person` ID `3` thay YOLO11 cho person canonical/ByteTrack/zone và cùng call `[0,3,4]` trả `hat`/`vest`; các boundary hai-model bên dưới được giữ như lịch sử phạm vi ban đầu của US-28.

> Với vai trò cán bộ an toàn, tôi muốn hệ thống dùng model `wesjos/Yolo-hard-hat-safety-vest` với đúng ba lớp `person`, `hat` và `vest`, để phát hiện mũ và áo phản quang theo một model PPE phù hợp với phạm vi prototype.

- Ưu tiên / trạng thái: **P0 / Đã triển khai cho prototype; US-13 final evaluation vẫn là production gate**
- Owner chính: `vision`; thay đổi contract/rule là công việc phối hợp `backend` và `frontend`.
- Phụ thuộc: US-03, US-04, US-07, US-08, US-12, US-13 và US-27.
- Thay thế có kiểm soát: model SH17 chỉ bị thay ở luồng PPE/object detection và annotation liên quan. Person detector YOLO11 hiện hành vẫn là nguồn chuẩn cho `foot_point`, zone rule và ByteTrack; việc thay luôn YOLO11 bằng class `person` của model mới là một quyết định riêng, không nằm trong US này.

#### Phạm vi model và semantics

- Artifact được pin từ nguồn `wesjos/Yolo-hard-hat-safety-vest` bằng revision, file weight, SHA-256, giấy phép, provenance và device/runtime đã kiểm chứng. Chưa đủ các bằng chứng này thì backend không được bật model trong môi trường dùng chung.
- Adapter vision chỉ phát hành ba `class_name` chính xác: `person`, `hat`, `vest`. Khởi động hoặc inference phải fail rõ ràng nếu metadata/class mapping của checkpoint không đúng; không đổi tên, đoán thêm lớp, hoặc ánh xạ lớp không rõ nghĩa vào luật an toàn.
- Model mới chạy tối đa một lần cho mỗi frame để lấy PPE/object observations. YOLO11 person detection và ByteTrack hiện hành tiếp tục chạy một lần theo flow US-03/US-08; association phải gắn `hat`/`vest` của model mới vào đúng person canonical trước khi backend áp rule.
- Khi hai model cùng trả `person`, REST/WebSocket chỉ phát hành một person canonical từ YOLO11 để không tạo box, `foot_point` hoặc `track_id` trùng. `person` của model PPE chỉ là tín hiệu hỗ trợ association và không được thay thế person canonical trong US này.
- Sau cutover, SH17 không được nạp, gọi hoặc trả qua REST/WebSocket/canvas/snapshot annotation. Artifact SH17 chỉ có thể còn trong lịch sử release hoặc backup đã kiểm soát, không phải dependency runtime.

#### Hành vi PPE mới

- Profile PPE mới chỉ có hai requirement: `hat_required` và `vest_required`; cả hai mặc định OFF cho camera–zone mới.
- `people[].ppe` trong contract PPE mới chỉ gồm `hat` và `vest`, mỗi mục có `status` là `present`, `missing` hoặc `unknown`, cùng confidence nullable. `missing_required_ppe` chỉ chứa `hat` và/hoặc `vest`.
- `hat` hoặc `vest` chỉ là `missing` khi person đạt ngưỡng confidence, association hợp lệ và không có detection PPE tương ứng. Requirement OFF không tạo alert nhưng không tắt inference.
- Rule key mới là `missing_ppe:hat` và `missing_ppe:vest`; occurrence/dedup theo US-08 tiếp tục hoạt động độc lập theo person, track và rule. Event cũ chứa `missing_ppe:helmet`, `missing_ppe:safety_glasses` hoặc `missing_ppe:gloves` chỉ được đọc như audit lịch sử, không bị đổi hoặc xóa.
- Kính và găng không còn là capability, requirement hoặc alert của profile mới. Không được trả `unknown` cho chúng để giả vờ model vẫn hỗ trợ; UI, rule, metric và dữ liệu mới phải thể hiện rõ chúng không thuộc profile `hat`/`vest`.

#### Contract, persistence và UI

- Đây là thay đổi có chủ ý từ profile PPE ba loại của US-07 sang profile hai loại. Trước khi code, Product Owner phải phê duyệt versioned REST/WebSocket/Pydantic/TypeScript contract và migration cấu hình; không được âm thầm xóa hay đổi nghĩa field hiện hành.
- Contract PPE phiên bản mới trả detection chỉ có `person`, `hat`, `vest`; person PPE chỉ có `hat`, `vest`; rule echo đúng hai requirement đã persist. Client profile cũ phải được migrate có kiểm soát hoặc nhận lỗi version rõ ràng, không được tiếp tục tạo alert kính/găng bằng output model mới.
- Migration phải giữ nguyên `ppe_requirements`, event, occurrence và audit lịch sử. `helmet_required` có thể được đề xuất map sang `hat_required` sau khi Product Owner xác nhận tương đương ngữ nghĩa; `safety_glasses_required` và `gloves_required` phải bị retire cho rule mới nhưng vẫn giữ được lịch sử.
- Frontend chỉ hiển thị box/list/badge cho `person`, `hat`, `vest`, có hai công tắc **Mũ bảo hộ** và **Áo phản quang** cùng luồng lưu cấu hình rõ ràng. Nhãn box giữ nguyên tên model `hat`/`vest`; text UI tiếng Việt có thể diễn giải tương ứng.
- Zone intrusion, multi-zone, `foot_point`, `track_id`, grouped review và event batch không đổi semantics. PPE model mới không được làm model/tracker chạy lặp theo số zone.

#### Privacy bắt buộc

- Model ba lớp không có `face`, `face-guard`, `face-mask` hoặc `head`, vì vậy không thể thay thế detector làm mờ danh tính của US-12.
- Trước khi bật lưu snapshot cho review/event bằng profile mới, phải có một redaction provider độc lập, được pin và benchmark riêng, hoặc một phương án redaction được Product Owner phê duyệt. Provider này không được làm xuất hiện lớp privacy trong public PPE contract.
- Pipeline vẫn bắt buộc `redact → annotate → persist`, xử lý ảnh thô chỉ trong memory và fail-closed: redaction lỗi hoặc không đủ candidate theo policy thì không được lưu event/snapshot. Không được giữ SH17 chỉ để lách yêu cầu thay model mà không ghi rõ provider privacy riêng.

#### Acceptance criteria

- Model artifact, revision, checksum, license/provenance, exact class mapping ba lớp và startup validation được ghi trong `models/README.md`; checkpoint sai mapping không thể khởi động inference PPE.
- Mọi REST/WebSocket result của profile mới chỉ có detection `person`, `hat`, `vest`; lớp lạ, dữ liệu rỗng, confidence thấp và không có person đều có response an toàn, typed và được test.
- Requirement, rule engine, occurrence key, event detail và UI chỉ hỗ trợ `hat`/`vest`; ON/OFF × present/missing/unknown, một/nhiều person, một/nhiều PPE, PPE không associate và retry/dedup đều vượt test.
- Person detection, `foot_point`, zone ON/OFF, multi-zone, ByteTrack, reconnect và grouped review của US-03/04/08/27 vượt regression; model PPE mới chỉ được gọi một lần mỗi frame, không theo số zone.
- Migration giữ event/audit và cấu hình lịch sử đọc được; contract version/profile cũ không thể âm thầm tạo alert kính/găng sau cutover.
- Snapshot privacy vẫn được redact, annotate và persist theo US-12 bằng provider đã được xác nhận; test gồm không có candidate, một/nhiều identity region, lỗi redactor và cleanup transaction.
- US-13 có dataset/calibration/final evaluation cho person, `hat`, `vest`, qualified absence, association, zone occurrence và tracking; báo cáo nêu model revision/checksum, threshold, precision/recall, false alarm và latency p50/p95 trước khi dùng ngoài demo.
- `make check`, focused vision/backend/frontend tests, migration upgrade/downgrade và smoke test `make setup` rồi `make run` đều đạt trên Python được hỗ trợ.

#### Task

1. [x] Xác minh model card/artifact `wesjos/Yolo-hard-hat-safety-vest`, pin revision/weight/checksum/license, kiểm tra chính xác ba lớp và thêm model registry/runtime startup validation.
2. [x] Thay adapter SH17 bằng facade vision chỉ phát hành observation `person`/`hat`/`vest`; cập nhật association với person canonical, threshold/configuration và benchmark một lần inference PPE mỗi frame.
3. [x] Chốt và phê duyệt contract PPE version mới, migration từ profile helmet/glasses/gloves sang hat/vest, compatibility/retirement policy và audit retention trước khi sửa API hoặc database.
4. [x] Cập nhật deterministic PPE rule, occurrence keys, persistence/API/wire types và frontend requirement controls, detection list, canvas/review overlay theo profile hai loại.
5. [x] Thay dependency redaction SH17 bằng provider privacy độc lập hoặc phương án đã được duyệt; giữ fail-closed, in-memory redaction, annotation sau redaction và cleanup.
6. [x] Mở rộng template US-13 sang `hat`/`vest`, chạy focused vision/backend/frontend, migration, privacy và CPU smoke benchmark. Final custom-dataset evaluation, browser UAT và target-device benchmark tiếp tục là gate bắt buộc trước pilot/production.

### Cổng nghiệm thu MVP cuối tuần hiện tại

- Core flow chạy trọn vẹn sau đăng nhập đúng vai trò: tải video hoặc ảnh → mô tả/confirm rule → tạo một hoặc nhiều vùng → person + mũ/áo phản quang + track → áp trạng thái máy theo vùng → HITL → snapshot blur → event/audit → dashboard.
- Một vi phạm liên tục chỉ tạo một event; false alarm được lưu để đo; không lưu snapshot chưa làm mờ.
- Precision, recall, false-alarm rate và latency có báo cáo tái lập.
- `make check`, production build, migration, deploy smoke test và UAT đạt trên cùng release commit.
- US-20, US-24 và US-27 đạt acceptance criteria trong MVP; US-19 được Product Owner nghiệm thu và là điểm bắt đầu kế hoạch nâng cao 5 tuần.

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

### US-27 — Trang AI auto-label dữ liệu phục vụ dataset

> Với vai trò nhóm phát triển dataset, tôi muốn có một trang riêng dùng AI để đề xuất nhãn cho ảnh và frame video mô phỏng, để tăng tốc chuẩn bị custom dataset nhưng vẫn giữ ground truth đã được con người kiểm duyệt.

- Ưu tiên / trạng thái: **P1 nâng cao / Chưa làm**
- Phụ thuộc: US-07, US-08, US-12, US-13, US-20
- Acceptance criteria:
  - Có workspace riêng, chỉ người dùng được phân quyền phù hợp mới truy cập; workspace không trộn với màn hình monitor/review sự cố đang vận hành.
  - Người dùng có thể tải ảnh hoặc trích frame từ video mô phỏng có quyền sử dụng; hệ thống chạy model hiện có để đề xuất bounding box `person`, trạng thái PPE mũ/kính/găng và `track_id` chỉ trong phạm vi video annotation.
  - UI cho phép duyệt, sửa, thêm, xóa hoặc từ chối từng nhãn AI; nhãn chỉ trở thành `human_verified` sau thao tác xác nhận rõ ràng của người dùng.
  - Mỗi annotation lưu provenance tối thiểu: media/frame ID, loại nhãn, giá trị/bounding box, confidence, model/checksum, thời điểm tạo và reviewer/quyết định; không lưu hay suy luận danh tính, khuôn mặt hoặc đặc trưng sinh trắc học.
  - Có thể xuất dataset manifest phiên bản hóa tương thích protocol US-13; manifest phân biệt rõ `ai_suggested`, `human_verified` và `rejected`, kèm checksum. Final evaluation chỉ nhận nhãn `human_verified` và không dùng nhãn chưa duyệt làm ground truth.
  - Khi AI inference, upload hoặc lưu annotation lỗi, UI hiển thị lỗi có thể xử lý; không tạo annotation một phần hoặc làm mất nhãn đã được reviewer lưu trước đó.
  - Có test cho quyền truy cập, luồng accept/edit/reject, provenance/export, và giới hạn không nhận diện danh tính.
- Task:
  1. Chốt annotation schema, class taxonomy, permission matrix, retention/quyền sử dụng media và format manifest với protocol US-13.
  2. Xây API/service dùng vision facade hiện có để tạo AI suggestion, lưu version/provenance và xuất manifest; không để frontend gọi model trực tiếp hoặc để vision truy cập database.
  3. Xây trang frontend độc lập cho upload/frame selection, annotation canvas và review queue; bổ sung route guard, trạng thái loading/empty/error và accessibility cơ bản.
  4. Viết unit, API và component/E2E tests cho lifecycle annotation, authorization, export checksum và regression privacy.

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
