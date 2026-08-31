# Area Management

The area dashboard subscribes to the shared safety-event update signal and
reloads its event list when Monitor or another browser tab changes an event.

Trang làm việc riêng của Quản lý khu vực. Feature này tổng hợp thống kê tuân thủ theo khu vực và các sự kiện đã xác nhận thông qua frontend API layer; không sở hữu logic phát hiện hoặc quản trị tài khoản.

Backend giới hạn dữ liệu theo danh sách camera được phân cho quản lý; dashboard ghép từng thống kê theo `camera_id`, giữ nhãn cố định Camera 1–4 và hiển thị cả sự kiện đang chờ xác minh thuộc các camera đó.
