# Quy Trình Làm Việc Tiêu Chuẩn (AI-Assisted Workflow)

## 1. Tổng quan Dự án & Trạng thái
- **Mô hình đội hình:** 4 Members + 4 AI Agents hỗ trợ (Accelerate coding & testing).
- **Trạng thái Task (trên Sheet):** `Chưa làm` ➡️ `Đang làm` ➡️ `Đang review` ➡️ `Bị kẹt` ➡️ `Hoàn thành` (hoặc `Không làm`).
- **Chiến lược Git Branch:** 
  - `main`: Chỉ chứa code đã chạy ổn định và sẵn sàng release.
  - `develop`: Nhánh tích hợp các tính năng mới từ các thành viên.
  - `feature/US-XX`: Nhánh làm việc cá nhân của mỗi thành viên cho từng task.

---

## 2. Quy trình làm việc chi tiết (Step-by-Step)

### 🟢 Bước 1: Nhận Task (Pick US)
1. Thành viên tự chọn một User Story (`US-XX`) chưa ai làm từ Github Backlog.
2. Lên Google Sheet cập nhật người phụ trách và đổi trạng thái thành **Đang làm**.
3. Tại máy cá nhân, tạo và chuyển sang branch mới từ nhánh `develop`:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/US-XX
   ```

### 🟡 Bước 2: AI Viết Specs & Chốt Specs (Chỉ Review Specs)
1. Member cung cấp thông tin cơ bản của `US-XX` cho AI Agent và yêu cầu AI sinh ra một file Specs chi tiết (lưu vào file `US-XX.md`).
2. Thành viên cập nhật trạng thái Sheet thành **Đang review**.
3. Gửi file `US-XX.md` cho một thành viên khác trong team để Review.
   - 🔄 **Not Happy:** Có comment chỉnh sửa ➡️ Yêu cầu AI sửa lại file Specs.
   - ✅ **Happy:** Chốt Specs ➡️ Chuyển Sheet về lại trạng thái **Đang làm** để bắt đầu code.

> 📋 **Checklist cho Reviewer (Chỉ tập trung vào Specs):**
> Reviewer cần đọc file `US-XX.md` và tự trả lời các câu hỏi sau:
> - [ ] **Tính đầy đủ:** Specs đã giải quyết đúng mục tiêu cốt lõi của User Story gốc chưa?
> - [ ] **Tiêu chí nghiệm thu (Acceptance Criteria):** Có đo lường và kiểm chứng được không? (Nếu mập mờ thì khó sinh Test).
> - [ ] **Ngoại lệ (Edge Cases):** AI đã lường trước các trường hợp luồng đi sai chưa? (Ví dụ: data rỗng, user nhập sai định dạng, đứt kết nối mạng...).
> - [ ] **Cấu trúc dữ liệu/Logic:** Input và Output định nghĩa có bị mâu thuẫn với cấu trúc hiện tại của dự án không?

### 🔵 Bước 3: Triển khai Code & Testing (AI Accelerate)
1. Dựa trên file Specs đã "Happy", Member ra lệnh cho AI Agent tiến hành viết code.
2. Code xong tính năng, yêu cầu AI sinh Code Test.
   
> 💡 **Gợi ý Quy trình Test cho 1 US:**
> Do AI viết test rất nhanh, team nên áp dụng nguyên tắc: **Code xong là phải có Test đi kèm.**
> - **Unit Test:** Yêu cầu AI viết các bài test để kiểm tra độc lập các logic tính toán, các hàm, hoặc class vừa tạo xem có chạy đúng như Specs hay không.
> - **Integration Test:** Sau khi qua Unit Test, yêu cầu AI viết test kiểm tra tích hợp: Code mới kết nối với Database / API hiện tại / Module của người khác có mượt mà và không làm hỏng tính năng cũ không.
> - *Quy tắc:* Thành viên phải chạy toàn bộ Test ở dưới máy local và pass 100% trước khi thực hiện bước tiếp theo.

### 🟣 Bước 4: Pull Request (PR)
1. Code và Test đã xong, commit và push code lên nhánh cá nhân:
   ```bash
   git push origin feature/US-XX
   ```
2. Tạo Pull Request (PR) merge từ `feature/US-XX` vào `develop`.
3. Nhờ một thành viên khác approve PR (xác nhận CI/CD pass nếu có, hoặc chỉ cần xác nhận code nhìn ổn thỏa).
4. Thực hiện Merge vào `develop`.
5. Đổi trạng thái trên Sheet thành **Hoàn thành**. Di chuyển file `US-XX.md` vào thư mục `done` trên Github.

### 🔴 Bước 5: Merge vào Main (Release)
- Quá trình này thường do Tech Lead hoặc cả team cùng xác nhận.
- Khi nhánh `develop` đã tích hợp xong nhiều US và **được chạy thử/kiểm tra xác nhận là hoạt động trơn tru (chạy được)**, không có bug nghiêm trọng.
- Tiến hành tạo PR merge từ `develop` vào `main` để chốt phiên bản.

---

Bạn xem bản Quy trình này đã sát với mong đợi chưa nhé. 
Nếu bạn muốn lưu nó vào dự án, mình có thể dùng công cụ để tự động tạo và lưu nó thành một file ví dụ như `docs/AI_TEAM_WORKFLOW.md` để cả team dễ dàng đọc và tuân thủ. Bạn có muốn mình tạo file luôn không?