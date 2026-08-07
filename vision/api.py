from __future__ import annotations

from pathlib import Path
from typing import TypedDict

import numpy as np


class PpeObservationValue(TypedDict):
    status: str
    confidence: float | None


class PersonPpeObservations(TypedDict):
    helmet: PpeObservationValue
    safety_glasses: PpeObservationValue
    gloves: PpeObservationValue


class ModelDetection(TypedDict):
    class_id: int
    class_name: str
    bbox: list[int]
    confidence: float
    person_index: int | None


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

        if self._model is None:
            from ultralytics import YOLO

            self._model = YOLO(str(Path(self._model_path)))

        result = self._model.predict(frame, conf=self._confidence_threshold, verbose=False)[0]
        names = result.names
        detections: list[ModelDetection] = []
        for box in result.boxes:
            class_id = int(box.cls[0])
            class_name = str(names[class_id]).lower()
            x1, y1, x2, y2 = (float(value) for value in box.xyxy[0].tolist())
            person_index = self._person_containing((x1 + x2) / 2, (y1 + y2) / 2, people)
            detections.append(
                {
                    "class_id": class_id,
                    "class_name": class_name,
                    "bbox": [int(x1), int(y1), int(x2), int(y2)],
                    "confidence": float(box.conf[0]),
                    "person_index": person_index,
                }
            )
            field = self._PPE_CLASS_TO_FIELD.get(class_name)
            if field is None or person_index is None:
                continue

            confidence = float(box.conf[0])
            current = observations[person_index][field]
            if current["confidence"] is None or confidence > current["confidence"]:
                observations[person_index][field] = {"status": "present", "confidence": confidence}

        return {"people": observations, "detections": detections}

    def preload(self) -> None:
        if self._model is None:
            from ultralytics import YOLO

            self._model = YOLO(str(Path(self._model_path)))

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
