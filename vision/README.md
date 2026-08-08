# Vision

`vision` sở hữu các observation Computer Vision thuần: person/PPE detection, association, tracking, geometry và redaction. Module không đọc HTTP, database hoặc requirement của người dùng.

US-07 sử dụng `vision.api.PpeVisionFacade` để lấy toàn bộ 17 detection class của checkpoint SH17, cùng observation PPE theo từng person. Mỗi detection gồm class ID/tên, bbox, confidence và `person_index` có thể là `null`; backend `rules` quyết định observation nào trở thành cảnh báo.

Public facade sẽ nằm tại `vision/api.py`. Tests của vision nằm tại `vision/tests/` khi module có implementation cần kiểm chứng.
