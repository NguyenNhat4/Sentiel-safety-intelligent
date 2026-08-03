# User Story Backlog — MFG-20 PPE & Zone Safety Agent

Tài liệu này chuyển phạm vi prototype trong [`PRD.md`](PRD.md) thành danh sách user story và đối chiếu trạng thái với [`PROGRESS.md`](../PROGRESS.md) tại ngày 2026-08-03.

## Quy ước trạng thái

- **Hoàn thành:** `PROGRESS.md` xác nhận luồng chính đã được triển khai.
- **Hoàn thành một phần:** Đã có một phần luồng hoặc bản baseline, nhưng chưa đáp ứng đầy đủ kết quả mong đợi trong PRD.
- **Chưa làm:** Chưa có bằng chứng hoàn thành trong `PROGRESS.md`, hoặc được ghi rõ là bước tiếp theo/known issue.

## User story đã hoàn thành

### US-01 — Tải và phát video mô phỏng

**Là** cán bộ an toàn, **tôi muốn** tải và phát một video mô phỏng **để** giám sát tình huống an toàn trong prototype mà không cần camera nhà máy thật.

- Trạng thái: **Hoàn thành**
- Bằng chứng: Frontend đã hỗ trợ video cục bộ, Play/Stop và gửi frame trong lúc phát.
- Tiêu chí đã đạt:
  - Tải một video cục bộ.
  - Xem preview và điều khiển phát/dừng.
  - Frame được lấy mẫu để phân tích khi video đang phát.

### US-02 — Cấu hình một vùng nguy hiểm bằng bốn điểm

**Là** cán bộ an toàn, **tôi muốn** chấm bốn điểm trên video **để** xác định vùng cấm cần giám sát.

- Trạng thái: **Hoàn thành**
- Bằng chứng: Frontend đã có chỉnh sửa vùng bốn điểm theo tọa độ chuẩn hóa và hiển thị polygon trên Canvas.
- Tiêu chí đã đạt:
  - Chỉ bắt đầu inference đầy đủ khi đủ bốn điểm.
  - Có thể kéo, xóa và đặt lại vùng.
  - Vùng giữ đúng vị trí theo kích thước hiển thị video.

### US-03 — Phát hiện người gần realtime

**Là** cán bộ an toàn, **tôi muốn** hệ thống phát hiện người trong video **để** quan sát vị trí của họ so với vùng nguy hiểm.

- Trạng thái: **Hoàn thành**
- Bằng chứng: Backend đã tích hợp YOLO person detection; frontend gửi JPEG qua WebSocket ở mức 2 FPS và vẽ bounding box cùng foot point.
- Tiêu chí đã đạt:
  - Trả về detection có bounding box.
  - Hiển thị detection trên video.
  - Chỉ xử lý một frame tại một thời điểm để tránh dồn hàng đợi.

### US-04 — Kết hợp vùng nguy hiểm với trạng thái máy ON/OFF

**Là** cán bộ an toàn, **tôi muốn** cảnh báo xâm nhập chỉ kích hoạt khi máy đang chạy **để** tránh cảnh báo sai khi khu vực ở trạng thái an toàn.

- Trạng thái: **Hoàn thành**
- Bằng chứng: Backend đánh giá foot point với polygon; frontend chỉ dừng để review khi người ở trong vùng và `machine_state` là `running`.
- Tiêu chí đã đạt:
  - Vẫn phát hiện và vẽ người khi máy dừng.
  - Không yêu cầu review khi máy dừng.
  - Tạm dừng video và mở review khi người vào vùng lúc máy chạy.

### US-05 — Nhận cảnh báo và review gần realtime

**Là** cán bộ an toàn, **tôi muốn** nhận cảnh báo ngay khi phát hiện tình huống nguy hiểm **để** có thể đánh giá và phản ứng kịp thời.

- Trạng thái: **Hoàn thành** cho luồng baseline xâm nhập vùng.
- Bằng chứng: WebSocket inference, review state và hành vi tạm dừng video đã được triển khai; live smoke test được ghi nhận là đạt.
- Tiêu chí đã đạt:
  - Kết quả inference được trả về qua WebSocket.
  - Tình huống xâm nhập vùng khi máy chạy mở review.
  - Monitor vẫn hiển thị sau khi xử lý cảnh báo.

