# Tài liệu kiểm thử và bảo đảm chất lượng sản phẩm

## 1. Thông tin tài liệu

- **Dự án:** P-047 – AI Agent giám sát an toàn PPE và khu vực nguy hiểm bằng Computer Vision.
- **Phiên bản tài liệu:** 1.0.
- **Ngày cập nhật:** 01/09/2026.
- **Phạm vi:** Frontend React/TypeScript, Backend FastAPI, Vision, PostgreSQL, REST/WebSocket contracts, media, snapshot, Docker và quy trình CI.
- **Mục đích:** Quy định cách kiểm thử, điều kiện chấp nhận và bằng chứng chất lượng trước khi tích hợp hoặc phát hành sản phẩm.

Tài liệu này mô tả cả kế hoạch kiểm thử và trạng thái chất lượng hiện tại. Các test trong source code, schema, migration và CI workflow là bằng chứng thực thi cuối cùng. Khi tài liệu và executable test khác nhau, kết quả của executable test tại đúng commit được kiểm tra là nguồn xác nhận hiện hành.

## 2. Mục tiêu kiểm thử

Hoạt động kiểm thử của P-047 cần bảo đảm các mục tiêu sau:

1. Người dùng đăng nhập đúng vai trò và chỉ truy cập được dữ liệu thuộc phạm vi được phân công.
2. Hệ thống phát hiện người, mũ và áo phản quang theo contract `hat_vest_v1`.
3. Xâm nhập vùng cấm được đánh giá đúng theo polygon và ngưỡng giao với bounding box người.
4. Cảnh báo thiếu PPE chỉ được áp dụng khi yêu cầu PPE đang bật và máy ở trạng thái phù hợp.
5. Tracking và occurrence không tạo nhiều cảnh báo cho cùng một người trong cùng phiên ngoài quy tắc đã phê duyệt.
6. Human-in-the-Loop không mất sự kiện, không submit lặp và bảo toàn quyết định của con người.
7. Snapshot được làm mờ danh tính trước khi lưu; lỗi privacy phải fail closed.
8. Live Monitor, Camera Detail, Audit và Area Manager đồng bộ cùng trạng thái sự kiện từ backend.
9. REST, WebSocket, ORM và migration duy trì tương thích khi contract chưa được phê duyệt thay đổi.
10. Frontend có thể lint, type-check, test và build production thành công.
11. Backend và Vision vượt qua lint, format và các test bắt buộc.
12. Docker image có thể build lặp lại từ dependency đã khóa và không chứa bí mật runtime.

## 3. Phạm vi kiểm thử

### 3.1. Chức năng trong phạm vi

- Đăng nhập, session, đổi mật khẩu bắt buộc và đăng xuất.
- Quản trị tài khoản theo ba vai trò: `system_admin`, `safety_manager`, `area_manager`.
- Gán camera cho Area Manager và giới hạn dữ liệu theo camera hoặc khu vực legacy.
- Liên kết, kiểm tra trạng thái và ngắt liên kết Telegram.
- Upload, xác thực, liệt kê, phát và xóa media theo quyền.
- Bốn camera logic `cam_1` đến `cam_4` và tính duy nhất của media assignment.
- Cấu hình trạng thái máy, yêu cầu mũ/áo và nhiều vùng cấm.
- Run, Replay và vòng đời monitoring session.
- Inference người/PPE, ByteTrack, temporal smoothing và portable tracking state.
- Đánh giá vùng cấm, debounce, occurrence và chống cảnh báo trùng.
- Pending-event inbox, HITL review, event audit và thống kê.
- Làm mờ danh tính, annotation và lưu snapshot.
- WebSocket camera detection và đồng bộ trạng thái giữa các màn hình.
- Operational metrics, readiness và các kiểm tra vận hành cơ bản.
- Migration PostgreSQL, Docker build và smoke test cục bộ khi môi trường cho phép.

### 3.2. Ngoài phạm vi MVP hiện tại

