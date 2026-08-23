from __future__ import annotations

from typing import TypedDict

import cv2
import numpy as np

from vision.face_detection import FaceDetection


class ModelDetection(TypedDict):
    class_id: int
    class_name: str
    bbox: list[int]
    confidence: float
    person_index: int | None


class PrivacyRedactionResult(TypedDict):
    image: np.ndarray
    redacted_regions: list[list[int]]
    used_person_fallback: bool
    detected_face_count: int
    fallback_person_count: int
    face_detector_failed: bool


class SnapshotPerson(TypedDict):
    bbox: list[int]
    confidence: float
    inside_zone: bool


class PrivacyRedactionError(RuntimeError):
    """Raised when a snapshot cannot be safely redacted."""


_PERSON_CLASS_NAME = "person"
_PERSON_HEAD_HEIGHT_RATIO = 0.4
_PERSON_NORMAL_COLOR = (94, 197, 34)
_PERSON_VIOLATION_COLOR = (64, 73, 255)
_DETECTION_COLORS = {
    "hat": (11, 158, 245),
    "vest": (153, 72, 236),
}
_DEFAULT_DETECTION_COLOR = (246, 130, 59)


def redact_person_head_regions(
    frame: np.ndarray,
    people: list[SnapshotPerson],
) -> PrivacyRedactionResult:
    """Conservatively blur the top 40% of every canonical person box.

    The input frame is never mutated. A frame with no usable canonical person box is
    rejected so callers cannot persist it by accident. This privacy path is independent
    from the PPE checkpoint and therefore cannot regress when that model changes.
    """
    return redact_identity_regions(frame, people, [])


def redact_identity_regions(
    frame: np.ndarray,
    people: list[SnapshotPerson],
    faces: list[FaceDetection],
    *,
    face_margin_ratio: float = 0.2,
    face_detector_failed: bool = False,
) -> PrivacyRedactionResult:
    """Blur YuNet faces and use the person-head fallback for each unmatched person."""
    if frame.ndim != 3 or frame.shape[2] != 3:
        raise PrivacyRedactionError("snapshot must be a three-channel image")
    if not 0.0 <= face_margin_ratio <= 1.0:
        raise ValueError("face_margin_ratio must be between 0 and 1")

    height, width = frame.shape[:2]
    person_regions = [
        region for person in people if (region := _bounded_region(person["bbox"], width, height)) is not None
    ]
    if not person_regions:
        raise PrivacyRedactionError("no canonical person region was available for redaction")

    bounded_faces = [region for face in faces if (region := _bounded_region(face["bbox"], width, height)) is not None]
    face_regions = _merged_regions(
        [_expanded_region(region, face_margin_ratio, width=width, height=height) for region in bounded_faces]
    )
    matched_people = {
        person_index
        for face_region in bounded_faces
        if (person_index := _associated_person_index(face_region, person_regions)) is not None
    }
    fallback_regions = [
        _person_head_region(person_region)
        for person_index, person_region in enumerate(person_regions)
        if person_index not in matched_people
    ]
    redacted_regions = _merged_regions([*face_regions, *fallback_regions])

    redacted = frame.copy()
    for x1, y1, x2, y2 in redacted_regions:
        redacted[y1:y2, x1:x2] = cv2.GaussianBlur(
            redacted[y1:y2, x1:x2],
            (0, 0),
            sigmaX=12,
            sigmaY=12,
        )

    return {
        "image": redacted,
        "redacted_regions": redacted_regions,
        "used_person_fallback": bool(fallback_regions),
        "detected_face_count": len(bounded_faces),
        "fallback_person_count": len(fallback_regions),
        "face_detector_failed": face_detector_failed,
    }