### US-06 — Lưu và xem nhật ký vi phạm đã xác nhận

**Là** cán bộ an toàn, **tôi muốn** lưu vi phạm thực tế và xem lại trong nhật ký **để** có bằng chứng phục vụ theo dõi an toàn.

- Trạng thái: **Hoàn thành** cho luồng baseline.
- Bằng chứng: REST event persistence, snapshot, SQLite cục bộ và màn hình “Nhật ký vi phạm” đã được triển khai.
- Tiêu chí đã đạt:
  - Quyết định “Vi phạm thực tế” tạo event đã acknowledge.
  - Event đã xác nhận xuất hiện trong nhật ký.
  - False alarm không xuất hiện như một cảnh báo chính thức.

## User story hoàn thành một phần

### US-07 — Phát hiện áo phản quang bằng model PPE

**Là** cán bộ an toàn, **tôi muốn** hệ thống nhận biết người có mặc áo phản quang hay không **để** phát hiện vi phạm PPE.

- Trạng thái: **Hoàn thành một phần**
- Đã có: Heuristic màu HSV vùng thân người cho controlled demo và trường kết quả safety-shirt trong inference.
- Còn thiếu: Thay heuristic bằng model PPE đã huấn luyện và xác minh class áo phản quang.
- Tiêu chí hoàn thành:
  - Model PPE đã huấn luyện được nạp từ cấu hình, không dùng heuristic màu làm kết quả chính.
  - Kết quả phân biệt có/không có áo phản quang được trả về mà không phá vỡ contract inference hiện tại.
  - Có test cho mapping class, confidence threshold và trường hợp không phát hiện PPE.

### US-08 — Theo dõi người và chống tạo event trùng

**Là** cán bộ an toàn, **tôi muốn** một vi phạm liên tục chỉ tạo một event **để** nhật ký không bị lặp và cảnh báo không gây nhiễu.

- Trạng thái: **Hoàn thành một phần / cần xác minh**
- Đã có: Một frame in flight, một pending review trong frontend và contract detection có luồng realtime ổn định.
- Còn thiếu: `PROGRESS.md` chưa xác nhận cơ chế dedup theo track/cooldown hoặc test chứng minh “một vi phạm chỉ tạo một event”.
- Tiêu chí hoàn thành:
  - Một người ở liên tục trong cùng tình huống vi phạm chỉ sinh một event active.
  - Không tạo event mới cho đến khi vi phạm cũ kết thúc hoặc hết cooldown được định nghĩa.
  - Có test cho frame lặp, tái xâm nhập và nhiều người đồng thời.

### US-09 — Xác nhận, acknowledge hoặc đánh dấu false alarm

**Là** cán bộ an toàn, **tôi muốn** phân loại kết quả review **để** hệ thống lưu đúng quyết định của con người.

- Trạng thái: **Hoàn thành một phần**
- Đã có: Hai hành động “Vi phạm thực tế” và “Cảnh báo sai”; event thực tế được lưu ở trạng thái acknowledged.
- Còn thiếu: PRD liệt kê riêng `acknowledge`, `confirm` và `false alarm`, trong khi baseline hiện chưa chứng minh ba trạng thái/vòng đời tách biệt.
- Tiêu chí hoàn thành:
  - Làm rõ vòng đời trạng thái event theo đúng nhu cầu MVP.
  - Nếu acknowledge và confirm là hai bước khác nhau, cung cấp API/UI và test cho cả hai.
  - False alarm được lưu hoặc thống kê đủ để đo false-alarm rate nhưng không xuất hiện như vi phạm chính thức.

### US-10 — Dashboard và thống kê cơ bản

**Là** cán bộ an toàn, **tôi muốn** xem thống kê sự kiện **để** đánh giá tình hình tuân thủ trong phiên demo.

