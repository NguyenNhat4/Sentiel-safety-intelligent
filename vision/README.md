# Vision

`vision` sở hữu các observation Computer Vision thuần: person/PPE detection, association, tracking, geometry và redaction. Module không đọc HTTP, database hoặc requirement của người dùng.

Runtime sử dụng `vision.api.PpeVisionFacade` với checkpoint duy nhất `yolo11m_safety.pt`. Facade xác thực mapping nguồn `{hat, nohat, novest, person, vest}`, chỉ yêu cầu source ID `0`, `3`, `4` một lần mỗi frame và chỉ phát hành `person`, `hat`, `vest`. Class `person` ID `3` là nguồn canonical cho bounding box, foot point, zone và ByteTrack; `hat`/`vest` được associate trực tiếp vào những person này từ cùng kết quả inference. Backend `rules` là nơi duy nhất biến observation thành qualified absence và cảnh báo.

Privacy không phụ thuộc model PPE. `PrivacyRedactionFacade` làm mờ 40% phía trên mọi person canonical trước persistence; nếu không có person box hợp lệ thì facade fail-closed và backend không lưu snapshot. Pipeline chỉ annotate person/`hat`/`vest` trên frame **đã** redact, không quyết định safety rule và không mutate ảnh đầu vào.

ByteTrack được tích hợp trong cùng facade/model call. Mỗi monitoring session có tracker state riêng, gọi frame liên tiếp bằng `persist=True`, và tự hết hạn sau TTL. `track_id` chỉ là association kỹ thuật trong phiên; vision không nhận diện danh tính và không quyết định occurrence/event.

Public facade nằm tại `vision/api.py`; backend chỉ gọi facade qua integration adapter. Tests của vision nằm tại `vision/tests/` và dùng ảnh tổng hợp, không dùng dữ liệu cá nhân thật. Redaction dựa trên person-head là safeguard fail-closed của prototype; một face detector chuyên dụng có benchmark và license phù hợp vẫn là production gate.
