# Backend Integrations

Adapter tại đây chuyển đổi provider hoặc protocol bên ngoài thành interface backend dùng được. Chúng không quyết định rule an toàn, severity hay event state.

`ppe_vision.py` gọi public facade `vision.api.PpeVisionFacade` cho cả PPE observation trong inference và redaction snapshot US-12. Adapter cache một SH17 facade chung; nó không quyết định alert, event state hay privacy policy. Event service chỉ yêu cầu redaction, sau đó mới quyết định persistence.
