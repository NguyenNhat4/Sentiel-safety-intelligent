# Vision

`vision` sở hữu các observation Computer Vision thuần: person/PPE detection, association, tracking, geometry và redaction. Module không đọc HTTP, database hoặc requirement của người dùng.

Runtime sử dụng `vision.api.PpeVisionFacade` với checkpoint duy nhất `yolo11m_safety.pt`. Facade xác thực mapping nguồn `{hat, nohat, novest, person, vest}`, chỉ yêu cầu source ID `0`, `3`, `4` một lần mỗi frame và chỉ phát hành `person`, `hat`, `vest`. Class `person` ID `3` là nguồn canonical cho bounding box, foot point, zone và ByteTrack; `hat`/`vest` được associate trực tiếp vào những person này từ cùng kết quả inference. Backend `rules` là nơi duy nhất biến observation thành qualified absence và cảnh báo.

Facade nhận compute device tùy chọn và truyền cùng device vào cả `predict` lẫn `track`. Worker CPU không đặt device nên giữ hành vi hiện tại; image RunPod GPU đặt `VISION_DEVICE=cuda:0` và từ chối startup nếu CUDA không khả dụng, tránh âm thầm fallback sang CPU.

Privacy không phụ thuộc model PPE. `PrivacyRedactionFacade` chạy OpenCV YuNet đúng một lần trên snapshot, mở rộng và làm mờ mọi face box, rồi làm mờ 40% phía trên riêng từng person canonical không có face tương ứng. Nếu YuNet lỗi, mọi person dùng fallback; nếu không có person box hợp lệ thì facade fail-closed và backend không lưu snapshot. Pipeline chỉ annotate person/`hat`/`vest` trên frame **đã** redact, không quyết định safety rule và không mutate ảnh đầu vào.

ByteTrack được tích hợp trong cùng facade/model call. Mỗi monitoring session có tracker state riêng, gọi frame liên tiếp bằng `persist=True`, và tự hết hạn sau TTL. `track_id` chỉ là association kỹ thuật trong phiên; vision không nhận diện danh tính và không quyết định occurrence/event.

Public facade nằm tại `vision/api.py`; backend chỉ gọi facade qua integration adapter. `face_detection.py` bọc model YuNet đã pin bằng một lock quanh `setInputSize + detect` để adapter cache vẫn an toàn khi request đồng thời. Tests của vision dùng ảnh tổng hợp; real-model smoke/benchmark dùng ảnh mẫu OpenCV ở ngoài repository. Pilot vẫn phải benchmark false-negative trên dữ liệu nhà máy đã được phép sử dụng.
