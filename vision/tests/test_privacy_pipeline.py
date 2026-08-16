import numpy as np
import pytest

from vision.pipeline import PrivacyRedactionError, annotate_snapshot, redact_person_head_regions


def _patterned_frame() -> np.ndarray:
    rows, columns = np.indices((100, 120))
    frame = np.zeros((100, 120, 3), dtype=np.uint8)
    frame[:, :, 0] = (rows * 13 + columns * 7) % 255
    frame[:, :, 1] = (rows * 5 + columns * 17) % 255
    frame[:, :, 2] = (rows * 19 + columns * 3) % 255
    return frame


def detection(class_name: str, bbox: list[int], class_id: int = 0) -> dict:
    return {
        "class_id": class_id,
        "class_name": class_name,
        "bbox": bbox,
        "confidence": 0.9,
        "person_index": None,
    }


def test_person_head_fallback_redacts_a_person_without_a_detected_face():
    frame = _patterned_frame()

    result = redact_person_head_regions(
        frame,
        [{"bbox": [20, 10, 80, 90], "confidence": 0.9, "inside_zone": False}],
    )

    assert result["used_person_fallback"] is True
    assert result["redacted_regions"] == [[20, 10, 80, 42]]
    assert not np.array_equal(result["image"][10:42, 20:80], frame[10:42, 20:80])
    assert np.array_equal(result["image"][42:90, 20:80], frame[42:90, 20:80])


def test_multiple_canonical_people_are_all_redacted():
    frame = _patterned_frame()
    people = [
        {"bbox": [10, 10, 50, 90], "confidence": 0.9, "inside_zone": False},
        {"bbox": [65, 10, 110, 90], "confidence": 0.9, "inside_zone": True},
    ]

    result = redact_person_head_regions(frame, people)

    assert result["used_person_fallback"] is True
    assert result["redacted_regions"] == [[10, 10, 50, 42], [65, 10, 110, 42]]
    assert not np.array_equal(result["image"][10:42, 10:50], frame[10:42, 10:50])
    assert not np.array_equal(result["image"][10:42, 65:110], frame[10:42, 65:110])


def test_snapshot_without_a_redaction_candidate_fails_closed():
    with pytest.raises(PrivacyRedactionError, match="no canonical person"):
        redact_person_head_regions(_patterned_frame(), [])


def test_snapshot_annotation_draws_person_and_hat_boxes_without_mutating_input():
    frame = np.zeros((100, 120, 3), dtype=np.uint8)

    annotated = annotate_snapshot(
        frame,
        [{"bbox": [10, 20, 40, 90], "confidence": 0.9, "inside_zone": True}],
        [
            detection("person", [0, 0, 5, 5]),
            detection("hat", [60, 30, 90, 60]),
        ],
    )

    assert np.array_equal(frame, np.zeros((100, 120, 3), dtype=np.uint8))
    assert annotated[20, 10].tolist() == [64, 73, 255]
    assert annotated[30, 60].tolist() == [11, 158, 245]
    assert np.array_equal(annotated[0, 0], frame[0, 0])
