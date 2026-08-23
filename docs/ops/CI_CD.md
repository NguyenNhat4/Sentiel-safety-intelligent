# CI/CD And Railway Release

## CI Gates

Pull requests and `main` run:

- Ruff lint and formatting for `src/`, `backend/` and `vision/`.
- Root, backend and Vision pytest suites.
- Frontend lint, type-check, tests and production build.
- Application Docker build when Docker inputs change.

The production image contains FastAPI, the React build, Vision integration and
media decoding dependencies. It does not contain a Streamer or MediaMTX service.

## Railway Resources

- `p047-app`: application and direct-file inference runtime.
- PostgreSQL: configuration, sessions and events.
- Railway Bucket in Singapore: canonical uploaded images/videos and redacted snapshots.
- Persistent volume mounted at `/app/data/media-assets`: legacy assets and OpenCV read-through cache.
- Optional Safety Vision worker.
- Optional S3-compatible storage for reviewed redacted snapshots.

Set `MEDIA_ASSET_DIR=/app/data/media-assets` and `MEDIA_STORAGE_BACKEND=s3`. Browser
uploads and playback use presigned bucket requests; credentials stay in Railway
variables. Do not store uploaded media only on the image filesystem because Railway
deployment filesystems are ephemeral.

## Release Contract

CI success allows the application image to be published. The deployment workflow
redeploys `p047-app` and waits for `/health`. Operational success requires:

1. Railway deployment reaches terminal `SUCCESS`.
2. PostgreSQL is reachable and migrations are applied.
3. The media volume is writable by the application user.
4. Public health and authenticated upload/list smoke checks pass.

Use a known-good immutable deployment/image for rollback. Never edit or remove an
already-applied Alembic revision.
