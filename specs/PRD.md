# Product Brief — MFG-20 PPE & Zone Safety Agent

## Bài toán

Cán bộ an toàn khó theo dõi liên tục nhiều camera, quy định PPE, vùng nguy hiểm và trạng thái máy. Vì vậy, các trường hợp thiếu đồ bảo hộ hoặc xâm nhập vùng nguy hiểm có thể bị bỏ sót hay cảnh báo chậm.

## Giải pháp

Xây dựng prototype dùng Computer Vision để:

* Phát hiện người trong video.

* Kiểm tra người có mặc áo bảo hộ hay không.

* Xác định người có đi vào một hoặc nhiều vùng nguy hiểm trên cùng video.

* Kết hợp trạng thái máy ON/OFF độc lập theo từng vùng.

* Tạo cảnh báo theo mức độ.

* Cho phép con người xác nhận hoặc đánh dấu cảnh báo sai.

* Lưu nhật ký và thống kê sự kiện.

## Người dùng chính

* Cán bộ an toàn.

## Phạm vi prototype

* Video mô phỏng, chưa dùng camera nhà máy thật.

* Từ 0 đến nhiều vùng nguy hiểm bốn điểm không giao/chạm/chứa nhau trên một video mô phỏng; không đặt giới hạn số vùng ở cấp sản phẩm.

* Một loại PPE trong baseline: áo phản quang.

* Một trạng thái máy ON/OFF mô phỏng cho mỗi vùng.

* Một người dùng.

* Cảnh báo realtime, nhật ký sự kiện và dashboard cơ bản.

* Cán bộ an toàn mô tả sinh rule, mức độ vi phạm để cảnh báo hoặc bỏ qua. 

* Cán bộ xác nhận cảnh báo đúng hay không.

## Core flow

→ Cán bộ mô tả → rule được tạo

→ Cán bộ tạo một hoặc nhiều vùng cấm, mỗi vùng gồm bốn điểm và trạng thái máy riêng.

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

* Critical alert xuất hiện gần realtime và chỉ gắn với vùng có máy đang chạy.

* Người dùng có thể acknowledge, confirm hoặc false alarm.

* Snapshot được làm mờ danh tính.

* Có số liệu precision, recall, false alarm và latency.

## Giới hạn

Prototype chưa chứng minh độ chính xác trong nhà máy thật, chưa tích hợp PLC, chưa xử lý nhiều camera/video đồng thời và không tự động dừng máy. Trạng thái máy theo vùng là mô phỏng do người vận hành cấu hình.
