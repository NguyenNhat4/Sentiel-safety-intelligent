TÊN ĐỀ TÀI: 
AI Agent Giám Sát An Toàn PPE & Khu Vực Nguy Hiểm Bằng Computer Vision (PPE & Zone Safety Agent)

MÔ TẢ BÀI TOÁN:
📍 Thực trạng: Nhà máy có khu vực nguy hiểm (máy dập, xe nâng, hóa chất) yêu cầu đội mũ/kính/găng đúng quy định và không xâm nhập vùng cấm; giám sát bằng người không xuể, vi phạm dễ bị bỏ sót.
🎯 Vấn đề: Cần AI Agent phân tích luồng camera phát hiện thiếu PPE và người xâm nhập vùng cấm khi máy đang chạy, cảnh báo realtime, ghi nhận vi phạm và thống kê tuân thủ theo khu vực/ca.
🔒 Ràng buộc: Cảnh báo nguy hiểm nghiêm trọng (người trong vùng nguy hiểm) escalate ngay tới người phụ trách (HITL); tôn trọng quyền riêng tư (làm mờ danh tính, chỉ lưu vi phạm); bảo mật dữ liệu hình ảnh; cân bằng độ chính xác/false alarm; độ trễ phát hiện thấp; ưu tiên an toàn con người.

TECH STACK GỢI Ý - không bắt buộc:
• Computer Vision (YOLOv8 phát hiện người + PPE, định nghĩa vùng cấm) + LLM (mô tả sự việc, sinh cảnh báo/báo cáo)
• LangGraph (detect → đối chiếu quy tắc vùng/máy → cảnh báo → escalate)
• xử lý video (OpenCV), làm mờ khuôn mặt
• bnd FastAPI + WebSocket
• frontend React (live view + nhật ký vi phạm)
• deploy cloud.

YÊU CẦU ĐẦU RA:
Cơ bản:
• Web deploy, đăng nhập 2 vai trò (Cán bộ an toàn & Quản lý khu vực)
• phân tích video/ảnh mô phỏng, phát hiện thiếu PPE & xâm nhập vùng cấm, cảnh báo realtime có khoanh vùng, làm mờ danh tính
• nhật ký vi phạm
• memory.
Nâng cao:
• Kết hợp trạng thái máy (chỉ cảnh báo khi máy chạy) giảm false alarm
• escalate tự động sự cố nghiêm trọng
• dashboard tỷ lệ tuân thủ theo khu vực/ca
• báo cáo an toàn định kỳ
• ngưỡng tin cậy chuyển người khi mơ hồ.

