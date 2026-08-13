# Benchmark scripts

`benchmark_model.py` measures inference-only latency and throughput for a YOLO checkpoint.
It defaults to the repository test video and the dedicated person model:

```bash
PYTHONPATH=. .venv/bin/python scripts/benchmark_model.py
```

To simulate the frontend/backend flow where every frame runs person detection followed by PPE
detection, use `--pipeline`:

```bash
PYTHONPATH=. .venv/bin/python scripts/benchmark_model.py \
  --pipeline --warmup 5 --iterations 30 --frames 30
```

The pipeline result is the combined latency and FPS for both models on one frame. It excludes
video decoding and WebSocket/network time, but includes both Ultralytics preprocessing, inference,
and postprocessing calls.

To benchmark the PPE model and save machine-readable output:

```bash
PYTHONPATH=. .venv/bin/python scripts/benchmark_model.py \
  --model models/ppe_yolov8n.pt \
  --output data/model-benchmark.json
```

The report includes mean/min/max/P50/P95/P99 latency in milliseconds and throughput in FPS.
Video decoding is excluded from the timing; preprocessing, model inference, and postprocessing
inside Ultralytics are included. Run the same command on the same hardware when comparing models.

`bootstrap_legacy_sqlite.py` is called by `make db-upgrade`. It recognizes the former local
SQLite schema that predates Alembic, writes a timestamped `.bak` backup beside the database,
adds the missing occurrence migration column, and stamps the known schema revision. New and
already-versioned databases are unchanged; PostgreSQL is never bootstrapped by this script.

`production_start.py` is the Docker entrypoint. It validates the approved model artifacts and
persistent data mount, safely adopts a recognized legacy SQLite database, upgrades Alembic to
head, verifies that head, then starts one Uvicorn worker. `docker_smoke.py` checks a running
local MVP; `backup_data.py` archives `data/` for the Docker-local backup runbook.
`restore_data.py` restores an archive only into an empty data directory after Compose is stopped.
