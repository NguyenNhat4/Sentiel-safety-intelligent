# Benchmark scripts

## Dọn dữ liệu local

`clean_local_data.py` xóa rows trong PostgreSQL local, giữ nguyên schema và
migration history, đồng thời dọn media uploads, snapshots và operational logs.
Script từ chối database Railway/production và bắt buộc cờ xác nhận:

```bash
make clean-local-data
```

Kiểm tra `DATABASE_URL` trong `.env.development` trước khi chạy. Lệnh này
không thể khôi phục dữ liệu đã xóa.

## Đồng bộ code lên Google Drive

`sync_code_to_google_drive.sh` dùng `rclone` để đồng bộ duy nhất các file
Python (`*.py`) trong `backend/app/` và `vision/`. Script không upload
`__pycache__`, `*.pyc`, `*.pyo`, test cache, model, media, tài liệu hoặc file
không phải Python. `rclone sync` cũng xóa trên thư mục Drive đích những file
Python đã bị xóa ở local, vì vậy hãy dùng một thư mục Drive riêng cho backup này.

### 1. Cài và kết nối Google Drive

Trên Ubuntu/Debian:

```bash
sudo apt update
sudo apt install rclone
rclone config
```

Trong `rclone config`:

1. Chọn `n` để tạo remote mới.
2. Đặt tên `gdrive`.
3. Chọn storage `drive` (Google Drive).
4. Có thể để trống `client_id` và `client_secret` cho tài khoản cá nhân.
5. Chọn quyền `drive` hoặc quyền phù hợp với tài khoản backup.
6. Chọn `auto config` và đăng nhập tài khoản Google trong trình duyệt.
7. Không chọn Shared Drive, trừ khi thư mục đích thuộc Shared Drive.

Kiểm tra kết nối mà không upload:

```bash
rclone lsd gdrive:
./scripts/sync_code_to_google_drive.sh --dry-run
```

### 2. Chạy đồng bộ

Mặc định code được đưa vào `gdrive:P-047-code/`:

```bash
./scripts/sync_code_to_google_drive.sh
```

Đổi tên remote hoặc thư mục đích bằng biến môi trường. Tên remote không chứa
dấu `:`:

```bash
GOOGLE_DRIVE_REMOTE=company-drive \
GOOGLE_DRIVE_DESTINATION=backups/P-047-code \
./scripts/sync_code_to_google_drive.sh
```

### 3. Tự động chạy mỗi 5 phút bằng cron

Lấy đường dẫn tuyệt đối của repository bằng `pwd`, sau đó mở cron:

```bash
crontab -e
```

Thêm một dòng, thay `/absolute/path/to/P-047` bằng đường dẫn thật:

```cron
*/5 * * * * /absolute/path/to/P-047/scripts/sync_code_to_google_drive.sh >> "$HOME/p047-drive-sync.log" 2>&1
```

Cron chạy với môi trường tối giản. Nếu `rclone` không nằm trong `PATH` của cron,
dùng đường dẫn trả về bởi `command -v rclone` trong `PATH` của crontab hoặc cài
`rclone` vào `/usr/bin`. File cấu hình mặc định nằm tại
`~/.config/rclone/rclone.conf`; không commit file này vì nó chứa token truy cập.

Chạy regression không dùng mạng sau khi sửa script:

```bash
./scripts/test_sync_code_to_google_drive.sh
```

`deploy_all_production.sh` runs the focused release gates, rebuilds and pushes
the application image, redeploys `p047-app`, waits for the new Railway deployment
to reach `SUCCESS`, and checks the application health endpoint:

```bash
./scripts/deploy_all_production.sh
```

The defaults target this project's production app service and image. Override
`RAILWAY_PROJECT_ID`, `RAILWAY_ENVIRONMENT`, app service, image name/tag, health
URL, or `DEPLOY_TIMEOUT_SECONDS` through environment variables when needed.
Production must mount a persistent volume at `MEDIA_ASSET_DIR`.

`migrate_media_assets_to_s3.py` copies legacy canonical files from that volume into
the configured media bucket, verifies object size, then updates one database row at
a time. Preview first, then apply after the S3 variables and migration are deployed:

```bash
python -m scripts.migrate_media_assets_to_s3
python -m scripts.migrate_media_assets_to_s3 --apply --delete-local
```

`container_entrypoint.sh` runs as container root only long enough to ensure the
Railway-mounted media directory belongs to `appuser`, then uses `gosu` so the
application and all media writes run without root privileges.

