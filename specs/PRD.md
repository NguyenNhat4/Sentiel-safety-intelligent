# Product Brief — MFG-20 PPE & Zone Safety Agent

## Bài toán

Cán bộ an toàn khó theo dõi liên tục nhiều camera, quy định PPE, vùng nguy hiểm và trạng thái máy. Vì vậy, các trường hợp thiếu đồ bảo hộ hoặc xâm nhập vùng nguy hiểm có thể bị bỏ sót hay cảnh báo chậm.

## Giải pháp

Xây dựng prototype dùng Computer Vision để:

* Phát hiện người trong video.

* Kiểm tra người có mặc áo bảo hộ hay không.

* Xác định người có đi vào vùng nguy hiểm.

* Kết hợp trạng thái máy ON/OFF.

* Tạo cảnh báo theo mức độ.

* Cho phép con người xác nhận hoặc đánh dấu cảnh báo sai.

* Lưu nhật ký và thống kê sự kiện.

## Người dùng chính

* Cán bộ an toàn.

## Phạm vi prototype

* Video mô phỏng, chưa dùng camera nhà máy thật.

* Một vùng nguy hiểm.

* Một loại PPE trong baseline: áo phản quang.

* Một trạng thái máy ON/OFF.

* Một người dùng.

* Cảnh báo realtime, nhật ký sự kiện và dashboard cơ bản.

* Cán bộ an toàn mô tả sinh rule, mức độ vi phạm để cảnh báo hoặc bỏ qua. 

* Cán bộ xác nhận cảnh báo đúng hay không.

## Core flow

→ Cán bộ mô tả → rule được tạo

→ Cán bộ chấm bốn điểm vẽ vùng cấm.

→ Video demo upload  
→ phát hiện người

→ phát hiện PPE (áo phản quang)
→ theo dõi người  
→ áp dụng rule  
→ tạo cảnh báo  
→ người thật xác nhận, snapshot vi phạm.  
→ lưu sự kiện.

## Thành công khi

* Chạy đúng các tình huống cơ bản.

* Một vi phạm chỉ tạo một event.

* Critical alert xuất hiện gần realtime.

* Người dùng có thể acknowledge, confirm hoặc false alarm.

* Snapshot được làm mờ danh tính.

* Có số liệu precision, recall, false alarm và latency.

## Giới hạn

Prototype chưa chứng minh độ chính xác trong nhà máy thật, chưa tích hợp PLC, chưa xử lý nhiều camera và không tự động dừng máy.
