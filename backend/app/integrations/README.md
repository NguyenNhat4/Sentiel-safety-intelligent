# Backend Integrations

Adapter tại đây chuyển đổi provider hoặc protocol bên ngoài thành interface backend dùng được. Chúng không quyết định rule an toàn, severity hay event state.

`ppe_vision.py` cache public `vision.api.PpeVisionFacade` dùng checkpoint YOLO11m Safety cho observation `hat`/`vest` và tín hiệu association `person`. Adapter không quyết định alert hoặc event state.

`privacy_vision.py` là boundary độc lập cho redaction fail-closed và annotation snapshot. Event service luôn gọi theo thứ tự `redact → annotate → persist`; privacy không tải hoặc phụ thuộc checkpoint PPE.