- Camera nhà máy thật và luồng RTSP production.
- Tích hợp PLC hoặc tự động dừng máy.
- Nhận dạng danh tính hoặc theo dõi một người xuyên camera.
- Cam kết độ chính xác trên mọi điều kiện nhà máy khi chưa hoàn thành dataset calibration.
- Kiểm thử tải production trên nhiều stream đồng thời ở quy mô lớn.
- Penetration test độc lập bởi đơn vị bảo mật bên ngoài.

Các nội dung ngoài phạm vi không được xem là đã bảo đảm chỉ vì unit test hoặc demo cục bộ thành công.

## 4. Chiến lược kiểm thử

### 4.1. Kiểm tra tĩnh

Kiểm tra tĩnh được thực hiện trước test chức năng để phát hiện lỗi cú pháp, type và style sớm:

- Ruff lint cho `src/`, `backend/` và `vision/`.
- Ruff format check cho các thư mục Python trên.
- ESLint cho toàn bộ frontend.
- TypeScript project build/type-check cho frontend.
- Kiểm tra whitespace và conflict marker bằng `git diff --check`.

Một thay đổi không được coi là sẵn sàng tích hợp khi còn lint error, type error hoặc format error mới. Warning đã biết phải được ghi rõ, không được trình bày như một kết quả hoàn toàn sạch.

### 4.2. Unit test

Unit test kiểm tra logic nhỏ, có đầu vào xác định và hạn chế phụ thuộc mạng hoặc dịch vụ ngoài:

- Vision: face detection, privacy pipeline, tracking, PPE association và tracking-state codec.
- Backend service: rule evaluation, debounce, occurrence lifecycle, statistics và notification orchestration.
- Frontend component: render theo role, thao tác form, modal review, event detail và trạng thái camera.
- Frontend utility/API client: serialization, request options, cache policy và event reconciliation.

Unit test phải bao phủ cả trường hợp đúng, biên và lỗi. Đối với hình học vùng, cần có dữ liệu dưới ngưỡng, đúng ngưỡng và trên ngưỡng. Đối với state machine, cần kiểm tra cả chuyển trạng thái hợp lệ và thao tác lặp idempotent.

### 4.3. Integration test

Integration test xác nhận các ranh giới giữa module:

- FastAPI route với Pydantic schema và service.
- Service với SQLAlchemy model và PostgreSQL.
- Backend với local Vision facade hoặc remote Vision Worker contract.
- Event persistence với snapshot storage và rollback.
- Auth/session với quyền truy cập resource.
- Frontend component với mock transport và response contract.
- Migration upgrade/downgrade với schema kỳ vọng.

PostgreSQL là database được hỗ trợ chính thức. Test SQLite chỉ được giữ cho các migration legacy cụ thể và không được dùng để chứng minh production database contract.

### 4.4. Contract test

Contract test đặc biệt quan trọng vì hệ thống có nhiều ranh giới runtime:

- REST request/response giữa frontend và backend.
- WebSocket payload cho inference và camera event notification.
- `safety_vision_v1` và `safety_vision_v2` giữa backend và Vision Worker.
- Portable state `bytetrack_ppe_state_v1`.
- ORM schema và Alembic migration.
- Event audit context và snapshot metadata.

Thay đổi field, enum, trạng thái, database constraint hoặc ý nghĩa nghiệp vụ phải có regression test tương ứng. Breaking change chỉ được thực hiện khi có phê duyệt rõ ràng và kế hoạch tương thích hoặc migration.

### 4.5. End-to-end và smoke test

Luồng E2E tối thiểu cần xác nhận:

1. Đăng nhập bằng tài khoản hợp lệ.
2. Upload hoặc chọn media đã sẵn sàng.
3. Gán media cho camera.
4. Cấu hình trạng thái máy, PPE và vùng cấm.
5. Bắt đầu phiên Run hoặc Replay.
6. Nhận detection qua WebSocket.
7. Tạo pending event sau điều kiện debounce.
8. Hiển thị sự kiện trong Live Monitor và Camera Detail.
9. Review thành `acknowledged` hoặc `false_alarm`.
10. Xác nhận Event Audit, thống kê và quyền Area Manager được cập nhật đúng.
11. Xác nhận snapshot đã được bảo vệ danh tính.

