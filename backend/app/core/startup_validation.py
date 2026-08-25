"""Production startup validation shared by the container entrypoint and health API."""

from __future__ import annotations

import hashlib
from pathlib import Path

import cv2

from backend.app.core.config import Settings

REQUIRED_MODEL_CHECKSUMS = {
    "yolo11m_safety.pt": "e5b2ad353a33579e821ed9be77ed8406b7bac14bb8abf5d6db77b071ea021218",
    "face_detection_yunet_2023mar.onnx": "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
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
    settings.validate_media_storage()
    snapshot_dir = Path(settings.snapshot_dir)
    media_asset_dir = Path(settings.media_asset_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    media_asset_dir.mkdir(parents=True, exist_ok=True)
    if settings.snapshot_storage_backend == "filesystem":
        snapshot_dir.mkdir(parents=True, exist_ok=True)
    probe = data_dir / ".startup-write-probe"
    probe.write_text("ok", encoding="utf-8")
    probe.unlink()
    media_probe = media_asset_dir / ".startup-write-probe"
    media_probe.write_text("ok", encoding="utf-8")
    media_probe.unlink()

    if not hasattr(cv2, "FaceDetectorYN_create"):
        raise RuntimeError("Installed OpenCV build does not provide FaceDetectorYN")

    model_paths = [Path(settings.face_detector_model_path)]
    if settings.vision_provider == "local":
        model_paths.append(Path(settings.ppe_model_path))
    for model_path in model_paths:
        expected = REQUIRED_MODEL_CHECKSUMS.get(model_path.name)
        if expected is None:
            raise RuntimeError(f"Model is not approved for this MVP image: {model_path}")
        if not model_path.is_file():
            raise RuntimeError(f"Required model is missing: {model_path}")
        if _sha256(model_path) != expected:
            raise RuntimeError(f"Required model checksum does not match: {model_path}")

    return {"data_writable": True, "media_assets_writable": True, "models_verified": True}