def annotate_snapshot(
    frame: np.ndarray,
    people: list[SnapshotPerson],
    detections: list[ModelDetection],
) -> np.ndarray:
    """Draw canonical person and three-class profile boxes after redaction."""
    if frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("snapshot must be a three-channel image")

    annotated = frame.copy()
    height, width = annotated.shape[:2]
    for index, person in enumerate(people):
        region = _bounded_region(person["bbox"], width, height)
        if region is None:
            continue
        color = _PERSON_VIOLATION_COLOR if person["inside_zone"] else _PERSON_NORMAL_COLOR
        label = f"PERSON #{index + 1} {person['confidence']:.0%}"
        _draw_box(annotated, region, color, label, thickness=3)

    for detection in detections:
        if detection["class_name"].lower() == _PERSON_CLASS_NAME:
            continue
        region = _bounded_region(detection["bbox"], width, height)
        if region is None:
            continue
        class_name = detection["class_name"].lower()
        label = f"{class_name.upper()} {detection['confidence']:.0%}"
        _draw_box(annotated, region, _DETECTION_COLORS.get(class_name, _DEFAULT_DETECTION_COLOR), label)

    return annotated


def _bounded_region(bbox: list[int], width: int, height: int) -> list[int] | None:
    if len(bbox) != 4:
        return None
    x1, y1, x2, y2 = bbox
    bounded = [max(0, min(width, x1)), max(0, min(height, y1)), max(0, min(width, x2)), max(0, min(height, y2))]
    if bounded[2] <= bounded[0] or bounded[3] <= bounded[1]:
        return None
    return bounded


def _person_head_region(person_region: list[int]) -> list[int]:
    x1, y1, x2, y2 = person_region
    head_bottom = min(y2, y1 + max(1, round((y2 - y1) * _PERSON_HEAD_HEIGHT_RATIO)))
    return [x1, y1, x2, head_bottom]


def _expanded_region(region: list[int], margin_ratio: float, *, width: int, height: int) -> list[int]:
    x1, y1, x2, y2 = region
    margin_x = round((x2 - x1) * margin_ratio)
    margin_y = round((y2 - y1) * margin_ratio)
    return [
        max(0, x1 - margin_x),
        max(0, y1 - margin_y),
        min(width, x2 + margin_x),
        min(height, y2 + margin_y),
    ]


def _associated_person_index(face_region: list[int], person_regions: list[list[int]]) -> int | None:
    face_center_x = (face_region[0] + face_region[2]) / 2
    face_center_y = (face_region[1] + face_region[3]) / 2
    candidates = [
        (index, (x2 - x1) * (y2 - y1))
        for index, (x1, y1, x2, y2) in enumerate(person_regions)
        if x1 <= face_center_x <= x2 and y1 <= face_center_y <= y2
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda candidate: candidate[1])[0]


def _merged_regions(regions: list[list[int]]) -> list[list[int]]:
    """Deduplicate and union overlapping rectangles so pixels are blurred once."""
    merged: list[list[int]] = []
    for region in regions:
        candidate = list(region)
        index = 0
        while index < len(merged):
            existing = merged[index]
            if not _regions_overlap(candidate, existing):
                index += 1
                continue
            candidate = [
                min(candidate[0], existing[0]),
                min(candidate[1], existing[1]),
                max(candidate[2], existing[2]),
                max(candidate[3], existing[3]),
            ]
            merged.pop(index)
            index = 0
        merged.append(candidate)
    return merged


def _regions_overlap(first: list[int], second: list[int]) -> bool:
    return max(first[0], second[0]) < min(first[2], second[2]) and max(first[1], second[1]) < min(first[3], second[3])


def _draw_box(
    image: np.ndarray,
    region: list[int],
    color: tuple[int, int, int],
    label: str,
    *,
    thickness: int = 2,
) -> None:
    x1, y1, x2, y2 = region
    cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness)
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.45
    text_thickness = 1
    (text_width, text_height), baseline = cv2.getTextSize(label, font, scale, text_thickness)
    label_top = max(0, y1 - text_height - baseline - 6)
    label_bottom = label_top + text_height + baseline + 6
    cv2.rectangle(image, (x1, label_top), (min(image.shape[1], x1 + text_width + 8), label_bottom), color, -1)
    cv2.putText(
        image, label, (x1 + 4, label_bottom - baseline - 3), font, scale, (255, 255, 255), text_thickness, cv2.LINE_AA
    )
