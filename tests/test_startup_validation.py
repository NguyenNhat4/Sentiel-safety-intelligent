import hashlib

import pytest

from backend.app.core.config import Settings
from backend.app.core.startup_validation import REQUIRED_MODEL_CHECKSUMS, validate_runtime_files


def test_validate_runtime_files_accepts_approved_models(tmp_path, monkeypatch):
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    person = model_dir / "yolo11n.pt"
    ppe = model_dir / "ppe_yolov8n.pt"
    person.write_bytes(b"person")
    ppe.write_bytes(b"ppe")
    monkeypatch.setitem(REQUIRED_MODEL_CHECKSUMS, person.name, hashlib.sha256(b"person").hexdigest())
    monkeypatch.setitem(REQUIRED_MODEL_CHECKSUMS, ppe.name, hashlib.sha256(b"ppe").hexdigest())
    monkeypatch.chdir(tmp_path)

    result = validate_runtime_files(
        Settings(
            person_model_path=str(person),
            ppe_model_path=str(ppe),
            operational_metrics_log_path="data/operational-metrics.jsonl",
        )
    )

    assert result == {"data_writable": True, "models_verified": True}


def test_validate_runtime_files_rejects_missing_model(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(RuntimeError, match="Required model is missing"):
        validate_runtime_files(
            Settings(
                person_model_path="models/yolo11n.pt",
                ppe_model_path="models/ppe_yolov8n.pt",
                operational_metrics_log_path="data/operational-metrics.jsonl",
            )
        )
