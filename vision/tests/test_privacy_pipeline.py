import numpy as np
import pytest

from vision.api import PrivacyRedactionFacade
from vision.pipeline import (
    PrivacyRedactionError,
    annotate_snapshot,
    redact_identity_regions,
    redact_person_head_regions,
)


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


def face(bbox: list[int], confidence: float = 0.9) -> dict:
    return {"bbox": bbox, "confidence": confidence}


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


def test_yunet_face_is_expanded_and_replaces_person_fallback():
    frame = _patterned_frame()
    original = frame.copy()
    people = [{"bbox": [20, 10, 80, 90], "confidence": 0.9, "inside_zone": False}]

    result = redact_identity_regions(frame, people, [face([35, 20, 55, 40])])

    assert result["redacted_regions"] == [[31, 16, 59, 44]]
    assert result["detected_face_count"] == 1
    assert result["fallback_person_count"] == 0
    assert result["used_person_fallback"] is False
    assert not np.array_equal(result["image"][16:44, 31:59], frame[16:44, 31:59])
    assert np.array_equal(result["image"][44:90, 20:80], frame[44:90, 20:80])
    assert np.array_equal(frame, original)


def test_mixed_people_use_face_and_per_person_fallback():
    frame = _patterned_frame()
    people = [
        {"bbox": [5, 5, 55, 95], "confidence": 0.9, "inside_zone": False},
        {"bbox": [65, 10, 115, 90], "confidence": 0.9, "inside_zone": True},
    ]

    result = redact_identity_regions(frame, people, [face([20, 15, 40, 35])], face_margin_ratio=0.0)

    assert result["redacted_regions"] == [[20, 15, 40, 35], [65, 10, 115, 42]]
    assert result["detected_face_count"] == 1
    assert result["fallback_person_count"] == 1
    assert result["used_person_fallback"] is True


def test_unassociated_face_is_blurred_while_person_still_falls_back():
    frame = _patterned_frame()
    people = [{"bbox": [10, 10, 50, 90], "confidence": 0.9, "inside_zone": False}]

    result = redact_identity_regions(frame, people, [face([80, 10, 110, 40])], face_margin_ratio=0.0)

    assert result["redacted_regions"] == [[80, 10, 110, 40], [10, 10, 50, 42]]
    assert result["fallback_person_count"] == 1


def test_multiple_faces_inside_one_person_do_not_trigger_fallback():
    result = redact_identity_regions(
        _patterned_frame(),
        [{"bbox": [10, 5, 110, 95], "confidence": 0.9, "inside_zone": False}],
        [face([20, 15, 40, 35]), face([70, 15, 90, 35])],
        face_margin_ratio=0.0,
    )

    assert result["redacted_regions"] == [[20, 15, 40, 35], [70, 15, 90, 35]]
    assert result["detected_face_count"] == 2
    assert result["fallback_person_count"] == 0


def test_overlapping_face_regions_are_blurred_once_without_losing_detection_count():
    result = redact_identity_regions(
        _patterned_frame(),
        [{"bbox": [10, 5, 110, 95], "confidence": 0.9, "inside_zone": False}],
        [face([20, 15, 50, 45]), face([40, 25, 70, 55])],
        face_margin_ratio=0.0,
    )

    assert result["redacted_regions"] == [[20, 15, 70, 55]]
    assert result["detected_face_count"] == 2
    assert result["fallback_person_count"] == 0


def test_face_margin_is_clamped_to_frame_bounds():
    result = redact_identity_regions(
        _patterned_frame(),
        [{"bbox": [0, 0, 50, 90], "confidence": 0.9, "inside_zone": False}],
        [face([-5, -5, 20, 20])],
        face_margin_ratio=0.5,
    )

    assert result["redacted_regions"] == [[0, 0, 30, 30]]


def test_yunet_error_falls_back_for_all_people_and_is_reported():
    class FailingDetector:
        def preload(self):
            pass

        def detect(self, frame):
            raise RuntimeError("detector unavailable")

    facade = PrivacyRedactionFacade(face_detector=FailingDetector())
    people = [{"bbox": [20, 10, 80, 90], "confidence": 0.9, "inside_zone": False}]

    result = facade.redact_snapshot(_patterned_frame(), people)

    assert result["redacted_regions"] == [[20, 10, 80, 42]]
    assert result["face_detector_failed"] is True
    assert result["fallback_person_count"] == 1


def test_yunet_runs_once_for_one_snapshot():
    class CountingDetector:
        def __init__(self):
            self.calls = 0

        def preload(self):
            pass

        def detect(self, frame):
            self.calls += 1
            return [face([35, 20, 55, 40])]

    detector = CountingDetector()
    facade = PrivacyRedactionFacade(face_detector=detector)

    facade.redact_snapshot(
        _patterned_frame(),
        [{"bbox": [20, 10, 80, 90], "confidence": 0.9, "inside_zone": False}],
    )

    assert detector.calls == 1


def test_snapshot_without_a_redaction_candidate_fails_closed():
    with pytest.raises(PrivacyRedactionError, match="no canonical person"):
        redact_person_head_regions(_patterned_frame(), [])

    with pytest.raises(PrivacyRedactionError, match="no canonical person"):
        redact_identity_regions(_patterned_frame(), [], [face([20, 10, 50, 40])])


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
