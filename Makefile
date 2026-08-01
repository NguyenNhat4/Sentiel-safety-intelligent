.PHONY: run test lint format check clean

VENV_BIN = .venv/bin

run:
	$(VENV_BIN)/uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

test:
	PYTHONPATH=. $(VENV_BIN)/pytest tests/ -v && PYTHONPATH=. $(VENV_BIN)/pytest backend/tests/ -v

lint:
	$(VENV_BIN)/ruff check src/ backend/

format:
	$(VENV_BIN)/ruff format --check src/ backend/

check: lint format test

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
