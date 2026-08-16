# Vision Tests

Các test tại đây kiểm chứng logic CV thuần, không khởi tạo FastAPI hoặc database, bao gồm YuNet face detection, redaction fail-closed, per-person fallback và annotation box chỉ chạy trên frame đã redact.

Chạy test US-07 cùng backend rule tests:

```bash
PYTHONPATH=. .venv/bin/pytest vision/tests backend/tests/test_frame_inference_ppe.py -v
```
