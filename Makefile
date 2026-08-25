.PHONY: setup py-setup env-setup db-upgrade clean-local-data run vision-worker-run vision-worker-image vision-worker-gpu-image vision-worker-benchmark vision-worker-compare-ui e2e-demo test lint format check clean frontend-install frontend-dev frontend-lint frontend-type-check frontend-test frontend-build docker-build docker-up docker-down docker-smoke backup restore

BENCHMARK_INPUT ?=
BENCHMARK_WARMUP ?= 10
BENCHMARK_ITERATIONS ?= 50

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

clean-local-data:
	PYTHONPATH=. $(VENV_BIN)/python scripts/clean_local_data.py --yes

run: db-upgrade frontend-build
	set -a; . ./.env.development; set +a; $(VENV_BIN)/uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

vision-worker-run:
	$(VENV_BIN)/uvicorn backend.app.vision_worker:app --reload --host 0.0.0.0 --port 8100

vision-worker-image:
	docker build -f Dockerfile.ai -t p047-vision:dev .

vision-worker-gpu-image:
	docker build --platform linux/amd64 -f Dockerfile.ai.gpu -t p047-vision:gpu-dev .

vision-worker-benchmark: vision-worker-gpu-image
	docker run --rm --gpus all --volume "$(CURDIR):/workspace:ro" --workdir /workspace --entrypoint python p047-vision:gpu-dev scripts/benchmark_model.py --pipeline --tracking --compare-cpu-gpu $(if $(BENCHMARK_INPUT),--source "/workspace/$(BENCHMARK_INPUT)",--synthetic) --warmup $(BENCHMARK_WARMUP) --iterations $(BENCHMARK_ITERATIONS) --frames 1

vision-worker-compare-ui: vision-worker-gpu-image
	bash scripts/run_vision_compare_ui.sh

e2e-demo:
	PYTHONPATH=. $(VENV_BIN)/python scripts/e2e_demo.py

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
