import numpy as np
import pytest

from vision.pipeline import PrivacyRedactionError, redact_identity_regions


def _patterned_frame() -> np.ndarray:
    rows, columns = np.indices((100, 120))
    frame = np.zeros((100, 120, 3), dtype=np.uint8)
    frame[:, :, 0] = (rows * 13 + columns * 7) % 255
    frame[:, :, 1] = (rows * 5 + columns * 17) % 255
    frame[:, :, 2] = (rows * 19 + columns * 3) % 255
    return frame


def detection(class_name: str, bbox: list[int]) -> dict:
    return {
        "class_id": 0,
        "class_name": class_name,
        "bbox": bbox,
        "confidence": 0.9,
        "person_index": None,
    }


def test_person_head_fallback_redacts_a_person_without_a_detected_face():
    frame = _patterned_frame()

    result = redact_identity_regions(frame, [detection("person", [20, 10, 80, 90])])

    assert result["used_person_fallback"] is True
    assert result["redacted_regions"] == [[20, 10, 80, 42]]
    assert not np.array_equal(result["image"][10:42, 20:80], frame[10:42, 20:80])
    assert np.array_equal(result["image"][42:90, 20:80], frame[42:90, 20:80])


def test_detected_identity_regions_for_multiple_people_are_all_redacted():
    frame = _patterned_frame()
    detections = [
        detection("person", [10, 10, 50, 90]),
        detection("face", [20, 18, 40, 38]),
        detection("person", [65, 10, 110, 90]),
        detection("head", [75, 16, 100, 42]),
    ]

    result = redact_identity_regions(frame, detections)

    assert result["used_person_fallback"] is False
    assert result["redacted_regions"] == [[20, 18, 40, 38], [75, 16, 100, 42]]
    assert not np.array_equal(result["image"][18:38, 20:40], frame[18:38, 20:40])
    assert not np.array_equal(result["image"][16:42, 75:100], frame[16:42, 75:100])


def test_snapshot_without_a_redaction_candidate_fails_closed():
    with pytest.raises(PrivacyRedactionError, match="no face, head, or person"):
        redact_identity_regions(_patterned_frame(), [detection("tool", [20, 10, 80, 90])])
