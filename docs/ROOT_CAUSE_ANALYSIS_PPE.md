# Báo Cáo Phân Tích Nguyên Nhân Gốc Rễ (Root Cause Analysis) & Giải Pháp Cảnh Báo PPE

## 1. Tóm Tắt Hiện Tượng
Trong video test: Người lao động không đội mũ bảo hộ xuất hiện trên khung hình khi trạng thái máy đang là **`running`**, nhưng hệ thống **không phát cảnh báo vi phạm PPE** (không chuyển trạng thái `VIOLATE`, không tạo `ActiveViolation` và không bật popup xác minh HITL / Event Review).

---

## 2. Nguyên Nhân Gốc Rễ (Root Cause Analysis)

Sau khi kiểm tra toàn bộ luồng xử lý từ AI Vision (`vision/api.py`), Backend Pipeline (`FrameInferenceService`), Tracking (`ViolationTrackingService`) và cấu hình Zone/PPE (`PpeRequirementService`, `CameraSessionRuntime`), chúng tôi xác định được **3 nguyên nhân chính** dẫn đến hiện tượng trên:

### Nguyên Nhân 1: PPE Check bị giới hạn bởi Vùng Giám Sát (`inside_zone`) trong Chế độ Multi-Zone
* **Cơ chế hiện tại trong code (`backend/app/services/frame_inference_service.py`):**
  Khi hệ thống chạy ở chế độ Multi-Zone (truyền `requirements_by_zone`), mã nguồn thực hiện lọc các zone mà người đó đứng vào (`inside_zone_ids`):
  ```python
  # frame_inference_service.py (dòng 258-270)
  for person, rule_person in zip(people, rule_people, strict=True):
      inside_zone_ids = {item.zone_id for item in person.zone_memberships if item.inside}
      applicable = [
          requirement for zone_id, requirement in requirements_by_zone.items()
          if zone_id in inside_zone_ids
      ]
      missing: set[str] = set()
      if request.machine_state == "running":
          for requirement in applicable:
              evaluated = self._rule_engine.evaluate(...)
              missing.update(evaluated.missing_required_ppe[0])
      person.missing_required_ppe = sorted(missing)
  ```
* **Hậu quả:**
  Nếu một người đứng **NGOÀI** tất cả các vùng cấm/vùng nguy hiểm (`inside_zone_ids` rỗng), danh sách `applicable` sẽ **RỖNG**. Hệ thống hoàn toàn không đánh giá quy tắc PPE cho người này, cho dù máy đang `running` và camera đã bật yêu cầu `hat_required=True` / `vest_required=True`.
* **Mâu thuẫn Quy tắc Nghiệp vụ:**
  Theo `docs/SAFETY_RULES_BUSINESS.md`, kiểm tra vi phạm thiếu PPE áp dụng khi trạng thái máy là `running` cho **bất kỳ người nào thuộc phạm vi giám sát của camera** (toàn bộ camera frame), không phụ thuộc vào việc người đó có nằm trong zone cấm hay không.

---

### Nguyên Nhân 2: Độ trễ tích lũy từ cơ chế Lọc 2 Lớp (Double Temporal Window Latency)
Hệ thống hiện tại đang duy trì **2 cơ chế đếm frame độc lập** nối tiếp nhau để xác nhận thiếu PPE:

1. **Lớp 1 - AI Vision Temporal Smoother (`PpeTemporalSmoother` trong `vision/api.py`):**
   * Cần **10 frame liên tiếp** (`temporal_frames=10`) model YOLO không nhìn thấy mũ (`raw_hat == False`) thì mới xác nhận trạng thái vắng mặt (`absence_confirmed = True`).
   * Trong 9 frame đầu, người đó được gắn trạng thái `unknown` (chưa xác định), chưa tính là `missing`.

2. **Lớp 2 - Tracking Violation Activation (`ViolationTrackingService` trong `backend/app/services/violation_tracking_service.py`):**
   * Sau khi AI Vision trả về `missing`, service này tiếp tục yêu cầu thêm **6 frame liên tiếp** (`ppe_confirmation_frames=6`) nhận được rule `missing_ppe:hat` thì mới chính thức kích hoạt `ActiveViolation`.

* **Tổng cộng latency:** Người lao động phải xuất hiện liên tục **ít nhất 16 frame (~0.5 - 1.5 giây tùy FPS)** không đội mũ và không bị mất trackID.
* **Hậu quả:** Trong video, nếu người di chuyển nhanh, bị gập góc khuất, hoặc bị ByteTrack gán lại `track_id` mới giữa chừng, chuỗi đếm 16 frame liên tiếp này liên tục bị reset về 0, dẫn đến **không bao giờ đạt ngưỡng 16 frame để bật Popup cảnh báo**.

