"""Verify the production S3-compatible snapshot bucket without exposing secrets.

Run from the repository root:
    PYTHONPATH=. .venv/bin/python scripts/test_snapshot_bucket.py
    PYTHONPATH=. .venv/bin/python scripts/test_snapshot_bucket.py --file path/to/image.jpg
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import cv2
import numpy as np
from dotenv import load_dotenv

from backend.app.core.config import Settings
from backend.app.integrations.snapshot_storage import SnapshotStorageError, create_snapshot_storage

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_ENV_FILE = REPOSITORY_ROOT / ".env.production"


def storage_error_kind(error: SnapshotStorageError) -> str:
    cause = error.__cause__
    if cause is None:
        return type(error).__name__
    response = getattr(cause, "response", None)
    error_code = response.get("Error", {}).get("Code") if isinstance(response, dict) else None
    return error_code or type(cause).__name__


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test production snapshot bucket write/read/delete.")
    parser.add_argument(
        "--file",
        type=Path,
        help="Optional file to upload. The object is deleted after the checksum check.",
    )
    return parser.parse_args()


def test_content(file_path: Path | None) -> bytes:
    if file_path is not None:
        if not file_path.is_file():
            raise ValueError(f"Test file does not exist: {file_path}")
        return file_path.read_bytes()

    success, encoded = cv2.imencode(".jpg", np.zeros((1, 1, 3), dtype=np.uint8))
    if not success:  # pragma: no cover - OpenCV image encoding is a runtime prerequisite
        raise RuntimeError("Could not create the JPEG test image")
    return encoded.tobytes()


def main() -> int:
    arguments = parse_arguments()
    if not PRODUCTION_ENV_FILE.is_file():
        print("ERROR: .env.production was not found; no bucket request was made.", file=sys.stderr)
        return 2

    load_dotenv(PRODUCTION_ENV_FILE, override=True)
    settings = Settings()
    if settings.snapshot_storage_backend != "s3":
        print("ERROR: SNAPSHOT_STORAGE_BACKEND must be s3; no bucket request was made.", file=sys.stderr)
        return 2

    try:
        content = test_content(arguments.file)
        storage = create_snapshot_storage(settings)
        key = storage.put(content)
    except (OSError, RuntimeError, SnapshotStorageError, ValueError) as exc:
        print(f"ERROR: bucket write failed ({storage_error_kind(exc)}): {exc}", file=sys.stderr)
        return 1

    try:
        received = storage.get(key)
        if hashlib.sha256(received).digest() != hashlib.sha256(content).digest():
            print(f"ERROR: bucket read checksum mismatch for {key}", file=sys.stderr)
            return 1
        print(f"OK: bucket write/read succeeded for {key}")
        return 0
    except SnapshotStorageError as exc:
        print(f"ERROR: bucket read failed ({storage_error_kind(exc)}): {exc}", file=sys.stderr)
        return 1
    finally:
        try:
            storage.delete(key)
        except SnapshotStorageError as exc:
            print(
                f"WARNING: could not delete test object {key} ({storage_error_kind(exc)}): {exc}",
                file=sys.stderr,
            )


if __name__ == "__main__":
    raise SystemExit(main())