Docker smoke test cần xác nhận container khởi động, migration chạy thành công, endpoint ứng dụng trả phản hồi và `/health` phản ánh đúng trạng thái phụ thuộc thay vì luôn báo healthy.

### 4.6. Kiểm thử mô hình và dữ liệu

Model test không chỉ kiểm tra code có chạy hay không. Đánh giá mô hình cần sử dụng tập dữ liệu được khóa phiên bản với ground truth và manifest rõ ràng.

Các nhóm tình huống tối thiểu gồm:

- Có người, không có người và nhiều người.
- Có đủ PPE, thiếu mũ, thiếu áo và thiếu cả hai.
- PPE nằm gần người đúng và nằm gần người khác.
- Người trong vùng, ngoài vùng, chạm biên và giao vùng ở các mức dưới/đúng/trên ngưỡng.
- Người bị che khuất, rời khung hình rồi xuất hiện lại.
- Ánh sáng yếu, thay đổi góc nhìn, motion blur và kích thước người nhỏ.
- Ảnh và video ở nhiều độ phân giải.

Chỉ số nên báo cáo gồm precision, recall, F1 theo lớp, false positive/false negative theo kịch bản, độ trễ mean/P50/P95 và throughput. RTT của giao diện so sánh worker không được dùng thay cho benchmark model có kiểm soát.

## 5. Môi trường kiểm thử

### 5.1. Phiên bản nền tảng

- Python 3.11.
- Node.js 22 trong CI.
- React 19, TypeScript và Vite 6.
- Pytest cho Python test suites.
- Vitest, Testing Library và jsdom cho frontend.
- Ruff cho lint và format Python.
- ESLint cho frontend.
- PostgreSQL là relational database chính thức.
- Docker/Buildx cho kiểm tra image production.

Dependency phải được cài từ `uv.lock` và `frontend/package-lock.json`. CI dùng `uv sync --frozen` và `npm ci` để tránh tự động thay đổi phiên bản trong lúc kiểm thử.

### 5.2. Nguyên tắc dữ liệu test

- Không sử dụng ảnh khuôn mặt thật hoặc dữ liệu nhạy cảm nếu không có quyền phù hợp.
- Ưu tiên fixture tổng hợp, media mẫu được phép sử dụng và snapshot đã làm mờ.
- Test không được phụ thuộc thứ tự chạy hoặc dữ liệu còn lại từ lần chạy trước.
- Mỗi test tạo resource phải tự cleanup hoặc dùng transaction/fixture cô lập.
- Không ghi token, mật khẩu, URL có credential hoặc raw frame vào log kiểm thử.
- Test Telegram và S3 mặc định phải mock provider; test thật chỉ chạy trong môi trường được kiểm soát.

## 6. Ma trận kiểm thử chức năng trọng yếu

