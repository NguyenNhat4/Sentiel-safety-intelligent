# Backend Module - PPE & Zone Safety Monitoring System

## Overview
Phân hệ `backend` là FastAPI web application theo kiến trúc Modular Monolith. Phân hệ đảm nhận vai trò API Gateway, quản lý trạng thái phiên phân tích video, ghi nhận và xử lý các sự kiện vi phạm quy định an toàn (PPE & xâm nhập vùng nguy hiểm), đẩy cảnh báo thời gian thực qua WebSocket, và cung cấp AI Safety Agent tư vấn xử lý sự cố.

## Directory Structure
```text
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── agent.py       # AI Safety Agent chat & recommendation endpoint
│   │       ├── analysis.py    # Video stream analysis orchestration
│   │       ├── events.py      # Safety violation event CRUD & acknowledgment
│   │       ├── statistics.py  # Safety compliance & violation metrics
│   │       └── websocket.py   # WebSocket alert streaming (/ws/alerts)
│   │   └── router.py          # API v1 aggregator
│   ├── core/
│   │   ├── config.py          # Pydantic Settings, CORS & env configuration
│   │   └── database.py        # SQLAlchemy Engine & session setup
│   ├── models/
│   │   └── event.py           # SafetyEvent ORM model
│   ├── schemas/
│   │   ├── analysis.py        # Analysis DTO schemas
│   │   ├── event.py           # Event DTO schemas
│   │   └── statistics.py     # Statistics DTO schemas
│   ├── services/
│   │   ├── analysis_service.py # Stream analysis state management
│   │   ├── event_service.py    # Event database CRUD service
│   │   ├── llm_service.py     # AI Agent reasoning service (LangChain / OpenAI)
│   │   └── statistics_service.py # Compliance & metric calculations
│   └── main.py                # FastAPI Application entrypoint & lifespan
├── migrations/                # Alembic database migrations
├── tests/                     # Pytest suite for backend endpoints & services
├── DECISIONS.md               # Technical & Architectural decisions log for backend
├── PROGRESS.md                # Task progress, state & next steps for backend
└── README.md                  # This documentation file
```

## Setup & Running
```bash
# Run backend development server
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# Run backend test suite
PYTHONPATH=. .venv/bin/pytest backend/tests -v
```
