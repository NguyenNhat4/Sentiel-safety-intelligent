# Business Specifications: Safety Rules & Violation Engine

> **WARNING / CẤM THAY ĐỔI**: Tài liệu này quy định các quy tắc nghiệp vụ an toàn (Business Safety Rules) tối thượng của hệ thống Rule Engine và Inference. Các quy định dưới đây là bắt buộc, cấm thay đổi hoặc làm sai lệch trong bất kỳ phiên bản hay lần refactor nào.

---

## 1. Quy tắc xâm nhập Vùng cấm / Vùng nguy hiểm (Zone Intrusion & Restricted Area)

- **Khi người đi vào Vùng cấm (Zone Intrusion / Person inside active zone):**
  - Hệ thống **BẮT BUỘC** ghi nhận trạng thái **VIOLATE** (Cảnh báo vi phạm nghiêm trọng).
  - Trạng thái vi phạm xâm nhập vùng áp dụng **BẤT KỂ** trạng thái máy (machine_state là `running` hay `stopped`) và **BẤT KỂ** người đó có trang bị đủ PPE (mũ/áo bảo hộ) hay không.
  - Việc xâm nhập vùng cấm được ưu tiên mức độ nghiêm trọng (Critical severity) cao nhất.

---

## 2. Quy tắc kiểm tra trang thiết bị bảo hộ cá nhân (PPE - Mũ & Áo phản quang)

- **Điều kiện kích hoạt kiểm tra PPE:**
  - Quy tắc kiểm tra vi phạm thiếu PPE (mũ bảo hộ `hat_required`, áo phản quang `vest_required`) chỉ được thực hiện khi trạng thái máy tại vùng/camera đang là **`running` (Đang chạy)**.
  - Khi máy ở trạng thái **`stopped` (Đã dừng)**, hệ thống bỏ qua kiểm tra thiếu PPE.

- **Đánh giá vi phạm thiếu PPE:**
  - Khi máy `running`, đối với bất kỳ người nào thuộc phạm vi giám sát (hoặc đi vào zone có yêu cầu PPE), hệ thống sẽ so sánh trang phục PPE của người đó với cấu hình yêu cầu (`hat_required`, `vest_required`).
  - Nếu thiếu bất kỳ trang bị nào được yêu cầu (ví dụ thiếu mũ bảo hộ khi `hat_required=True` hoặc thiếu áo phản quang khi `vest_required=True`), hệ thống **BẮT BUỘC** phát cảnh báo vi phạm (**VIOLATE** / `missing_ppe:hat` / `missing_ppe:vest`).
  - Cảnh báo vi phạm thiếu PPE phải được đưa ra trên giao diện **Live Monitor** và danh sách cảnh báo xác minh (HITL Log / Event Review).

---

## 3. Tóm tắt Bảng Chân lý Nghiệp vụ (Business Decision Matrix)

| Trạng thái Máy (`machine_state`) | Vị trí (`inside_zone`) | Kiểm tra PPE (`hat/vest_required`) | Trang bị PPE của người | Kết quả Hệ thống (`result`) | Cảnh báo / Alert |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Bất kỳ** (`running` / `stopped`) | **Có** (Inside Zone) | Bất kỳ | Bất kỳ | **VIOLATE** | Xâm nhập vùng nguy hiểm |
| **`stopped`** | **Không** (Outside Zone) | Bất kỳ | Bất kỳ | **NORMAL** | Không vi phạm |
| **`running`** | **Có / Giám sát** | Đủ PPE theo cấu hình | Đủ mũ & áo yêu cầu | **VIOLATE** (do vào zone) / NORMAL (nếu không cấm zone) | Vi phạm Zone / Bình thường nếu đủ PPE |
| **`running`** | **Có / Giám sát** | Thiếu PPE theo cấu hình | Thiếu mũ hoặc áo yêu cầu | **VIOLATE** | Cảnh báo thiếu PPE (`missing_ppe:hat` / `missing_ppe:vest`) |

---

*Ghi chú: Bản tài liệu này đóng vai trò làm chuẩn nghiệp vụ không thể thay đổi cho Safety Rule Engine.*
