# Benchmark scripts

`configure_railway_hls.sh` synchronizes the shared HLS signing secret and
Railway service-reference variables to `p047-app` and `streamer`. It reads
`HLS_TOKEN_SECRET` from the process environment first, otherwise from the
gitignored `.env.production`, and never prints the value:

```bash
./scripts/configure_railway_hls.sh
```

The default environment is `production`, and both services are redeployed only
after all variables have been written. Use `--no-redeploy` to update variables
without deploying, or `--project PROJECT_ID` when this checkout is not linked
to the intended Railway project. The private streamer port defaults to `8080`;
override it with `--streamer-port PORT` only when the runtime listens elsewhere.
Run `--help` for service-name overrides.

`build_streamer.sh` builds the standalone mock camera streamer image from the
repository root. It defaults to `nguyennaht4/streamer:dev`; pass another image
tag as the first argument when needed:

```bash
./scripts/build_streamer.sh
./scripts/build_streamer.sh DOCKERHUB_USERNAME/streamer:dev
```

`push_streamer.sh` builds and publishes the streamer image to Docker Hub. Run
`docker login` first, or use an existing Docker credential helper. It accepts
the Docker Hub image name and tag separately:

```bash
docker login
./scripts/push_streamer.sh
./scripts/push_streamer.sh DOCKERHUB_USERNAME/p047-streamer v1.0.0
```

The default image is `nguyennaht4/streamer:dev`. Set `DOCKERHUB_IMAGE` to
change the default image name without passing an argument:

```bash
DOCKERHUB_IMAGE=DOCKERHUB_USERNAME/p047-streamer ./scripts/push_streamer.sh
```

`push_app.sh` builds and publishes the main P-047 app image from the root
`Dockerfile`. Its default image is `nguyennaht4/p047:latest`:

```bash
docker login
./scripts/push_app.sh
./scripts/push_app.sh DOCKERHUB_USERNAME/p047 v1.0.0
```

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

`benchmark_privacy.py` measures the server-side privacy stage: one YuNet call, face/person fallback blur and JPEG encoding. It uses a generated 1280×720 frame by default or the first frame from an image/video:

```bash
PYTHONPATH=. .venv/bin/python scripts/benchmark_privacy.py \
  --input /path/to/authorized-test-image.jpg \
  --output data/privacy-benchmark.json
```

The input is treated as one canonical person box so the report also identifies whether YuNet found a face or used the person-head fallback. Do not commit test media containing personal data.

`bootstrap_legacy_sqlite.py` is called by `make db-upgrade`. It recognizes the former local
SQLite schema that predates Alembic, writes a timestamped `.bak` backup beside the database,
adds only the missing occurrence migration column/index, and stamps the known schema revision.
It never creates tables from current ORM metadata; later schema remains owned by ordered Alembic
revisions. New and already-versioned databases are unchanged; PostgreSQL is never bootstrapped
by this script.

`production_start.py` is the Docker entrypoint. It validates the approved model artifacts and
persistent data mount, safely adopts a recognized legacy SQLite database, upgrades Alembic to
head, verifies that head, then starts one Uvicorn worker. `docker_smoke.py` checks a running
local MVP; `backup_data.py` archives `data/` for the Docker-local backup runbook.
`restore_data.py` restores an archive only into an empty data directory after Compose is stopped.

`test_snapshot_bucket.py` loads `.env.production` and checks the configured S3-compatible
snapshot storage by uploading a generated 1×1 JPEG, reading it back with a checksum comparison,
then deleting it. To test exact bytes from a local file instead, provide `--file path/to/file`.
