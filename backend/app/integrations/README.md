# Backend Integrations

Adapter tại đây chuyển đổi provider hoặc protocol bên ngoài thành interface backend dùng được. Chúng không quyết định rule an toàn, severity hay event state.

US-07 có `ppe_vision.py`, adapter gọi public facade `vision.api.PpeVisionFacade` và trả PPE observations theo từng person cho flow inference. Rule ON/OFF và quyết định alert vẫn thuộc `backend.app.services.ppe_requirement_service`.
