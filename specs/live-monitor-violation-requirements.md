# P-047 — Requirement cảnh báo vi phạm trên Live Monitor

## Phạm vi

Tài liệu này chỉ mô tả phần cảnh báo vi phạm trên trang **Live Monitor**.

Tạm thời không thực hiện:

- Cải thiện giao diện trang camera detail.
- Thu gọn/mở rộng sidebar.
- Âm thanh cảnh báo.
- Thay đổi logic xác định vi phạm PPE hoặc xâm nhập vùng cấm.

## 1. Danh sách cảnh báo chờ xử lý

Live Monitor có một danh sách cảnh báo chung cho tất cả camera:

- Không chia danh sách riêng theo camera.
- Cảnh báo mới nhất nằm trên cùng.
- Danh sách chỉ chứa:
  - Cảnh báo PPE chưa xử lý.
  - Cảnh báo vùng cấm có popup đã bị đóng nhưng chưa được xử lý.
- Cảnh báo vùng cấm đang hiển thị trong popup tự động không xuất hiện trong danh sách.
- Mỗi dòng hiển thị tối thiểu:
  - Camera xảy ra cảnh báo.
  - Loại vi phạm: PPE hoặc vùng cấm.
  - Tên vùng nếu là vi phạm vùng cấm.
  - Thời điểm phát hiện.
  - Trạng thái `Chưa xử lý`.
- Bấm vào một dòng sẽ mở popup HITL tương ứng với đầy đủ thông tin.
- Cảnh báo chưa xử lý phải được lưu; không được mất khi đóng popup/toast, tải lại trang hoặc quay lại Live Monitor.

## 2. Luồng cảnh báo PPE

Khi có một cảnh báo PPE mới:

1. Không tự động mở popup HITL lớn.
2. Hiện một thông báo nhỏ dạng toast ở góc phải bên dưới màn hình.
3. Đồng thời thêm cảnh báo vào danh sách chung trên Live Monitor.
4. Toast phải nhỏ, có thể đóng và không cản người dùng giám sát camera khác.
5. Bấm vào toast sẽ mở popup HITL của cảnh báo đó.
6. Nếu đóng hoặc bỏ qua toast, cảnh báo vẫn còn trong danh sách chung để xử lý sau.
7. Người dùng cũng có thể bấm vào dòng trong danh sách chung để mở popup HITL.

Popup PPE hiển thị đầy đủ:

- Camera xảy ra vi phạm.
- Loại vi phạm PPE.
- PPE bị thiếu, ví dụ thiếu mũ hoặc thiếu áo phản quang.
- Thời điểm phát hiện.
- Hình ảnh/bằng chứng và thông tin HITL hiện có.

## 3. Luồng cảnh báo vùng cấm

Khi có một cảnh báo vùng cấm mới:

1. Tự động mở popup HITL ngay lập tức.
2. Mỗi thời điểm chỉ hiển thị một popup vùng cấm.
3. Nếu cảnh báo vùng cấm khác đến khi một popup đang mở:
   - Không mở popup chồng lên.
   - Đưa cảnh báo mới vào hàng đợi.
   - Chỉ hiện popup tiếp theo sau khi popup hiện tại được đóng hoặc xử lý xong.
4. Nếu người dùng đóng popup mà chưa xác nhận:
   - Lưu cảnh báo ở trạng thái `Chưa xử lý`.
   - Thêm cảnh báo vào danh sách chung trên Live Monitor.
   - Sau đó hiện popup vùng cấm tiếp theo trong hàng đợi, nếu có.
5. Nếu người dùng xử lý trực tiếp trên popup:
   - Không thêm cảnh báo vào danh sách chờ xử lý.
   - Chuyển bản ghi sang Nhật ký vi phạm cùng kết quả HITL.
   - Sau đó hiện popup vùng cấm tiếp theo trong hàng đợi, nếu có.

Popup vùng cấm hiển thị đầy đủ:

- Camera xảy ra vi phạm.
- Tên vùng cấm.
- Loại vi phạm.
- Thời điểm phát hiện.
- Hình ảnh/bằng chứng và thông tin HITL hiện có.

## 4. Xử lý HITL

Popup được mở từ toast PPE, hàng đợi vùng cấm hoặc danh sách chung đều sử dụng cùng luồng HITL hiện tại.

Người giám sát có thể:

- Xác nhận vi phạm thật.
- Xác nhận `Cảnh báo sai / False alarm`.
- Đóng popup để xử lý sau.

| Thao tác | Danh sách chờ xử lý | Nhật ký vi phạm |
|---|---|---|
| Đóng popup | Còn trong hoặc được thêm vào danh sách | Chưa chuyển thành bản ghi đã xử lý |
| Xác nhận vi phạm thật | Biến mất khỏi danh sách | Lưu với kết quả `Đã xác nhận vi phạm` |
| Xác nhận cảnh báo sai | Biến mất khỏi danh sách | Lưu với kết quả `Cảnh báo sai` |

`Biến mất` chỉ có nghĩa là cảnh báo rời khỏi danh sách cần xử lý. Dữ liệu không bị xóa.

## 5. Yêu cầu không gây cản trở

- Không phát âm thanh cho bất kỳ loại cảnh báo nào.
- Không cho phép nhiều popup chồng lên nhau.
- Toast PPE nằm ở góc phải dưới, có thể đóng và không che khu vực giám sát chính.
- Cảnh báo không được ngăn người dùng xem hoặc chuyển sang camera khác.
- Đóng popup/toast không làm mất cảnh báo chưa xử lý.

## 6. Tiêu chí hoàn thành ở mức hành vi

- PPE mới tạo toast và một dòng trong danh sách nhưng không tự mở popup lớn.
- Bấm toast hoặc dòng PPE mở đúng popup HITL.
- Vùng cấm mới tự mở popup ngay.
- Nhiều cảnh báo vùng cấm được xử lý tuần tự, không chồng popup.
- Đóng popup vùng cấm đưa cảnh báo vào danh sách chung ở trạng thái chưa xử lý.
- Xác nhận vi phạm thật hoặc cảnh báo sai loại bỏ dòng khỏi danh sách và lưu đúng kết quả trong Nhật ký vi phạm.
- Danh sách chung sắp xếp cảnh báo mới nhất ở trên cùng và chứa cảnh báo của tất cả camera.
- Không có âm thanh cảnh báo.