| Mã | Chức năng | Tình huống kiểm thử chính | Kết quả mong đợi | Mức ưu tiên |
|---|---|---|---|---|
| TC-AUTH-01 | Đăng nhập | Đúng/sai mật khẩu, session hết hạn | Chỉ thông tin hợp lệ tạo session; lỗi không rò rỉ dữ liệu | P0 |
| TC-AUTH-02 | Phân quyền | Ba role truy cập cùng một API/màn hình | Chỉ role được phép nhận dữ liệu và thao tác | P0 |
| TC-AUTH-03 | Area Manager | Tài khoản được gán một số camera | Chỉ xem sự kiện/thống kê của camera được gán | P0 |
| TC-MEDIA-01 | Upload media | Đúng/sai loại file, quá kích thước, file hỏng | File hợp lệ thành READY; file lỗi bị từ chối an toàn | P0 |
| TC-CAM-01 | Gán media | Một asset được gán cho hai camera | Backend từ chối xung đột assignment | P0 |
| TC-CAM-02 | Run/Replay | Chạy mới và replay một camera | Session ID mới, playback/tracking được reset đúng | P0 |
| TC-PPE-01 | Đủ PPE | Người có mũ và áo khi máy chạy | Không tạo cảnh báo thiếu PPE | P0 |
| TC-PPE-02 | Thiếu PPE | Thiếu mũ hoặc áo đủ số frame | Tạo đúng violation sau confirmation/debounce | P0 |
| TC-PPE-03 | Máy dừng | Người thiếu PPE khi máy dừng | Không tạo cảnh báo PPE | P0 |
| TC-ZONE-01 | Xâm nhập vùng | Giao polygon lớn hơn 20% box người | Tạo violation vùng sau debounce áp dụng | P0 |
| TC-ZONE-02 | Biên vùng | Giao đúng 20% hoặc chỉ chạm biên | Không tính là ở trong vùng | P0 |
| TC-ZONE-03 | Trạng thái máy | Người trong vùng khi máy dừng | Vẫn tạo violation vùng | P0 |
| TC-TRACK-01 | Chống trùng | Một người vi phạm liên tục | Không tạo nhiều event ngoài contract phiên | P0 |
| TC-TRACK-02 | Track handoff | Người bị che khuất và đổi Track ID gần vị trí cũ | Occurrence hợp lệ được bảo toàn | P1 |
| TC-HITL-01 | Review | Chọn VIOLATE hoặc NORMAL | Cùng event chuyển trạng thái đúng một lần | P0 |
| TC-HITL-02 | Submit lặp | Double click hoặc retry request | Không tạo bản ghi hay notification trùng | P0 |
| TC-PRIV-01 | Làm mờ mặt | Phát hiện được khuôn mặt | Mọi khuôn mặt được blur trước khi persist | P0 |
| TC-PRIV-02 | Detector lỗi | YuNet lỗi hoặc không tìm thấy mặt | Dùng person fallback hoặc từ chối persist theo fail-closed | P0 |
| TC-SYNC-01 | Event realtime | Event mới được persist trong lúc socket hoạt động | Monitor và Camera Detail tải được cùng event | P0 |
| TC-SYNC-02 | Mất kết nối | Socket disconnect rồi reconnect | Reconciliation lấy lại event bị bỏ lỡ, không nhân đôi | P1 |
| TC-SYNC-03 | Review đa màn hình | Review ở Monitor khi Audit/Detail đang mở | Các view tải lại trạng thái authoritative | P0 |
| TC-AUDIT-01 | Decision audit | Review một event | Context quyết định bất biến và có actor/timestamp | P0 |
| TC-TELE-01 | Telegram | Chuyển event sang acknowledged | Notification được queue đúng một lần | P1 |
| TC-TELE-02 | Liên kết tài khoản | Nhiều deep link còn hạn | Một link hợp lệ kết nối và thu hồi challenge còn lại | P1 |
| TC-MIG-01 | Migration | Upgrade database hiện có | Không mất event, user, camera hoặc audit data | P0 |
| TC-WORKER-01 | Remote Vision | Timeout/sai version/sai payload | Backend fail closed, không tạo kết quả normal giả | P0 |
| TC-STATE-01 | Portable state | Revision trùng hoặc payload quá giới hạn | CAS/retry theo contract hoặc fail closed | P0 |
| TC-UI-01 | Frontend build | Lint, type-check, test, build | Không có error và tạo được production bundle | P0 |

## 7. Cách chạy kiểm thử

### 7.1. Quality gate đầy đủ

Từ thư mục gốc repository:

```bash
make check
```

Lệnh này chạy theo thứ tự:

1. Ruff lint.
2. Ruff format check.
3. Frontend lint.
4. Frontend type-check.
5. Frontend test.
6. Frontend production build.
7. Root Python tests.
8. Backend và Vision tests.

### 7.2. Chạy từng nhóm kiểm thử

```bash
make lint
make format
make frontend-lint
make frontend-type-check
make frontend-test
make frontend-build
make test
```

Chạy trực tiếp bằng công cụ:

```bash
uv run ruff check src/ backend/ vision/
uv run ruff format --check src/ backend/ vision/
uv run pytest tests/ -v --tb=short
uv run pytest backend/tests/ vision/tests/ -v --tb=short
npm --prefix frontend run lint
npm --prefix frontend run type-check
npm --prefix frontend run test
npm --prefix frontend run build
```

### 7.3. Chạy test tập trung

Khi sửa một chức năng, cần chạy test gần thay đổi trước, sau đó chạy quality gate rộng hơn. Ví dụ:

```bash
uv run pytest backend/tests/test_events.py -v
uv run pytest backend/tests/test_violation_tracking.py -v
uv run pytest vision/tests/test_privacy_pipeline.py -v
npm --prefix frontend run test -- EventDetailDialog.test.tsx
```

Tên file phải được chọn theo phần mã thực sự thay đổi. Focused test giúp phản hồi nhanh nhưng không thay thế full suite trước khi merge.

### 7.4. Lưu ý khi chạy trên Windows

`Makefile` sử dụng một số cú pháp shell kiểu Bash. Trong trạng thái ghi nhận gần nhất, `make check` trên Windows có thể dừng khi Bash cố chạy `.venv/Scripts/pytest` với lỗi `Permission denied`. Khi gặp trường hợp này, cần chạy trực tiếp bằng Python của virtual environment:

```powershell
.venv\Scripts\python.exe -m pytest tests -v --tb=short
.venv\Scripts\python.exe -m pytest backend/tests vision/tests -v --tb=short
.venv\Scripts\python.exe -m ruff check src backend vision
.venv\Scripts\python.exe -m ruff format --check src backend vision
```

Đây là khác biệt của test launcher trên máy local, không phải lý do để bỏ qua Python tests. CI Linux vẫn là quality gate bắt buộc trước khi merge vào `main`.

## 8. Quality gate trong CI

CI chạy khi có pull request vào `main` hoặc push lên `main`. Các job chính gồm:

| Job | Nội dung |
|---|---|
| Backend and vision lint | Cài dependency khóa bằng uv; chạy Ruff lint và format check |
| Root Python tests | Chạy cross-cutting tests trong `tests/` |
| Backend and vision tests | Chạy toàn bộ `backend/tests/` và `vision/tests/` |
| Frontend | Cài bằng `npm ci`; chạy lint, type-check, test và build |
| Docker | Build image khi Docker input thay đổi; chỉ push image trên sự kiện được phép |

CI dùng Python 3.11, Node.js 22 và Git LFS cho các job cần model. Các job phải sử dụng dependency đã khóa để kết quả có thể tái lập.

Pull request không được merge nếu job bắt buộc thất bại. Việc build được Docker image không đồng nghĩa ứng dụng đã sẵn sàng production; release còn cần migration, dependency readiness, health check và smoke evidence.

## 9. Tiêu chí chấp nhận và hoàn thành

### 9.1. Tiêu chí cho một thay đổi thông thường

Một thay đổi được xem là sẵn sàng review khi:

- Acceptance criteria của task đã được đáp ứng.
- Có focused test cho hành vi mới hoặc regression đã sửa.
- Không làm thay đổi contract ngoài phạm vi được duyệt.
- Focused tests pass.
- Lint, format và type-check liên quan pass.
- Không có secret, raw identity data hoặc file runtime ngoài ý muốn trong diff.
- Tài liệu và cấu trúc dự án được cập nhật nếu thay đổi boundary/file layout.

### 9.2. Tiêu chí trước khi merge

- Full CI bắt buộc pass tại commit dự kiến merge.
- Không còn test failure mới.
- Failure có sẵn phải được chứng minh là ngoài phạm vi, ghi issue/known issue và không được che khuất bằng cách xóa test.
- Migration mới phải có test upgrade, tính tương thích dữ liệu và rollback phù hợp.
- REST/WebSocket/provider contract thay đổi phải có test ở cả producer và consumer.
- Review bảo mật và privacy phải được thực hiện cho thay đổi liên quan media, snapshot, auth hoặc notification.

### 9.3. Tiêu chí trước khi release

