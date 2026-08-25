# Hướng Dẫn Onboarding Cho Lập Trình Viên Mới (P-047 Safety Monitoring)

Tài liệu này là hướng dẫn tổng quan và từng bước dành cho kỹ sư/lập trình viên mới khi bắt đầu tiếp cận, phát triển hoặc bảo trì hệ thống **P-047 Safety Monitoring**.

---

## 1. Tổng Quan Hệ Thống

**P-047** là hệ thống mẫu prototype sử dụng AI/Computer Vision để hỗ trợ giám sát an toàn lao động trong nhà máy sản xuất. Hệ thống phân tích video hoặc hình ảnh trực tiếp, tự động phát hiện người, kiểm tra trang thiết bị bảo hộ cá nhân (PPE: Mũ bảo hộ và Áo phản quang), kiểm tra xâm nhập các vùng nguy hiểm (Danger Zones), gửi cảnh báo gần như thời gian thực để con người xác minh (Human-in-the-Loop - HITL), và lưu trữ bằng chứng sự kiện đã che danh tính (Privacy Redaction).

### Vai Trò Nguồn Sự Thật (Source of Truth)
- Các file mã nguồn executable (FastAPI routes, Pydantic schemas, SQLAlchemy ORM models, Alembic migrations, React TypeScript types) là **nguồn sự thật duy nhất** về runtime contract.
- Nguồn tài liệu dẫn đường chính là `context-map.md` và `ARCHITECTURE.md`.

---

## 2. Vai Trò Người Dùng Trong Hệ Thống (RBAC)

Hệ thống phân quyền 3 vai trò chính:
1. **`system_admin` (Quản trị hệ thống):**
   - Quản lý tài khoản người dùng, cấp/reset mật khẩu tạm.
   - Tải lên (upload) và quản lý tài sản hình ảnh/video trong **Thư viện media**.
2. **`safety_manager` (Quản lý an toàn):**
   - Cấu hình 4 ô camera logic (`cam_1` đến `cam_4`): gán media asset, vẽ vùng nguy hiểm (Polygon), cấu hình quy tắc an toàn (Mũ, Áo, Zone Intrusion, Machine State).
   - Theo dõi Live Monitor, điều khiển chạy mô phỏng (Run/Replay) phiên inference.
   - Thực hiện xác minh cảnh báo Human-in-the-Loop (Xác nhận vi phạm / Báo cờ False Alarm).
3. **`area_manager` (Quản lý khu vực):**
   - Xem thống kê compliance/vi phạm của khu vực mình phụ trách.
   - Theo dõi lịch sử sự kiện (Event History) và xử lý các hành động tiếp theo.

---

## 3. Kiến Trúc Cấu Trúc Mã Nguồn (Ownership Boundaries)

Dự án tuân theo mô hình **Modular Monolith** với 3 thành phần chính (Owners):

```text
       ┌────────────────────────┐
       │     React 19 UI        │  (frontend/)
       └───────────┬────────────┘
                   │ REST / WebSocket
                   ▼
       ┌────────────────────────┐
       │    FastAPI Backend     │  (backend/)
       └───────────┬────────────┘
                   │ Integration Adapter
                   ▼
       ┌────────────────────────┐
       │   Vision Facade /      │  (vision/ hoặc Remote HTTP Worker)
       │   YOLO11m Safety Model │
       └────────────────────────┘
```

1. **`frontend/` (React 19 + TypeScript + Vite):**
   - Phụ trách giao diện người dùng, hiển thị video/ảnh, vẽ bounding box/polygon overlay, điều phối trạng thái UI và gửi action HITL.
   - **Không được:** Tự quyết định mức độ nghiêm trọng (severity) hoặc tự tính toán phân quyền.
2. **`backend/` (FastAPI + SQLAlchemy + PostgreSQL):**
   - Phụ trách REST API, WebSocket server, xác thực auth/RBAC, quản lý phiên camera (Camera Sessions), kiểm tra quy tắc an toàn (Safety Rule Engine), dedup sự kiện, lưu trữ database và gọi Privacy Redaction.
   - **Không được:** Chứa trực tiếp mã nguồn Computer Vision thô hoặc render HTML.
3. **`vision/` (YOLO11m Safety + ByteTrack + OpenCV YuNet):**
   - Phụ trách phát hiện người (`person`), mũ (`hat`), áo (`vest`), gán ByteTrack ID và làm mờ khuôn mặt (Privacy Redaction).
   - **Không được:** Phụ thuộc vào HTTP, database, thông tin người dùng hay vòng đời sự kiện (event lifecycle).

---

## 4. Quy Tắc Nghiệp Vụ An Toàn Cốt Lõi (Business Safety Rules)

Đây là các quy tắc **bất biến** (Immutable Safety Rules) bắt buộc phải nắm rõ:

