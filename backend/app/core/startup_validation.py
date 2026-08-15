"""Production startup validation shared by the container entrypoint and health API."""

from __future__ import annotations

import hashlib
from pathlib import Path

from backend.app.core.config import Settings

REQUIRED_MODEL_CHECKSUMS = {
    "yolo11n.pt": "0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1",
    "ppe_yolov8n.pt": "5449f62bd7cf30c01c7fd138db2729a38abcb4d5120449773fba475d54f30b62",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_runtime_files(settings: Settings) -> dict[str, bool]:
    """Fail before serving traffic when runtime files are missing or corrupt."""
    data_dir = Path(settings.operational_metrics_log_path).parent
    settings.validate_snapshot_storage()
    snapshot_dir = Path(settings.snapshot_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    if settings.snapshot_storage_backend == "filesystem":
        snapshot_dir.mkdir(parents=True, exist_ok=True)
    probe = data_dir / ".startup-write-probe"
    probe.write_text("ok", encoding="utf-8")
    probe.unlink()

    model_paths = (Path(settings.person_model_path), Path(settings.ppe_model_path))
    for model_path in model_paths:
        expected = REQUIRED_MODEL_CHECKSUMS.get(model_path.name)
        if expected is None:
            raise RuntimeError(f"Model is not approved for this MVP image: {model_path}")
        if not model_path.is_file():
            raise RuntimeError(f"Required model is missing: {model_path}")
        if _sha256(model_path) != expected:
            raise RuntimeError(f"Required model checksum does not match: {model_path}")

    return {"data_writable": True, "models_verified": True}