- CI tại revision phát hành pass hoàn toàn.
- Docker image được build từ đúng revision và dependency khóa.
- PostgreSQL reachable và migration được áp dụng thành công.
- Media storage/volume có quyền đọc ghi cần thiết.
- Model artifact đúng checksum và load thành công.
- `/health` phản ánh trạng thái sẵn sàng thực tế.
- Smoke test upload/list/playback và luồng sự kiện quan trọng pass.
- Có revision/deployment bất biến đã biết để rollback.
- Không deploy Railway nếu chưa có yêu cầu và quyền phát hành rõ ràng.

## 10. Trạng thái kiểm thử gần nhất

Trạng thái dưới đây được tổng hợp từ kết quả được ghi nhận ngày 31/08/2026, không phải cam kết rằng mọi worktree hoặc commit về sau giữ nguyên kết quả này.

### 10.1. Kết quả đã xác nhận

- Frontend full suite đạt **116/116 tests pass** ở lần ghi nhận mới nhất.
- Frontend type-check pass.
- Frontend production build pass.
- Frontend lint không có error; còn một warning React Hooks đã biết tại `StreamViewer.tsx:155`.
- Focused Telegram UI regression đạt 1/1.
- Các lần kiểm tra focused trước đó cho Camera Violation Log, Event Detail, Monitor, Area Manager và event synchronization đều pass theo phạm vi thay đổi tương ứng.
- `git diff --check` pass cho các thay đổi tài liệu ngày 01/09/2026.

### 10.2. Giới hạn và lỗi đã biết

- Trên Windows, `make check` có thể bị chặn bởi cách Bash gọi `.venv/Scripts/pytest`; cần chạy Python suites trực tiếp bằng `.venv\Scripts\python.exe -m pytest`.
- Kết quả Python gần nhất ghi nhận **31/32 root tests pass** và **299/316 backend/vision tests pass** khi chạy trực tiếp.
- Các failure còn lại liên quan migration SQLite legacy, notification, debounce/PPE, audit/event batch, remote adapter và multi-zone. Đây là các lỗi contract/legacy đã biết, nhưng vẫn phải được xử lý hoặc có quyết định chấp nhận rõ ràng trước khi tuyên bố toàn bộ quality gate pass.
- PostgreSQL là contract hiện hành; failure của SQLite migration legacy cần được phân loại riêng, không được dùng để thay đổi production contract về SQLite fallback.
- Calibration model trên dữ liệu nhà máy đại diện vẫn là điều kiện cần trước khi đưa ra cam kết chất lượng ngoài phạm vi demo.

### 10.3. Đánh giá hiện tại

Frontend và các luồng UI trọng yếu có mức regression coverage tốt và build ổn định. Backend/Vision có test suite rộng nhưng chưa đạt trạng thái xanh hoàn toàn ở kết quả gần nhất. Vì vậy, sản phẩm có đủ bằng chứng cho MVP/demo theo các luồng đã kiểm tra, nhưng chưa nên tuyên bố toàn bộ repository đạt release quality cho production cho đến khi các failure còn lại được phân loại và xử lý.

## 11. Quy trình ghi nhận và xử lý lỗi

Mỗi lỗi kiểm thử cần ghi tối thiểu:

- Tiêu đề mô tả hành vi sai.
- Commit/revision và môi trường tái hiện.
- Điều kiện ban đầu và dữ liệu test.
- Các bước tái hiện.
- Kết quả mong đợi và kết quả thực tế.
- Log hoặc ảnh chụp đã loại bỏ dữ liệu nhạy cảm.
- Mức độ ưu tiên và ảnh hưởng người dùng.
- Test regression cần bổ sung.

Phân loại mức độ:

- **P0 – Critical:** Rò rỉ danh tính, vượt quyền, mất dữ liệu, sai quyết định an toàn nghiêm trọng, không thể khởi động hoặc migration phá hỏng dữ liệu.
- **P1 – High:** Luồng chính không hoạt động, cảnh báo bị mất/trùng, review sai trạng thái, camera hoặc media không vận hành được.
- **P2 – Medium:** Chức năng phụ sai, UI gây nhầm lẫn nhưng có workaround, lỗi hiệu năng chưa làm dừng luồng chính.
- **P3 – Low:** Lỗi trình bày nhỏ, nội dung hoặc tối ưu không ảnh hưởng kết quả nghiệp vụ.

