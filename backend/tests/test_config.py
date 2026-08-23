import pytest
from pydantic import ValidationError

from backend.app.core.config import Settings


def test_settings_load_development_environment_file_by_default() -> None:
    assert Settings.model_config["env_file"] == ".env.development"


def test_person_detection_confidence_defaults_to_current_runtime_value() -> None:
    assert Settings(_env_file=None).person_detection_confidence == 0.6


def test_person_detection_confidence_loads_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("PERSON_DETECTION_CONFIDENCE", "0.42")

    assert Settings(_env_file=None).person_detection_confidence == 0.42


@pytest.mark.parametrize("value", [0.0, -0.1, 1.01])
def test_person_detection_confidence_rejects_out_of_range_values(value: float) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, person_detection_confidence=value)


def test_ppe_detection_confidence_defaults_to_02() -> None:
    assert Settings(_env_file=None).ppe_detection_confidence == 0.2


def test_ppe_detection_confidence_loads_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("PPE_DETECTION_CONFIDENCE", "0.27")

    assert Settings(_env_file=None).ppe_detection_confidence == 0.27


@pytest.mark.parametrize("value", [0.0, -0.1, 1.01])
def test_ppe_detection_confidence_rejects_out_of_range_values(value: float) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ppe_detection_confidence=value)


def test_yolo_inference_image_size_defaults_to_960() -> None:
    assert Settings(_env_file=None).yolo_inference_image_size == 960


def test_yolo_inference_image_size_loads_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("YOLO_INFERENCE_IMAGE_SIZE", "1280")

    assert Settings(_env_file=None).yolo_inference_image_size == 1280


@pytest.mark.parametrize("value", [0, 641, 4128])
def test_yolo_inference_image_size_rejects_invalid_values(value: int) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, yolo_inference_image_size=value)


def test_ppe_temporal_frames_defaults_to_10() -> None:
    assert Settings(_env_file=None).ppe_temporal_frames == 10


def test_ppe_temporal_frames_loads_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("PPE_TEMPORAL_FRAMES", "7")

    assert Settings(_env_file=None).ppe_temporal_frames == 7


@pytest.mark.parametrize("value", [0, 61])
def test_ppe_temporal_frames_rejects_invalid_values(value: int) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ppe_temporal_frames=value)


def test_settings_loads_production_env_file() -> None:
    assert Settings.model_config["env_file"] == ".env.production"
