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
    redact_identity_regions,
)

TrackedPerson = tuple[int, int, int, int, float, int]


class PersonTrackingFacade:
    """Keeps one Ultralytics ByteTrack instance per monitoring session."""

    def __init__(
        self,
        model_path: str,
        *,
        session_ttl_seconds: float = 300.0,
        model_factory: Callable[[str], Any] | None = None,
        tracker_dependency_loader: Callable[[], None] | None = None,
    ) -> None:
        self._model_path = model_path
        self._session_ttl_seconds = session_ttl_seconds
        self._model_factory = model_factory
        self._tracker_dependency_loader = tracker_dependency_loader or self._load_tracker_dependencies
        self._sessions: dict[str, tuple[Any, float]] = {}
        self._preloaded_model: Any | None = None

    def track(self, session_id: str, frame: np.ndarray, *, now: float) -> list[TrackedPerson]:
        self._expire(now)
        session = self._sessions.get(session_id)
        if session is None:
            model = self._preloaded_model or self._create_model()
            self._preloaded_model = None
        else:
            model = session[0]
        self._sessions[session_id] = (model, now)

        result = model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            classes=[0],
            conf=0.35,
            verbose=False,
        )[0]
        people: list[TrackedPerson] = []
        for box in result.boxes:
            if box.id is None:
                continue
            x1, y1, x2, y2 = (int(value) for value in box.xyxy[0].tolist())
            people.append((x1, y1, x2 - x1, y2 - y1, float(box.conf[0]), int(box.id[0].item())))
        return people

    def end_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def preload(self) -> None:
        """Load the first person model and ByteTrack dependencies before traffic."""
        if self._preloaded_model is None:
            self._preloaded_model = self._create_model()
        self._tracker_dependency_loader()

    def _create_model(self) -> Any:
        if self._model_factory is not None:
            return self._model_factory(self._model_path)
        from ultralytics import YOLO

        return YOLO(str(Path(self._model_path)))

    @staticmethod
    def _load_tracker_dependencies() -> None:
        from ultralytics.trackers import BYTETracker  # noqa: F401

    def _expire(self, now: float) -> None:
        expired = [
            session_id
            for session_id, (_, last_seen) in self._sessions.items()
            if now - last_seen >= self._session_ttl_seconds
        ]
        for session_id in expired:
            self._sessions.pop(session_id, None)


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