P0 phải chặn merge và release. P1 mặc định chặn release trừ khi có quyết định chấp nhận rủi ro rõ ràng. P2/P3 phải được ghi nhận và lên kế hoạch, không nên ẩn bằng cách bỏ test.

## 12. Bằng chứng kiểm thử cần lưu

Đối với mỗi pull request hoặc lần phát hành, nhóm nên lưu:

- Link hoặc mã CI run gắn với commit SHA.
- Danh sách focused test đã chạy.
- Kết quả full suite và thời điểm chạy.
- Kết quả lint, format, type-check và build.
- Docker image tag/digest nếu có build release.
- Migration revision và kết quả áp dụng.
- Health/smoke evidence đã loại bỏ credential.
- Báo cáo benchmark nếu thay model hoặc pipeline inference.
- Known issues và quyết định chấp nhận rủi ro nếu có.

Không lưu raw frame, token, cookie, mật khẩu, presigned URL còn hiệu lực hoặc thông tin nhận dạng cá nhân trong test report.

## 13. Trách nhiệm của nhóm

- **Người triển khai:** Viết focused test, tự chạy kiểm tra liên quan và mô tả bằng chứng trong pull request.
- **Người review:** Kiểm tra acceptance criteria, ranh giới contract, privacy/security và chất lượng test.
- **Người phụ trách frontend:** Xác nhận lint, type-check, component/API tests và production build.
- **Người phụ trách backend:** Xác nhận route/service/database tests, migration và authorization.
- **Người phụ trách Vision:** Xác nhận model contract, tracking, PPE, privacy và benchmark có kiểm soát.
- **Người phát hành:** Chỉ phát hành revision đã qua quality gate, xác nhận readiness và chuẩn bị rollback.

Một người có thể đảm nhiệm nhiều vai trò trong nhóm nhỏ, nhưng không được bỏ qua bằng chứng tương ứng.

## 14. Checklist kiểm thử trước khi bàn giao

- [ ] Phạm vi và acceptance criteria đã được xác nhận.
- [ ] Test case mới hoặc regression test đã được bổ sung.
- [ ] Focused tests pass.
- [ ] Ruff lint và format check pass.
- [ ] Frontend lint và type-check pass.
- [ ] Frontend tests và production build pass.
- [ ] Root, backend và Vision tests pass hoặc failure đã được phân loại rõ.
- [ ] REST/WebSocket/database/provider contract vẫn tương thích.
- [ ] Auth, authorization và privacy được kiểm tra nếu có liên quan.
- [ ] Không có file runtime, snapshot hoặc secret ngoài ý muốn trong commit.
- [ ] Migration và rollback đã được kiểm tra nếu schema thay đổi.
- [ ] Docker build/smoke test đã chạy nếu thay đổi runtime image.
- [ ] Tài liệu và project structure đã được cập nhật nếu cần.
- [ ] CI gắn với commit bàn giao đã pass.
- [ ] Deployment chỉ được thực hiện khi có yêu cầu rõ ràng.

## 15. Kết luận

Chất lượng của P-047 được bảo đảm bằng nhiều lớp kiểm thử thay vì chỉ dựa vào độ chính xác của mô hình. Một cảnh báo an toàn chỉ đáng tin cậy khi model observation, tracking, rule engine, persistence, privacy, phân quyền, giao diện review và audit cùng hoạt động đúng.

Do đó, điều kiện hoàn thành của sản phẩm phải bao gồm cả test chức năng, test contract, test migration, kiểm tra privacy/security, build production và bằng chứng vận hành. Mọi kết luận “đã pass” phải gắn với revision và môi trường cụ thể; các lỗi đã biết phải được trình bày minh bạch cho đến khi được sửa hoặc có quyết định chấp nhận chính thức.
