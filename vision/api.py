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


class PpeVisionFacade:
    """Returns PPE-presence observations without applying safety rules."""

    _PPE_CLASS_TO_FIELD = {"helmet": "helmet", "glasses": "safety_glasses", "gloves": "gloves"}

    def __init__(self, model_path: str, confidence_threshold: float = 0.35) -> None:
        self._model_path = model_path
        self._confidence_threshold = confidence_threshold
        self._model = None

    def observe(
        self,
        frame: np.ndarray,
        people: list[tuple[int, int, int, int, float]],
    ) -> list[PersonPpeObservations]:
        observations = [self._unknown_observations() for _ in people]
        if not people:
            return observations

        if self._model is None:
            from ultralytics import YOLO

            self._model = YOLO(str(Path(self._model_path)))

        result = self._model.predict(frame, conf=self._confidence_threshold, verbose=False)[0]
        names = result.names
        for box in result.boxes:
            class_name = str(names[int(box.cls[0])]).lower()
            field = self._PPE_CLASS_TO_FIELD.get(class_name)
            if field is None:
                continue

            x1, y1, x2, y2 = (float(value) for value in box.xyxy[0].tolist())
            person_index = self._person_containing((x1 + x2) / 2, (y1 + y2) / 2, people)
            if person_index is None:
                continue

            confidence = float(box.conf[0])
            current = observations[person_index][field]
            if current["confidence"] is None or confidence > current["confidence"]:
                observations[person_index][field] = {"status": "present", "confidence": confidence}

        return observations

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
