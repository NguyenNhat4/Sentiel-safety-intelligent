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
