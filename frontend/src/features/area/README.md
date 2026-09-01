# Area Management

The area dashboard subscribes to the shared safety-event update signal and
reloads its event list when Monitor or another browser tab changes an event.

Trang làm việc riêng của Quản lý khu vực. Feature này tổng hợp số event thật theo trạng thái và camera thông qua frontend API layer; không sở hữu logic phát hiện hoặc quản trị tài khoản. Dashboard không suy diễn tỷ lệ tuân thủ khi hệ thống chưa lưu mẫu số lượt kiểm tra bình thường.

Backend giới hạn dữ liệu theo danh sách camera được phân cho quản lý; dashboard ghép từng thống kê theo `camera_id`, hiển thị tên camera lấy từ tên media đã upload và hiển thị cả sự kiện đang chờ xác minh thuộc các camera đó.
