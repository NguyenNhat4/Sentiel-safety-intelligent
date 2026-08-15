# Backend Integrations

Adapter tại đây chuyển đổi provider hoặc protocol bên ngoài thành interface backend dùng được. Chúng không quyết định rule an toàn, severity hay event state.

`ppe_vision.py` gọi public facade `vision.api.PpeVisionFacade` cho PPE observation trong inference, redaction snapshot US-12, và annotation box thuần trên frame đã redact. Adapter cache một SH17 facade chung; nó không quyết định alert, event state hay privacy policy. Event service redacts trước, sau đó mới yêu cầu annotation và persistence.

Snapshot storage exposes a non-mutating connectivity check. `/health` uses it to verify the configured S3 bucket with `HeadBucket`; it never uploads, reads, or deletes a snapshot during a health probe.
