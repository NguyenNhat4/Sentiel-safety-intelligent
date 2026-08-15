"""Production startup validation shared by the container entrypoint and health API."""

from __future__ import annotations

import hashlib
from pathlib import Path

from backend.app.core.config import Settings

REQUIRED_MODEL_CHECKSUMS = {
    "yolo11m_safety.pt": "f53324f39d76da6017d41038e74f95b3dceb33524738721e03f69f3ea58a1ece",
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

    model_paths = (Path(settings.ppe_model_path),)
    for model_path in model_paths:
        expected = REQUIRED_MODEL_CHECKSUMS.get(model_path.name)
        if expected is None:
            raise RuntimeError(f"Model is not approved for this MVP image: {model_path}")
        if not model_path.is_file():
            raise RuntimeError(f"Required model is missing: {model_path}")
        if _sha256(model_path) != expected:
            raise RuntimeError(f"Required model checksum does not match: {model_path}")

    return {"data_writable": True, "models_verified": True}
