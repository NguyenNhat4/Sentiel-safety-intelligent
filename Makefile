.PHONY: setup py-setup env-setup db-upgrade run streamer-run streamer-test e2e-demo e2e-streaming test lint format check clean frontend-install frontend-dev frontend-lint frontend-type-check frontend-test frontend-build docker-build docker-up docker-down docker-smoke backup restore

ifeq ($(OS),Windows_NT)
VENV_BIN = .venv/Scripts
else
VENV_BIN = .venv/bin
endif

setup: py-setup frontend-install env-setup db-upgrade

py-setup:
	uv sync

env-setup:
	@if [ ! -f .env.development ]; then cp .env.development.example .env.development && echo "Created .env.development from .env.development.example"; fi

db-upgrade:
	PYTHONPATH=. $(VENV_BIN)/python scripts/bootstrap_legacy_sqlite.py
	PYTHONPATH=. $(VENV_BIN)/alembic upgrade head

run: db-upgrade frontend-build
	set -a; . ./.env.development; set +a; docker compose up -d mediamtx; MEDIA_RTSP_ENABLED=true MEDIA_RTSP_ORIGIN=rtsp://p047_local_publisher:p047_local_only_change_me@localhost:8554 MEDIA_PUBLIC_ORIGIN=http://localhost:8888 HLS_UPSTREAM_ORIGIN=http://localhost:8888 $(VENV_BIN)/uvicorn streamer.app:app --host 0.0.0.0 --port 8001 & STREAMER_PID=$$!; trap 'kill $$STREAMER_PID; docker compose stop mediamtx' EXIT INT TERM; $(VENV_BIN)/uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

streamer-run:
	$(VENV_BIN)/uvicorn streamer.app:app --reload --host 0.0.0.0 --port 8001

streamer-test:
	PYTHONPATH=. $(VENV_BIN)/pytest streamer/tests/ -v

e2e-demo:
	PYTHONPATH=. $(VENV_BIN)/python scripts/e2e_demo.py

e2e-streaming:
	PYTHONPATH=. $(VENV_BIN)/python scripts/e2e_streaming.py

frontend-install:
	npm --prefix frontend ci

frontend-dev:
	npm --prefix frontend run dev

frontend-lint:
	npm --prefix frontend run lint

frontend-type-check:
	npm --prefix frontend run type-check

frontend-test:
	npm --prefix frontend run test

frontend-build:
	set -a; [ ! -f .env.development ] || . ./.env.development; set +a; npm --prefix frontend run build

docker-build:
	docker compose build

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

docker-smoke:
	$(VENV_BIN)/python scripts/docker_smoke.py

backup:
	$(VENV_BIN)/python scripts/backup_data.py

restore:
	@test -n "$(ARCHIVE)" || (echo "Usage: make restore ARCHIVE=backups/p047-data-...tar.gz" && exit 2)
	$(VENV_BIN)/python scripts/restore_data.py $(ARCHIVE)

test:
	PYTHONPATH=. $(VENV_BIN)/pytest tests/ streamer/tests/ -v && PYTHONPATH=. $(VENV_BIN)/pytest backend/tests/ vision/tests/ -v

lint:
	$(VENV_BIN)/ruff check src/ backend/ streamer/ vision/

format:
	$(VENV_BIN)/ruff format --check src/ backend/ streamer/ vision/

check: lint format frontend-lint frontend-type-check frontend-test frontend-build test

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
