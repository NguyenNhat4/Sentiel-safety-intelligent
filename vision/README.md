# Vision

`vision` sở hữu các observation Computer Vision thuần: person/PPE detection, association, tracking, geometry và redaction. Module không đọc HTTP, database hoặc requirement của người dùng.

Runtime sử dụng `vision.api.PpeVisionFacade` với checkpoint duy nhất `yolo11m_safety.pt`. Facade xác thực mapping nguồn `{hat, nohat, novest, person, vest}`, chỉ yêu cầu source ID `0`, `3`, `4` một lần mỗi frame và chỉ phát hành `person`, `hat`, `vest`. Class `person` ID `3` là nguồn canonical cho bounding box, foot point, zone và ByteTrack; `hat`/`vest` được associate trực tiếp vào những person này từ cùng kết quả inference. Backend `rules` là nơi duy nhất biến observation thành qualified absence và cảnh báo.

Facade nhận compute device tùy chọn và truyền cùng device vào cả `predict` lẫn `track`. Worker CPU không đặt device nên giữ hành vi hiện tại; image RunPod GPU đặt `VISION_DEVICE=cuda:0` và từ chối startup nếu CUDA không khả dụng, tránh âm thầm fallback sang CPU.

Privacy không phụ thuộc model PPE. `PrivacyRedactionFacade` chạy OpenCV YuNet đúng một lần trên snapshot và chỉ mở rộng/làm mờ các face box được phát hiện. Nếu không phát hiện được mặt hoặc YuNet lỗi thì không blur fallback; trạng thái lỗi vẫn được ghi nhận qua operational metrics. Nếu không có person box hợp lệ thì facade fail-closed và backend không lưu snapshot. Pipeline chỉ annotate person/`hat`/`vest` trên frame **đã** xử lý, không quyết định safety rule và không mutate ảnh đầu vào.

ByteTrack được tích hợp trong cùng facade/model call. Local và worker v1 giữ mỗi monitoring session trong RAM, gọi frame liên tiếp bằng `persist=True`, và tự hết hạn sau TTL. Worker v2 dùng fresh tracker cho từng request rồi restore/export state rõ ràng. `track_id` chỉ là association kỹ thuật trong phiên; vision không nhận diện danh tính và không quyết định occurrence/event.

Contract worker phân tán dùng `tracking_state.py` để chuyển ByteTrack active/lost state và PPE temporal history thành JSON versioned, rồi phục hồi trên một worker mới. Module này không đọc HTTP hoặc database; backend vẫn là owner duy nhất của persistence.

Public facade nằm tại `vision/api.py`; backend chỉ gọi facade qua integration adapter. `face_detection.py` bọc model YuNet đã pin bằng một lock quanh `setInputSize + detect` để adapter cache vẫn an toàn khi request đồng thời. Tests của vision dùng ảnh tổng hợp; real-model smoke/benchmark dùng ảnh mẫu OpenCV ở ngoài repository. Pilot vẫn phải benchmark false-negative trên dữ liệu nhà máy đã được phép sử dụng.
