# Vision Tests

Các test tại đây kiểm chứng logic CV thuần, không khởi tạo FastAPI hoặc database.

Chạy test US-07 cùng backend rule tests:

```bash
PYTHONPATH=. .venv/bin/pytest vision/tests backend/tests/test_frame_inference_ppe.py -v
```
