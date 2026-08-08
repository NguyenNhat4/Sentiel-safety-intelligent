# Vision

`vision` sở hữu các observation Computer Vision thuần: person/PPE detection, association, tracking, geometry và redaction. Module không đọc HTTP, database hoặc requirement của người dùng.

US-07 sử dụng `vision.api.PpeVisionFacade` để lấy toàn bộ 17 detection class của checkpoint SH17, cùng observation PPE theo từng person. Mỗi detection gồm class ID/tên, bbox, confidence và `person_index` có thể là `null`; backend `rules` quyết định observation nào trở thành cảnh báo.

US-12 sử dụng chính checkpoint SH17 để che danh tính trước persistence. `vision/pipeline.py` làm mờ mọi vùng `face`, `face-guard`, `face-mask` và `head`; với mỗi `person` không có vùng nhận dạng tương ứng, pipeline làm mờ 40% phía trên bounding box. Nếu không có vùng nhận dạng lẫn `person`, facade báo lỗi fail-closed và backend không được lưu snapshot. Cùng pipeline chỉ annotate person/SH17 bounding boxes trên frame **đã** redact; nó không chạy detector, không quyết định safety rule, và không mutate ảnh đầu vào.

Public facade nằm tại `vision/api.py`; backend chỉ gọi facade qua integration adapter. Tests của vision nằm tại `vision/tests/` và dùng ảnh tổng hợp, không dùng dữ liệu cá nhân thật. SH17 là phương án MVP; một face detector chuyên dụng có benchmark và license phù hợp vẫn là production gate.
