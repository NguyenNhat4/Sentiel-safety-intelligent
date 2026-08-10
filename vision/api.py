from __future__ import annotations

from pathlib import Path
from typing import TypedDict

import numpy as np

from vision.pipeline import (
    ModelDetection,
    PrivacyRedactionResult,
    SnapshotPerson,
    annotate_snapshot,
    redact_identity_regions,
)


class PpeObservationValue(TypedDict):
    status: str
    confidence: float | None


class PersonPpeObservations(TypedDict):
    helmet: PpeObservationValue
    safety_glasses: PpeObservationValue
    gloves: PpeObservationValue


class PpeVisionResult(TypedDict):
    people: list[PersonPpeObservations]
    detections: list[ModelDetection]


class PpeVisionFacade:
    """Returns PPE-presence observations without applying safety rules."""

    _PPE_CLASS_TO_FIELD = {"helmet": "helmet", "glasses": "safety_glasses", "gloves": "gloves"}

    def __init__(
        self,
        model_path: str,
        confidence_threshold: float = 0.35,
        person_confidence_threshold: float = 0.5,
    ) -> None:
        self._model_path = model_path
        self._confidence_threshold = confidence_threshold
        self._person_confidence_threshold = person_confidence_threshold
        self._model = None

    def observe(
        self,
        frame: np.ndarray,
        people: list[tuple[int, int, int, int, float]],
    ) -> PpeVisionResult:
        observations = [self._unknown_observations() for _ in people]
        detections = self._detect(frame, people)
        for detection in detections:
            class_name = detection["class_name"]
            confidence = detection["confidence"]
            person_index = detection["person_index"]
            field = self._PPE_CLASS_TO_FIELD.get(class_name)
            if field is None or person_index is None:
                continue

            current = observations[person_index][field]
            if current["confidence"] is None or confidence > current["confidence"]:
                observations[person_index][field] = {"status": "present", "confidence": confidence}

        return {"people": observations, "detections": detections}

    def redact_snapshot(self, frame: np.ndarray) -> PrivacyRedactionResult:
        """Redact identity regions from a frame using the configured SH17 checkpoint."""
        return redact_identity_regions(frame, self._detect(frame, []))

    @staticmethod
    def annotate_snapshot(
        frame: np.ndarray,
        people: list[SnapshotPerson],
        detections: list[ModelDetection],
    ) -> np.ndarray:
        return annotate_snapshot(frame, people, detections)

    def preload(self) -> None:
        self._load_model()

    def _detect(
        self,
        frame: np.ndarray,
        people: list[tuple[int, int, int, int, float]],
    ) -> list[ModelDetection]:
        result = self._load_model().predict(frame, conf=self._confidence_threshold, verbose=False)[0]
        names = result.names
        detections: list[ModelDetection] = []
        for box in result.boxes:
            class_id = int(box.cls[0])
            class_name = str(names[class_id]).lower()
            x1, y1, x2, y2 = (float(value) for value in box.xyxy[0].tolist())
            detections.append(
                {
                    "class_id": class_id,
                    "class_name": class_name,
                    "bbox": [int(x1), int(y1), int(x2), int(y2)],
                    "confidence": float(box.conf[0]),
                    "person_index": self._person_containing((x1 + x2) / 2, (y1 + y2) / 2, people),
                }
            )
        return detections

    def _load_model(self):
        if self._model is None:
            from ultralytics import YOLO

            self._model = YOLO(str(Path(self._model_path)))
        return self._model

    @staticmethod
    def _unknown_observations() -> PersonPpeObservations:
        return {
            "helmet": {"status": "unknown", "confidence": None},
            "safety_glasses": {"status": "unknown", "confidence": None},
            "gloves": {"status": "unknown", "confidence": None},
        }

    @staticmethod
    def _person_containing(
        center_x: float,
        center_y: float,
        people: list[tuple[int, int, int, int, float]],
    ) -> int | None:
        for index, (x, y, width, height, _) in enumerate(people):
            if x <= center_x <= x + width and y <= center_y <= y + height:
                return index
        return None
