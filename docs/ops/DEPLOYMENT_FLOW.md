# Deployment Flow

## Production Topology

```mermaid
flowchart LR
    Browser -->|HTTPS| App[p047-app]
    MediaVolume[(Railway Persistent Volume)] --> App
    App --> Postgres[(PostgreSQL)]
    App -. optional .-> Vision[Safety Vision Worker]
    App -. reviewed snapshots .-> S3[(S3-compatible Storage)]
```

Production no longer deploys Streamer or MediaMTX. Mount the application volume at
`/app/data/media-assets` and set `MEDIA_ASSET_DIR` to the same path.

## Release

```mermaid
flowchart TD
    Check[make check] --> Build[Build p047-app image]
    Build --> Push[Push immutable app image]
    Push --> Redeploy[Redeploy p047-app]
    Redeploy --> Poll[Poll Railway deployment]
    Poll -->|SUCCESS| Health[Verify public /health]
    Poll -->|FAILED or CRASHED| Logs[Inspect build and deploy logs]
```

`scripts/deploy_all_production.sh` runs focused US-29/frontend gates, publishes
the application image, redeploys `p047-app`, waits for terminal `SUCCESS`, then
checks the public health endpoint. A queued deployment is not release success.

## Required Runtime Configuration

| Variable/resource | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection |
| Railway volume at `/app/data/media-assets` | Durable uploaded media |
| `MEDIA_ASSET_DIR=/app/data/media-assets` | Backend asset directory |
| `MAX_MEDIA_ASSET_BYTES` | Per-upload size ceiling |
| `MEDIA_INFERENCE_MAX_FPS` | Bounded direct-file sampling rate |
| `SNAPSHOT_STORAGE_*` | Production redacted evidence storage |

Rollback uses a known-good app image/deployment. Database migrations are not
rewritten or removed during rollback; uploaded media remains on the volume.
