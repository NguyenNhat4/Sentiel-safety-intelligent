# Backend Design Decisions

## 2026-08-01: FastAPI + SQLAlchemy Modular Monolith Architecture
- **Reason:** Fast development speed, native async support for WebSockets, seamless integration with Python CV and AI ecosystem (YOLO/OpenCV/LangChain).
- **Rejected alternative:** Separate Microservices framework (high overhead for early MVP phase).
- **Constraint:** Maintain strict separation of concerns between `backend`, `vision`, and `frontend`.

## 2026-08-01: Dual DB Support (PostgreSQL for Prod / SQLite in-memory fallback for Tests)
- **Reason:** Allows instant running of fast unit and API integration test suites in CI/local without requiring active local PostgreSQL daemon.
- **Constraint:** Use standard SQLAlchemy ORM constructs compatible with both PostgreSQL and SQLite.

## 2026-08-01: Realtime Alerts via WebSocket & AI Safety Agent Fallback
- **Reason:** Safety officers require instantaneous alerts when critical danger zone intrusion occurs. Safety Agent provides immediate actionable escalation advice.
- **Constraint:** Provide rule-based recommendation fallback when OpenAI API key is not configured.

## 2026-08-01: Browser-driven frame inference baseline
- **Reason:** A sampled-frame API provides the shortest working path from local video playback to zone overlays and human review without a separate video worker.
- **Choice:** YOLO detects people; an HSV torso heuristic detects a high-visibility shirt for the controlled demo.
- **Constraint:** The heuristic is not production PPE detection and must be replaced by trained model weights before field evaluation.

## 2026-08-02: Binary WebSocket inference transport
- **Reason:** Sampled browser frames need low-overhead bidirectional transport while retaining the existing inference response contract.
- **Choice:** `/api/v1/ws/inference` accepts per-connection zone configuration, frame metadata, and binary JPEG frames; inference runs outside the async event loop and returns correlated JSON results.
- **Constraint:** The baseline processes one frame at a time and retains the REST frame endpoint for compatibility.
- **Zone-entry rule:** Review pauses are triggered by the detected person's bottom-center foot point entering the polygon; machine state continues to affect PPE violation severity, not zone-entry detection.
