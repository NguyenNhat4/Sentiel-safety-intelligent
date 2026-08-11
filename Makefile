.PHONY: setup py-setup env-setup run test lint format check clean frontend-install frontend-dev frontend-lint frontend-type-check frontend-test frontend-build

VENV_BIN = .venv/bin

setup: py-setup frontend-install env-setup

py-setup:
	uv sync

env-setup:
	@if [ ! -f .env ]; then cp .env.example .env && echo "Created .env from .env.example"; fi

run: frontend-build
	$(VENV_BIN)/uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

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
	npm --prefix frontend run build

test:
	PYTHONPATH=. $(VENV_BIN)/pytest tests/ -v && PYTHONPATH=. $(VENV_BIN)/pytest backend/tests/ vision/tests/ -v

lint:
	$(VENV_BIN)/ruff check src/ backend/ vision/

format:
	$(VENV_BIN)/ruff format --check src/ backend/ vision/

check: lint format frontend-lint frontend-type-check frontend-test frontend-build test

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