- Trạng thái: **Hoàn thành một phần**
- Đã có: Backend statistics endpoint và service thống kê.
- Còn thiếu: `PROGRESS.md` chưa xác nhận dashboard frontend cơ bản đã hoàn thiện.
- Tiêu chí hoàn thành:
  - Hiển thị ít nhất tổng sự kiện, vi phạm đã xác nhận và false alarm.
  - Dữ liệu dashboard lấy từ API thống kê thay vì tính riêng trên frontend.
  - Có trạng thái loading, empty và lỗi.

### US-11 — Mô tả rule và mức độ vi phạm

**Là** cán bộ an toàn, **tôi muốn** mô tả rule bằng ngôn ngữ tự nhiên và chọn mức độ vi phạm **để** hệ thống biết khi nào cảnh báo hoặc bỏ qua.

- Trạng thái: **Hoàn thành một phần**
- Đã có: Safety Agent endpoint và rule-based recommendation fallback ở backend.
- Còn thiếu: Chưa có bằng chứng về luồng end-to-end từ mô tả của cán bộ đến rule thực thi trong inference và mức cảnh báo.
- Tiêu chí hoàn thành:
  - Người dùng nhập được mô tả rule và mức độ vi phạm.
  - Rule đã tạo được validate trước khi áp dụng.
  - Inference áp dụng rule và trả về quyết định cảnh báo/bỏ qua có thể giải thích.

## User story còn lại

### US-12 — Làm mờ danh tính trước khi lưu snapshot

**Là** cán bộ an toàn, **tôi muốn** danh tính trong snapshot được làm mờ **để** bảo vệ quyền riêng tư của người lao động.

- Trạng thái: **Chưa làm**
- Bằng chứng: `PROGRESS.md` ghi snapshot hiện có `privacy_blurred=false` và đặt face blur ở bước tiếp theo.
- Tiêu chí hoàn thành:
  - Snapshot của vi phạm được làm mờ mặt/danh tính trước khi ghi xuống storage.
  - Event lưu `privacy_blurred=true` chỉ khi ảnh đã được xử lý thành công.
  - Không để lại bản snapshot chưa làm mờ khi transaction hoặc bước xử lý lỗi.
  - Có test cho ảnh có mặt, không có mặt và lỗi xử lý.

### US-13 — Đo precision, recall, false alarm và latency

**Là** nhóm phát triển, **tôi muốn** đo các chỉ số chất lượng của prototype **để** biết hệ thống có đáp ứng tiêu chí thành công trong PRD hay không.

- Trạng thái: **Chưa làm**
- Tiêu chí hoàn thành:
  - Có tập demo/ground truth đủ để tính precision và recall cho tình huống baseline.
  - False-alarm rate được tính từ quyết định review của cán bộ.
  - Latency được đo từ lúc gửi frame đến lúc nhận kết quả/cảnh báo.
  - Kết quả đo, điều kiện thử nghiệm và giới hạn được ghi lại rõ ràng.

## Thứ tự thực hiện đề xuất

1. **US-07 — Model PPE đã huấn luyện:** hoàn thiện năng lực cốt lõi “áo phản quang” của PRD.
2. **US-12 — Privacy blur:** đóng known issue ảnh hưởng trực tiếp đến tiêu chí thành công và quyền riêng tư.
3. **US-08 — Dedup event:** bảo đảm “một vi phạm chỉ tạo một event”.
4. **US-09 — Vòng đời review:** làm rõ và hoàn thiện acknowledge/confirm/false alarm.
5. **US-10 — Dashboard:** hoàn thành phần hiển thị thống kê cơ bản.
6. **US-13 — Chỉ số đánh giá:** cung cấp bằng chứng precision, recall, false alarm và latency.
7. **US-11 — Rule từ mô tả:** nối Safety Agent hiện có vào core flow sau khi detection và event lifecycle ổn định.

## Ngoài phạm vi prototype

Các hạng mục sau không nên đưa vào backlog MVP nếu PRD chưa thay đổi: camera nhà máy thật, tích hợp PLC, nhiều camera, nhiều vùng nguy hiểm, nhiều người dùng và tự động dừng máy.
