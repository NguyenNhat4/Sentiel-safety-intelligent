# AI Agent Giám Sát An Toàn PPE & Khu Vực Nguy Hiểm Bằng Computer Vision

> Tóm tắt 1 câu: Thiếu giám sát an toàn liên tục tại nhà máy → AI Agent phân tích camera theo thời gian thực (YOLO + OpenCV) cho Cán bộ an toàn và Quản lý khu vực.

## Vấn đề (Problem)

📍 Thực trạng: Nhà máy có khu vực nguy hiểm (máy dập, xe nâng, hóa chất) yêu cầu đội mũ/kính/găng đúng quy định và không xâm nhập vùng cấm; giám sát bằng người không xuể, vi phạm dễ bị bỏ sót.
🎯 Vấn đề: Cần AI Agent phân tích luồng camera phát hiện thiếu PPE và người xâm nhập vùng cấm khi máy đang chạy, cảnh báo realtime, ghi nhận vi phạm và thống kê tuân thủ theo khu vực/ca.
🔒 Ràng buộc: Cảnh báo nguy hiểm nghiêm trọng (người trong vùng nguy hiểm) escalate ngay tới người phụ trách (HITL); tôn trọng quyền riêng tư (làm mờ danh tính, chỉ lưu vi phạm); bảo mật dữ liệu hình ảnh; cân bằng độ chính xác/false alarm.

## Giải pháp (Solution)

Sản phẩm giám sát an toàn tự động bằng Computer Vision:
- Feature 1: **Phát hiện thiếu PPE & xâm nhập vùng cấm** bằng YOLO pretrained và OpenCV polygon zone.
- Feature 2: **Cảnh báo realtime** thông qua FastAPI WebSocket cho Frontend React.
- Feature 3: **Quản lý & Thống kê vi phạm** lưu trữ vào PostgreSQL, Dashboard theo khu vực và ca.
- Feature 4: **Đảm bảo Privacy** tự động làm mờ khuôn mặt danh tính người vi phạm.

## Target User

- Primary: Cán bộ an toàn (Safety Officer) - Nhận cảnh báo realtime, đánh giá vi phạm, escalate.
- Secondary: Quản lý khu vực (Zone Manager) - Theo dõi thống kê tuân thủ, dashboard.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Computer Vision | Python, Ultralytics YOLO, OpenCV, ByteTrack |
| Backend | FastAPI + SQLAlchemy |
| Frontend | React + TypeScript + Vite |
| Database | PostgreSQL |
| DevOps | Docker Compose |

## Quick Start

```bash
# 1. Clone repo
git clone https://github.com/AI20K-Build-Cohort-2/P-047.git
cd P-047

# 2. Setup environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Start Backend & Database
docker-compose up -d db
uvicorn backend.app.main:app --reload

# 4. Start Frontend
cd frontend
npm install
npm run dev
```

## Project Structure

Chi tiết về cấu trúc thư mục dự án (bao gồm cấu trúc hiện tại và định hướng kiến trúc tương lai) đã được chuyển sang tài liệu riêng:

👉 **[docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)**

### Tóm tắt nhanh:
- **`backend/`**: Modular Monolith FastAPI Backend (REST API, WebSocket, AI Safety Agent LLM, SQLAlchemy/PostgreSQL, Pytest).
- **`vision/`**: Computer Vision Pipeline (YOLO detection, ByteTrack tracking, Polygon zone rule check, Privacy face blurring).
- **`frontend/`**: React + TypeScript + Vite Dashboard UI cho cán bộ an toàn.
- **`docs/`**: Tài liệu kiến trúc, PRD, cấu trúc dự án và hướng dẫn.
- **`data/`**: Video stream mẫu và dữ liệu kiểm thử.


## License

MIT
