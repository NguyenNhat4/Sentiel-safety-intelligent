"""One-time copy of legacy volume media into the configured S3 bucket."""

from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy import select

from backend.app.core.config import get_settings
from backend.app.core.database import SessionLocal
from backend.app.integrations.media_storage import create_media_storage
from backend.app.models.media_asset import MediaAsset


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="copy objects and update PostgreSQL")
    parser.add_argument("--delete-local", action="store_true", help="remove volume files after each committed copy")
    args = parser.parse_args()
    settings = get_settings()
    settings.validate_media_storage()
    if settings.media_storage_backend != "s3":
        raise SystemExit("MEDIA_STORAGE_BACKEND must be s3")

    storage = create_media_storage(settings)
    with SessionLocal() as db:
        assets = list(db.scalars(select(MediaAsset).where(MediaAsset.storage_backend == "filesystem")))
        print(f"legacy_assets={len(assets)} apply={args.apply}")
        for asset in assets:
            source = Path(settings.media_asset_dir) / asset.storage_filename
            if not source.is_file():
                raise SystemExit(f"missing volume file for asset {asset.id}")
            key = f"media-assets/{asset.id}{source.suffix.casefold()}"
            if not args.apply:
                print(f"would_copy asset={asset.id} bytes={source.stat().st_size}")
                continue
            storage.put_file(key, source, asset.content_type)
            metadata = storage.head(key)
            if metadata.size_bytes != asset.size_bytes:
                storage.delete(key)
                raise SystemExit(f"bucket size mismatch for asset {asset.id}")
            asset.storage_filename = key
            asset.storage_backend = "s3"
            db.commit()
            if args.delete_local:
                source.unlink()
            print(f"copied asset={asset.id} bytes={metadata.size_bytes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
