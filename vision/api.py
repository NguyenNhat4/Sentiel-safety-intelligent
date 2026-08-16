from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, TypedDict

import numpy as np

from vision.pipeline import (
    ModelDetection,
    PrivacyRedactionResult,
    SnapshotPerson,
    annotate_snapshot,
    redact_person_head_regions,
)

CanonicalPerson = tuple[int, int, int, int, float, int]


class PpeObservationValue(TypedDict):
    status: str
    confidence: float | None


class PersonPpeObservations(TypedDict):
    hat: PpeObservationValue
    vest: PpeObservationValue


class PpeVisionResult(TypedDict):
    people: list[PersonPpeObservations]
    detections: list[ModelDetection]


class SafetyVisionResult(PpeVisionResult):
    canonical_people: list[CanonicalPerson]


class PpeVisionFacade:
    """Runs the single Safety checkpoint for canonical people, tracking and PPE."""

    SOURCE_CLASS_NAMES = {0: "hat", 1: "nohat", 2: "novest", 3: "person", 4: "vest"}
    EXPOSED_CLASS_NAMES = frozenset({"hat", "person", "vest"})
    _PPE_CLASS_TO_FIELD = {"hat": "hat", "vest": "vest"}

    def __init__(
        self,
        model_path: str,
        confidence_threshold: float = 0.35,
        person_confidence_threshold: float = 0.5,
        session_ttl_seconds: float = 300.0,
        model_factory: Callable[[str], Any] | None = None,
    ) -> None:
        self._model_path = model_path
        self._confidence_threshold = confidence_threshold
        self._person_confidence_threshold = person_confidence_threshold
        self._session_ttl_seconds = session_ttl_seconds
        self._model_factory = model_factory
        self._model = None
        self._sessions: dict[str, tuple[Any, float]] = {}

    def analyze(
        self,
        frame: np.ndarray,
        monitoring_session_id: str | None,
        now: float,
    ) -> SafetyVisionResult:
        """Return canonical people and PPE from one model call for this frame."""
        if monitoring_session_id is None:
            result = self._load_model().predict(
                frame,
                classes=[0, 3, 4],
                conf=self._confidence_threshold,
                verbose=False,
                device="cpu",
            )[0]
            return self._safety_result(result, require_track_ids=False)

        self._expire_sessions(now)
        session = self._sessions.get(monitoring_session_id)
        model = self._create_model() if session is None else session[0]
        self._validate_model_classes(model.names)
        self._sessions[monitoring_session_id] = (model, now)
        result = model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            classes=[0, 3, 4],
            conf=self._confidence_threshold,
            verbose=False,
            device="cpu",
        )[0]
        return self._safety_result(result, require_track_ids=True)

    def observe(
        self,
        frame: np.ndarray,
        people: list[tuple[int, int, int, int, float]],
    ) -> PpeVisionResult:
        observations = [self._unknown_observations() for _ in people]
        detections = self._canonical_people(people)
        detections.extend(self._detect_ppe(frame, people))
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

    def preload(self) -> None:
        self._load_model()

    def end_session(self, monitoring_session_id: str) -> None:
        self._sessions.pop(monitoring_session_id, None)

    def _safety_result(self, result: Any, *, require_track_ids: bool) -> SafetyVisionResult:
        self._validate_model_classes(result.names)
        canonical_people: list[CanonicalPerson] = []
        ppe_boxes: list[tuple[int, str, list[int], float]] = []

        for box in result.boxes:
            class_id = int(box.cls[0])
            class_name = str(result.names[class_id]).lower()
            if class_name not in self.EXPOSED_CLASS_NAMES:
                continue
            x1, y1, x2, y2 = (int(value) for value in box.xyxy[0].tolist())
            confidence = float(box.conf[0])
            if class_name == "person":
                track_id = self._box_track_id(box)
                if require_track_ids and track_id is None:
                    continue
                canonical_people.append(
                    (
                        x1,
                        y1,
                        x2 - x1,
                        y2 - y1,
                        confidence,
                        track_id or len(canonical_people) + 1,
                    )
                )
            else:
                ppe_boxes.append((class_id, class_name, [x1, y1, x2, y2], confidence))

        people_without_tracks = [person[:5] for person in canonical_people]
        observations = [self._unknown_observations() for _ in canonical_people]
        detections = self._canonical_people(people_without_tracks)
        for class_id, class_name, bbox, confidence in ppe_boxes:
            x1, y1, x2, y2 = bbox
            person_index = self._person_containing(
                (x1 + x2) / 2,
                (y1 + y2) / 2,
                people_without_tracks,
            )
            detections.append(
                {
                    "class_id": class_id,
                    "class_name": class_name,
                    "bbox": bbox,
                    "confidence": confidence,
                    "person_index": person_index,
                }
            )
            if person_index is None:
                continue
            current = observations[person_index][class_name]
            if current["confidence"] is None or confidence > current["confidence"]:
                observations[person_index][class_name] = {
                    "status": "present",
                    "confidence": confidence,
                }

        return {
            "canonical_people": canonical_people,
            "people": observations,
            "detections": detections,
        }

    def _detect_ppe(
        self,
        frame: np.ndarray,
        people: list[tuple[int, int, int, int, float]],
    ) -> list[ModelDetection]:
        result = self._load_model().predict(
            frame,
            classes=[0, 3, 4],
            conf=self._confidence_threshold,
            verbose=False,
            device="cpu",
        )[0]
        names = result.names
        selected_boxes: list[tuple[int, str, list[int], float]] = []
        model_people: list[tuple[float, float, float, float]] = []
        for box in result.boxes:
            class_id = int(box.cls[0])
            class_name = str(names[class_id]).lower()
            if class_name not in self.EXPOSED_CLASS_NAMES:
                continue
            x1, y1, x2, y2 = (float(value) for value in box.xyxy[0].tolist())
            if class_name == "person":
                model_people.append((x1, y1, x2, y2))
                continue
            selected_boxes.append((class_id, class_name, [int(x1), int(y1), int(x2), int(y2)], float(box.conf[0])))

        detections: list[ModelDetection] = []
        for class_id, class_name, bbox, confidence in selected_boxes:
            x1, y1, x2, y2 = bbox
            detections.append(
                {
                    "class_id": class_id,
                    "class_name": class_name,
                    "bbox": bbox,
                    "confidence": confidence,
                    "person_index": self._associated_person(
                        (x1 + x2) / 2,
                        (y1 + y2) / 2,
                        model_people,
                        people,
                    ),
                }
            )
        return detections

    def _load_model(self):
        if self._model is None:
            self._model = self._create_model()
        self._validate_model_classes(self._model.names)
        return self._model

    def _create_model(self) -> Any:
        if self._model_factory is not None:
            return self._model_factory(self._model_path)
        if Path(self._model_path).suffix.lower() != ".onnx":
            raise RuntimeError(
                "Safety inference requires an ONNX checkpoint; set PPE_MODEL_PATH to models/yolo11m_safety.onnx"
            )
        from ultralytics import YOLO

        return YOLO(str(Path(self._model_path)), task="detect")

    def _expire_sessions(self, now: float) -> None:
        expired = [
            session_id
            for session_id, (_, last_seen) in self._sessions.items()
            if now - last_seen >= self._session_ttl_seconds
        ]
        for session_id in expired:
            self._sessions.pop(session_id, None)

    @staticmethod
    def _box_track_id(box: Any) -> int | None:
        if getattr(box, "id", None) is None:
            return None
        value = box.id[0]
        return int(value.item() if hasattr(value, "item") else value)

    @staticmethod
    def _unknown_observations() -> PersonPpeObservations:
        return {
            "hat": {"status": "unknown", "confidence": None},
            "vest": {"status": "unknown", "confidence": None},
        }

    @classmethod
    def _validate_model_classes(cls, names: dict[int, str] | list[str]) -> None:
        normalized = {
            index: str(name) for index, name in dict(enumerate(names) if isinstance(names, list) else names).items()
        }
        if normalized != cls.SOURCE_CLASS_NAMES:
            raise RuntimeError(f"Safety ONNX class mapping must be {cls.SOURCE_CLASS_NAMES}, received {normalized}")

    @staticmethod
    def _canonical_people(
        people: list[tuple[int, int, int, int, float]],
    ) -> list[ModelDetection]:
        return [
            {
                "class_id": 3,
                "class_name": "person",
                "bbox": [x, y, x + width, y + height],
                "confidence": confidence,
                "person_index": index,
            }
            for index, (x, y, width, height, confidence) in enumerate(people)
        ]

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

    @classmethod
    def _associated_person(
        cls,
        center_x: float,
        center_y: float,
        model_people: list[tuple[float, float, float, float]],
        canonical_people: list[tuple[int, int, int, int, float]],
    ) -> int | None:
        candidates: list[tuple[float, int]] = []
        for model_person in model_people:
            x1, y1, x2, y2 = model_person
            if not (x1 <= center_x <= x2 and y1 <= center_y <= y2):
                continue
            for index, (x, y, width, height, _) in enumerate(canonical_people):
                overlap = cls._intersection_over_union(model_person, (x, y, x + width, y + height))
                if overlap > 0:
                    candidates.append((overlap, index))
        if candidates:
            return max(candidates, key=lambda item: item[0])[1]
        return cls._person_containing(center_x, center_y, canonical_people)

    @staticmethod
    def _intersection_over_union(
        left: tuple[float, float, float, float],
        right: tuple[float, float, float, float],
    ) -> float:
        intersection_width = max(0.0, min(left[2], right[2]) - max(left[0], right[0]))
        intersection_height = max(0.0, min(left[3], right[3]) - max(left[1], right[1]))
        intersection = intersection_width * intersection_height
        if intersection == 0:
            return 0.0
        left_area = max(0.0, left[2] - left[0]) * max(0.0, left[3] - left[1])
        right_area = max(0.0, right[2] - right[0]) * max(0.0, right[3] - right[1])
        return intersection / (left_area + right_area - intersection)


class PrivacyRedactionFacade:
    """Redacts identity from canonical person boxes without loading a PPE model."""

    @staticmethod
    def redact_snapshot(
        frame: np.ndarray,
        people: list[SnapshotPerson],
    ) -> PrivacyRedactionResult:
        return redact_person_head_regions(frame, people)

    @staticmethod
    def annotate_snapshot(
        frame: np.ndarray,
        people: list[SnapshotPerson],
        detections: list[ModelDetection],
    ) -> np.ndarray:
        return annotate_snapshot(frame, people, detections)