1. **Vùng Nguy Hiểm (Zone Intrusion):**
   - Khi `zone_intrusion_enabled = true` trên một vùng, bất kỳ người nào đi vào vùng này **LUÔN LUÔN** tạo cảnh báo vi phạm (`violate`), **bất kể** máy đang chạy (`running`) hay dừng (`stopped`).
2. **Trang Thiết Bị Bảo Hộ (PPE Compliance):**
   - Quy tắc thiếu PPE (`hat_required`, `vest_required`) **chỉ được đánh giá khi máy đang chạy (`machine_state = running`)**.
   - Khi máy ở trạng thái dừng (`machine_state = stopped`), các thiếu sót về PPE sẽ **KHÔNG** tạo cảnh báo vi phạm.
3. **Chống Trùng Sự Kiện (Dedup & Occurrence):**
   - Mỗi người được theo dõi (track_id trong 1 session) chỉ tạo tối đa **1 cảnh báo vi phạm chờ review** cho mỗi rule/zone để tránh tình trạng spam UI cảnh báo liên tục.
4. **Bảo Vệ Danh Tính (Privacy Gate):**
   - Snapshot sự kiện bắt buộc phải chạy qua pipeline làm mờ khuôn mặt (YuNet / person fallback) trước khi lưu trữ. Nếu làm mờ thất bại, hệ thống **không lưu snapshot** và không đánh dấu `privacy_blurred = true`.

---

## 5. Bảng Thuật Ngữ Cốt Lõi (Glossary)

| Thuật ngữ | Khái niệm / Giải thích |
|---|---|
| **Camera Slot** | 4 vị trí camera logic cố định (`cam_1`, `cam_2`, `cam_3`, `cam_4`) hiển thị trên màn hình Live Monitor. |
| **Media Asset** | Tệp video hoặc ảnh được `system_admin` tải lên thư viện media, sau đó gán vào Camera Slot. |
| **Monitoring Zone** | Vùng polygon (tối thiểu 4 điểm) được vẽ trên hình ảnh camera để đánh giá an toàn. |
| **Machine State** | Trạng thái máy móc gắn với từng zone hoặc camera (`running` hoặc `stopped`). |
| **ByteTrack ID** | ID định danh người trong một phiên video theo thời gian thực để theo dõi chuyển động. |
| **Occurrence** | Một chuỗi sự kiện vi phạm liên tục của một `track_id` trong một vùng nguy hiểm/quy tắc. |
| **HITL Review** | Quy trình Human-in-the-Loop: Quản lý an toàn xem snapshot và xác nhận vi phạm hoặc đánh dấu cảnh báo giả (False Alarm). |
| **Decision Audit** | Bản ghi ngữ cảnh bất biến của sự kiện (`decision_context_v1`) lưu trữ nguyên trạng rule version, machine state, confidence và người review. |

---

## 6. Lộ Trình Cho Lập Trình Viên Mới (Getting Started Roadmap)

### Bước 1: Khởi động dự án cục bộ
```bash
# 1. Cài đặt môi trường và dependencies locked
make setup

# 2. Khởi chạy ứng dụng (Backend FastAPI + Frontend Vite build)
make run
```
Sau khi chạy `make run`, ứng dụng sẽ mở tại `http://localhost:8000`.

### Bước 2: Chạy kiểm tra (Verification Checks)
```bash
# Kiểm tra tổng thể dự án
make check

# Hoặc chạy riêng lẻ từng phần:
PYTHONPATH=. .venv/bin/pytest backend/tests vision/tests -v
npm --prefix frontend run type-check
npm --prefix frontend run test
```

### Bước 3: Đọc các tài liệu quan trọng tiếp theo
1. **`context-map.md`**: Bản đồ dẫn đường tổng thể cho toàn bộ repository.
2. **`ARCHITECTURE.md`**: Chi tiết kiến trúc đích và các ràng buộc kỹ thuật.
3. **`docs/architecture/architecture_diagram.md`**: Các sơ đồ sequence và runtime flow.
4. **`docs/architecture/alert-rule-contract.md`**: Đặc tả chi tiết hợp đồng quy tắc cảnh báo.
5. **`docs/ops/DEPLOYMENT_FLOW.md`**: Luồng triển khai hệ thống (CI/CD, Railway, Docker).

---

## 7. Quy Trình Đóng Góp Code (Workflow Guidelines)

1. Luôn tuân thủ hướng dẫn trong `AGENTS.md`.
2. Không tự ý sửa trực tiếp artifact build (như thư mục `dist/`). Sửa mã nguồn và chạy lệnh build tương ứng.
3. Trước khi submit thay đổi, bắt buộc gọi và hoàn thành các bước pre-commit checks (`make check`).