---

### Nguyên Nhân 3: Cấu hình mặc định Yêu cầu PPE (`hat_required`) bị tắt ở cấp Zone/Camera
* Trong `PpeRequirementService` và `CameraSessionRuntime`:
  Nếu camera chưa được cấu hình lưu trong database (`PpeRequirementResponse.is_configured == False`), giá trị mặc định của `hat_required` và `vest_required` bị fallback về **`False`**.
* Nếu người dùng chưa thực hiện bấm "Lưu cấu hình PPE" trên UI cho camera/zone đó, hệ thống sẽ chạy với `hat_required=False`, làm bỏ qua toàn bộ cảnh báo thiếu mũ.

---

## 3. Bảng Tổng Hợp So Sánh Trạng Thái

| Yếu tố | Trạng thái hiện tại | Kỳ vọng chuẩn nghiệp vụ |
| :--- | :--- | :--- |
| **Phạm vi kiểm tra PPE** | Chỉ kiểm tra người nằm **INSIDE** zone | Kiểm tra **TOÀN FRAME** bất kể trong/ngoài zone khi máy `running` |
| **Xác nhận vi phạm (Frame window)** | 10 frames (Vision) + 6 frames (Tracking) = **16 frames** | Gộp thành **1 lớp duy nhất N frames** (ví dụ N=3 hoặc N=5) |
| **Phát sinh Popup HITL** | Cần đạt đủ 16 frames | Đạt đủ N frames thiếu PPE là kích hoạt Popup HITL ngay |

---

## 4. Giải Pháp Đề Xuất (Action Plan & Architectural Solution)

### Giải pháp 1: Sửa Logic Đánh Giá PPE Cấp Camera (Camera-wide Fallback)
Cập nhật `FrameInferenceService` sao cho khi máy ở trạng thái `running`:
* Nếu người nằm trong zone nào $\rightarrow$ áp dụng cấu hình PPE của zone đó.
* Nếu người đứng ngoài tất cả các zone $\rightarrow$ áp dụng cấu hình PPE mặc định/toàn cảnh của camera (`camera_ppe_requirements`).
```python
# Code đề xuất cho FrameInferenceService:
if request.machine_state == "running":
    # Lấy cấu hình chung của camera làm fallback
    camera_req = requirements
    for person, rule_person in zip(people, rule_people, strict=True):
        inside_zone_ids = {item.zone_id for item in person.zone_memberships if item.inside}
        applicable_reqs = [
            requirements_by_zone[zid] for zid in inside_zone_ids if zid in requirements_by_zone
        ] if requirements_by_zone else [camera_req]

        # Nếu đứng ngoài zone, vẫn dùng camera_req
        if not applicable_reqs:
            applicable_reqs = [camera_req]

        missing: set[str] = set()
        for req in applicable_reqs:
            evaluated = self._rule_engine.evaluate(
                people=[rule_person],
                requirements=req,
                machine_state=request.machine_state,
                zone_active=False,
            )
            missing.update(evaluated.missing_required_ppe[0])
        person.missing_required_ppe = sorted(missing)
```

### Giải pháp 2: Gộp và Đơn Giản Hóa Ngưỡng Frame Xác Nhận (Single N-Frame Window)
* Chuyển cơ chế lọc bớt rườm rà sang **1 lớp duy nhất**:
  * Đặt `PpeTemporalSmoother(temporal_frames=1)` (hoặc bỏ qua lớp smoother ở vision khi đã có tracking ở backend).
  * Điều chỉnh `ppe_confirmation_frames = N` (Ví dụ: `N = 3` hoặc `N = 5` frames) trực tiếp trong `ViolationTrackingService`.
* Nhờ đó, bất kỳ vi phạm nào kéo dài đủ `N` frame liên tiếp sẽ kích hoạt `ActiveViolation(is_new=True)` và lập tức đẩy Event sang Popup HITL.

### Giải pháp 3: Kiểm Tra Cấu Hinh Mặc Định & Cảnh Báo UI
* Đảm bảo mặc định khi bật tính năng yêu cầu PPE trên UI (PPE required toggle), `hat_required` hoặc `vest_required` được đặt `True` cho tất cả các zone hoặc cấp camera.
