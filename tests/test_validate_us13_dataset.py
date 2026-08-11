import importlib.util
import json
from pathlib import Path

SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "validate_us13_dataset.py"
SPEC = importlib.util.spec_from_file_location("validate_us13_dataset", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def valid_video(**overrides: object) -> dict[str, object]:
    video: dict[str, object] = {
        "video_id": "VID_S01_001",
        "scenario_id": "S01",
        "split": "calibration",
        "media_uri": "approved-storage://p047/VID_S01_001.mp4",
        "media_sha256": "a" * 64,
        "annotation_path": "annotations/VID_S01_001.json",
        "annotation_sha256": "b" * 64,
        "consent_record_id": "CONSENT_001",
    }
    video.update(overrides)
    return video


def write_manifest(tmp_path: Path, videos: list[dict[str, object]]) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "dataset_id": "p047-custom-eval",
                "dataset_version": "1.0.0",
                "annotation_schema_version": "1.0.0",
                "split_policy": "grouped_by_video_and_scenario",
                "videos": videos,
            }
        ),
        encoding="utf-8",
    )
    return path


def test_valid_manifest_has_no_errors(tmp_path: Path) -> None:
    assert MODULE.validate_manifest(write_manifest(tmp_path, [valid_video()])) == []


def test_rejects_duplicate_video_and_scenario_split_leakage(tmp_path: Path) -> None:
    manifest = write_manifest(
        tmp_path,
        [valid_video(), valid_video(video_id="VID_S01_002", split="final")],
    )

    errors = MODULE.validate_manifest(manifest)

    assert "Scenario leaks across splits: S01" in errors
