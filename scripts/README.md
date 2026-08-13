# Benchmark scripts

`benchmark_model.py` measures inference-only latency and throughput for a YOLO checkpoint.
It defaults to the repository test video and the unified YOLO11m Safety runtime model:

```bash
PYTHONPATH=. .venv/bin/python scripts/benchmark_model.py
```

To match the frontend/backend flow where one call returns person, hat and vest, use `--pipeline`:

```bash
PYTHONPATH=. .venv/bin/python scripts/benchmark_model.py \
  --pipeline --warmup 5 --iterations 30 --frames 30
```

The pipeline result is latency and FPS for the single YOLO11m Safety call on one frame. It excludes
video decoding and WebSocket/network time, but includes Ultralytics preprocessing, inference and
postprocessing.

To benchmark the PPE model and save machine-readable output:

```bash
PYTHONPATH=. .venv/bin/python scripts/benchmark_model.py \
  --model models/yolo11m_safety.pt \
  --output data/model-benchmark.json
```

Pipeline mode matches runtime filtering: YOLO11m Safety uses source classes `[0, 3, 4]`
(`hat`, `person`, `vest`) exactly once per frame. Class `3` supplies canonical people
for tracking and zone rules. Single-model mode deliberately measures all checkpoint
classes unless a future CLI option states otherwise.

The report includes mean/min/max/P50/P95/P99 latency in milliseconds and throughput in FPS.
Video decoding is excluded from the timing; preprocessing, model inference, and postprocessing
inside Ultralytics are included. Run the same command on the same hardware when comparing models.

`bootstrap_legacy_sqlite.py` is called by `make db-upgrade`. It recognizes the former local
SQLite schema that predates Alembic, writes a timestamped `.bak` backup beside the database,
adds the missing occurrence migration column, and stamps the known schema revision. New and
already-versioned databases are unchanged; PostgreSQL is never bootstrapped by this script.
