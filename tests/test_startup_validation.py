import hashlib

import pytest

from backend.app.core.config import Settings
from backend.app.core.startup_validation import REQUIRED_MODEL_CHECKSUMS, validate_runtime_files


def test_validate_runtime_files_accepts_approved_models(tmp_path, monkeypatch):
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    safety = model_dir / "yolo11m_safety.onnx"
    safety.write_bytes(b"safety")
    monkeypatch.setitem(REQUIRED_MODEL_CHECKSUMS, safety.name, hashlib.sha256(b"safety").hexdigest())
    monkeypatch.chdir(tmp_path)

    result = validate_runtime_files(
        Settings(
            ppe_model_path=str(safety),
            operational_metrics_log_path="data/operational-metrics.jsonl",
            snapshot_dir="runtime/snapshots",
        )
    )

    assert result == {"data_writable": True, "models_verified": True}
    assert (tmp_path / "runtime" / "snapshots").is_dir()


def test_validate_runtime_files_rejects_missing_model(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(RuntimeError, match="Required model is missing"):
        validate_runtime_files(
            Settings(
                ppe_model_path="models/yolo11m_safety.onnx",
                operational_metrics_log_path="data/operational-metrics.jsonl",
            )
        )
