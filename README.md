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

### Cấu trúc hiện tại (Current Project Structure)

Cấu trúc hiện tại là boilerplate mặc định được cung cấp từ AI20K Build Phase Template. Cấu trúc này ban đầu được thiết kế cho các Agent LangGraph thông thường:

```
├── src/
│   ├── agents/          # LangGraph Agent (graph, nodes, tools)
│   ├── api/             # FastAPI Backend
│   └── ...
├── tests/               # Unit/Integration tests
├── scripts/             # AI Logging hooks
├── docs/                # Documents & Guidebooks
├── eval/                # Evaluation results
└── presentation/        # Demo materials
```

**Giải thích:**
Đây là cấu trúc nguyên bản phù hợp cho bài toán Text-based AI Agent. Tuy nhiên, dự án Giám Sát An Toàn PPE phụ thuộc nhiều vào việc phân tích video thời gian thực bằng Computer Vision (YOLO/OpenCV) và yêu cầu một giao diện trực quan. Do đó, cấu trúc cũ không còn phù hợp và chưa tối ưu để tách biệt các luồng xử lý luồng hình ảnh (CV pipeline), frontend phức tạp (React) và API backend.

### Cấu trúc tương lai (Future Project Structure)

Trong các phase tiếp theo, dự án sẽ được refactor sang kiến trúc Modular Monolith mới để hỗ trợ tốt nhất cho hệ thống Computer Vision realtime như thiết kế:

```text
P-047/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── analysis_service.py
│   │   │   ├── event_service.py
│   │   │   └── statistics_service.py
│   │   └── main.py
│   ├── migrations/
│   └── tests/
│
├── vision/
│   ├── detection/
│   │   ├── person_detector.py
│   │   └── ppe_detector.py
│   ├── tracking/
│   ├── association/
│   ├── zones/
│   ├── privacy/
│   ├── rules/
│   ├── pipeline.py
│   └── tests/
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── features/
│   │   │   ├── monitor/
│   │   │   ├── alerts/
│   │   │   ├── events/
│   │   │   └── dashboard/
│   │   └── types/
│   └── package.json
│
├── data/
│   ├── demo/
│   ├── edge-cases/
│   └── expected-results.json
│
├── contracts/
│   ├── detection.schema.json
│   └── event.schema.json
│
├── docs/
│   ├── architecture.md
│   ├── rules.md
│   └── limitations.md
│
├── docker-compose.yml
└── README.md
```

**Giải thích:**
Cấu trúc mới được chia thành các phân hệ chức năng rõ ràng (separation of concerns):
1. **`vision/`**: Xử lý toàn bộ logic liên quan đến nhận diện hình ảnh/video đầu vào. Độc lập hoàn toàn với web framework, dễ dàng scale.
2. **`backend/`**: API gateway nhận kết quả phân tích từ `vision`, lưu trữ trạng thái vào database, xử lý rule vi phạm và đẩy cảnh báo realtime qua WebSocket tới người dùng.
3. **`frontend/`**: Ứng dụng client-side trực quan cho Cán bộ an toàn quản lý video live, xem cảnh báo vi phạm và dashboard báo cáo.
4. **`contracts/`**: Đóng vai trò là chuẩn giao tiếp trung gian (JSON schemas) đảm bảo các module có thể kết nối với nhau một cách thống nhất và dễ dàng mở rộng.

## License

MIT
