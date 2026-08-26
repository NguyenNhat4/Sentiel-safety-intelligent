# P-047 Safety Monitoring

P-047 is a React 19 and FastAPI prototype that evaluates uploaded image/video
assets for person, PPE and danger-zone safety rules. PostgreSQL stores
configuration, sessions and reviewed events; the backend reads media directly
from a private application volume and calls the local or remote Vision facade.

## Requirements

- Python 3.11 with `uv`
- Node.js 22
- PostgreSQL
- Docker for container workflows

## Setup

```bash
make setup
make run
```

`make setup` installs locked dependencies, creates `.env.development` when
missing and applies Alembic migrations. `make run` rebuilds the frontend and
starts FastAPI at <http://localhost:8000>.

The local media library defaults to `data/media-assets`. Configure:

```dotenv
MEDIA_ASSET_DIR=data/media-assets
MAX_MEDIA_ASSET_BYTES=1073741824
MEDIA_INFERENCE_MAX_FPS=2
```

## Demo Workflow

1. Sign in as `system_admin` and upload a named image/video in **Thư viện media**.
2. Sign in as `safety_manager`; Live Monitor always displays Camera 1 through 4.
3. Select a camera slot to open its internal configuration page. This page has no sidebar item.
4. Select a READY asset, preview it, configure zones/PPE and choose **Lưu cấu hình**.
5. Back on Live Monitor, choose **Chạy mô phỏng** to start all valid cameras.
6. Video sessions stop at EOF and expose Replay per camera; images infer exactly once.

Streamer, MediaMTX, HLS, RTSP, MJPEG and Connect/Disconnect are not part of the
runtime or deployment.

## Checks

```bash
make check
```

Focused commands:

```bash
PYTHONPATH=. .venv/bin/pytest backend/tests vision/tests -v
npm --prefix frontend run test
npm --prefix frontend run type-check
npm --prefix frontend run build
```

## Docker

```bash
docker compose up -d --build
```

Compose starts PostgreSQL and the application. It mounts
`./data/media-assets:/app/data/media-assets` for uploaded assets.

## Railway

Production requires:

- `p047-app` with a persistent volume mounted at `/app/data/media-assets`
- PostgreSQL with `DATABASE_URL`
- `MEDIA_ASSET_DIR=/app/data/media-assets`
- Optional S3-compatible snapshot variables for production evidence readiness
- Optional separate Safety Vision worker when `VISION_PROVIDER=remote`
- `safety_vision_v2` for PostgreSQL-backed tracking continuity across stateless GPU replicas; v1 remains the rollback contract

Release automation deploys only `p047-app`:

```bash
./scripts/deploy_all_production.sh
```

A release is successful only after Railway reports terminal `SUCCESS` and the
public `/health` response is verified. Uploaded media must never rely on the
ephemeral image filesystem.

## Architecture

Production code has three owners: `backend/`, `frontend/` and `vision/`.
Executable API, schema, ORM, migration, frontend wire types and tests are the
runtime source of truth. Start repository context discovery at `context-map.md`.
