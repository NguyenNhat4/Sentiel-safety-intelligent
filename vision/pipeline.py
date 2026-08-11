from __future__ import annotations

from typing import TypedDict

import cv2
import numpy as np


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


class SnapshotPerson(TypedDict):
    bbox: list[int]
    confidence: float
    inside_zone: bool


class PrivacyRedactionError(RuntimeError):
    """Raised when a snapshot cannot be safely redacted."""


_IDENTITY_CLASS_NAMES = frozenset({"face", "face-guard", "face-mask", "head"})
_PERSON_CLASS_NAME = "person"
_PERSON_HEAD_HEIGHT_RATIO = 0.4
_PERSON_NORMAL_COLOR = (94, 197, 34)
_PERSON_VIOLATION_COLOR = (64, 73, 255)
_DETECTION_COLORS = {
    "helmet": (11, 158, 245),
    "head": (11, 158, 245),
    "glasses": (246, 92, 139),
    "safety_glasses": (246, 92, 139),
    "face": (246, 92, 139),
    "face-guard": (246, 92, 139),
    "face-mask": (246, 92, 139),
    "gloves": (129, 185, 16),
    "hands": (129, 185, 16),
    "hand": (129, 185, 16),
    "shoes": (246, 130, 59),
    "foot": (246, 130, 59),
    "safety-suit": (153, 72, 236),
    "safety-vest": (153, 72, 236),
    "medical-suit": (153, 72, 236),
    "ear": (212, 182, 6),
    "ear-mufs": (212, 182, 6),
    "tool": (8, 179, 234),
}
_DEFAULT_DETECTION_COLOR = (246, 130, 59)


def redact_identity_regions(
    frame: np.ndarray,
    detections: list[ModelDetection],
) -> PrivacyRedactionResult:
    """Blur identity detections and conservatively cover heads of unmatched people.

    The input frame is never mutated. A frame with no usable direct identity region
    or person fallback is rejected so callers cannot persist it by accident.
    """
    if frame.ndim != 3 or frame.shape[2] != 3:
        raise PrivacyRedactionError("snapshot must be a three-channel image")

    height, width = frame.shape[:2]
    identity_regions = [
        region
        for detection in detections
        if detection["class_name"].lower() in _IDENTITY_CLASS_NAMES
        if (region := _bounded_region(detection["bbox"], width, height)) is not None
    ]
    person_regions = [
        region
        for detection in detections
        if detection["class_name"].lower() == _PERSON_CLASS_NAME
        if (region := _bounded_region(detection["bbox"], width, height)) is not None
    ]

    regions = list(identity_regions)
    used_person_fallback = False
    for person_region in person_regions:
        if any(_center_is_inside(region, person_region) for region in identity_regions):
            continue
        regions.append(_person_head_region(person_region))
        used_person_fallback = True

    unique_regions = _unique_regions(regions)
    if not unique_regions:
        raise PrivacyRedactionError("no face, head, or person region was available for redaction")

    redacted = frame.copy()
    for x1, y1, x2, y2 in unique_regions:
        redacted[y1:y2, x1:x2] = cv2.GaussianBlur(
            redacted[y1:y2, x1:x2],
            (0, 0),
            sigmaX=12,
            sigmaY=12,
        )

    return {
        "image": redacted,
        "redacted_regions": unique_regions,
        "used_person_fallback": used_person_fallback,
    }


def annotate_snapshot(
    frame: np.ndarray,
    people: list[SnapshotPerson],
    detections: list[ModelDetection],
) -> np.ndarray:
    """Draw the reviewed frame's person and SH17 detection boxes after redaction."""
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


def _center_is_inside(region: list[int], person_region: list[int]) -> bool:
    center_x = (region[0] + region[2]) / 2
    center_y = (region[1] + region[3]) / 2
    return person_region[0] <= center_x <= person_region[2] and person_region[1] <= center_y <= person_region[3]


def _person_head_region(person_region: list[int]) -> list[int]:
    x1, y1, x2, y2 = person_region
    head_bottom = min(y2, y1 + max(1, round((y2 - y1) * _PERSON_HEAD_HEIGHT_RATIO)))
    return [x1, y1, x2, head_bottom]


def _unique_regions(regions: list[list[int]]) -> list[list[int]]:
    return [list(region) for region in dict.fromkeys(tuple(region) for region in regions)]


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