`push_app.sh` reads the three `VITE_*` build values from `.env.production`,
builds and publishes the main P-047 image, then asks Railway service `p047-app`
to redeploy from the latest configured image source. Its default image is
`nguyennhat4/p047:latest`:

```bash
docker login
./scripts/push_app.sh
./scripts/push_app.sh DOCKERHUB_USERNAME/p047 v1.0.0
```

The Railway CLI must be installed, authenticated and linked to the intended
project. Prefer an explicit project ID in automation:

```bash
RAILWAY_PROJECT_ID=YOUR_PROJECT_ID ./scripts/push_app.sh
```

Override the target or publish without a Railway mutation when needed:

```bash
RAILWAY_APP_SERVICE=web RAILWAY_ENVIRONMENT=staging ./scripts/push_app.sh
SKIP_RAILWAY_REDEPLOY=true ./scripts/push_app.sh
```

`railway redeploy --from-source` is intentional: it pulls the newly published
image instead of restarting the deployment that still references the previous
image digest. The command queues a deployment; verify its final status and
`/health` before treating the release as successful.

`benchmark_model.py` measures inference-only latency and throughput for a YOLO checkpoint.
It defaults to the repository test video and the unified YOLO11n Safety KD runtime model:

```bash
PYTHONPATH=. .venv/bin/python scripts/benchmark_model.py
```

To match the frontend/backend flow where one call returns person, hat and vest, use `--pipeline`:

```bash
PYTHONPATH=. .venv/bin/python scripts/benchmark_model.py \
  --pipeline --warmup 5 --iterations 30 --frames 30
```

The pipeline result is latency and FPS for the single YOLO11n Safety KD call on one frame. It excludes
video decoding and WebSocket/network time, but includes Ultralytics preprocessing, inference and
postprocessing.

To benchmark the PPE model and save machine-readable output:

```bash
PYTHONPATH=. .venv/bin/python scripts/benchmark_model.py \
  --model models/yolo11n_safety_kd_best.pt \
  --output data/model-benchmark.json
```

Pipeline mode matches runtime filtering: YOLO11n Safety KD uses source classes `[0, 3, 4]`
(`hat`, `person`, `vest`) exactly once per frame. Class `3` supplies canonical people
for tracking and zone rules. Single-model mode deliberately measures all checkpoint
classes unless a future CLI option states otherwise.

The report includes mean/min/max/P50/P95/P99 latency in milliseconds and throughput in FPS.
Video decoding is excluded from the timing; preprocessing, model inference, and postprocessing
inside Ultralytics are included. Run the same command on the same hardware when comparing models.

For a one-command CPU versus NVIDIA GPU comparison on another Linux machine, run:

```bash
make vision-worker-benchmark
```

The target builds the CUDA image, requires Docker GPU access, then runs the same YOLO11m Safety
checkpoint, classes `[0, 3, 4]`, ByteTrack pipeline, deterministic 640×640 frame, 10 warm-up calls
and 50 measured calls first on CPU and then on `cuda:0`. It prints mean/P50/P95 latency, FPS and
the GPU speedup. Model loading, warm-up, video decoding and HTTP/network time are excluded.

Use one authorized, repository-relative camera image for a more representative result:

```bash
make vision-worker-benchmark \
  BENCHMARK_INPUT=data/authorized-test.jpg \
  BENCHMARK_WARMUP=20 \
  BENCHMARK_ITERATIONS=100
```

Do not commit media containing personal data. CPU and GPU are intentionally measured sequentially
inside the same image and machine; compare runs only when `torch.cuda.is_available()` is true.

For an interactive image/video comparison with browser-to-worker latency, run:

```bash
make vision-worker-compare-ui
```

The target builds the same CUDA image, starts one container forced to `cpu` on port `8101` and one
container on `cuda:0` on port `8102`, waits for both `/ping` endpoints, and serves the developer UI
at <http://127.0.0.1:5173/vision-worker-compare.html>. Press `Ctrl+C` to stop and remove exactly
those two containers. Set `VISION_WORKER_API_KEY` before the command to enable the same worker key
on both, then enter it in both password fields in the page.

The page submits an image once or samples a locally played video at 1/2/5/10 FPS. It sends the same
frame to CPU and GPU concurrently, keeps at most one comparison cycle in flight, and reports
latest/mean/P50/P95 RTT, an indicative `1000 / mean` ceiling, GPU speedup, and skipped frames. Use
this for end-to-end responsiveness and visual overlays; use `make vision-worker-benchmark` for the
controlled sequential model-only comparison.

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
