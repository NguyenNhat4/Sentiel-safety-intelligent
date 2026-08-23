from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any, NotRequired, TypedDict

import numpy as np

from vision.face_detection import FaceDetector, YuNetFaceDetector
from vision.pipeline import (
    ModelDetection,
    PrivacyRedactionResult,
    SnapshotPerson,
    annotate_snapshot,
    redact_identity_regions,
    redact_person_head_regions,
)

logger = logging.getLogger(__name__)

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


class PpeAbsenceConfirmation(TypedDict):
    hat: bool
    vest: bool


class SafetyVisionResult(PpeVisionResult):
    canonical_people: list[CanonicalPerson]
    absence_confirmed: NotRequired[list[PpeAbsenceConfirmation]]


# ---------------------------------------------------------------------------
# Temporal Smoothing
# ---------------------------------------------------------------------------


class _TrackPpeHistory:
    """Per-track rolling streak counters for anti-flicker grace period."""

    __slots__ = (
        "hat_present_streak",
        "hat_missing_streak",
        "hat_present_confirmed",
        "vest_present_streak",
        "vest_missing_streak",
        "vest_present_confirmed",
        "lost_frames",
    )

    def __init__(self) -> None:
        self.hat_present_streak: int = 0
        self.hat_missing_streak: int = 0
        self.hat_present_confirmed: bool = False
        self.vest_present_streak: int = 0
        self.vest_missing_streak: int = 0
        self.vest_present_confirmed: bool = False
        self.lost_frames: int = 0


class PpeTemporalSmoother:
    """Confirm initial absence and hold established presence during short gaps.

    ``None`` means absence is still pending confirmation, ``False`` means the
    configured absence streak is confirmed, and ``True`` means PPE is present
    either directly or through the grace hold. Backend remains responsible for
    qualifying confirmed absence as ``missing``.
    """

    def __init__(
        self,
        temporal_frames: int = 10,
    ) -> None:
        if temporal_frames < 1:
            raise ValueError("temporal_frames must be at least 1")
        self._temporal_frames = temporal_frames
        self._history: dict[int, _TrackPpeHistory] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def smooth(
        self,
        track_id: int,
        raw_hat: bool,
        raw_vest: bool,
    ) -> tuple[bool | None, bool | None]:
        """Return (smoothed_hat, smoothed_vest) for *track_id* this frame."""
        h = self._history.setdefault(track_id, _TrackPpeHistory())
        h.lost_frames = 0
        return self._smooth_one(h, "hat", raw_hat), self._smooth_one(h, "vest", raw_vest)

    def advance_tracks(self, present_track_ids: set[int]) -> None:
        """Retain short ByteTrack gaps and purge tracks only after the grace window."""
        for track_id, history in list(self._history.items()):
            if track_id in present_track_ids:
                history.lost_frames = 0
                continue
            history.lost_frames += 1
            if history.lost_frames > self._temporal_frames:
                self.purge_track(track_id)

    def purge_track(self, track_id: int) -> None:
        """Remove history for a track that has left the scene."""
        self._history.pop(track_id, None)

    def active_tracks(self) -> set[int]:
        """Return the set of track IDs currently held in memory."""
        return set(self._history.keys())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _smooth_one(self, h: _TrackPpeHistory, item: str, raw: bool) -> bool | None:
        present_attr = f"{item}_present_streak"
        missing_attr = f"{item}_missing_streak"
        confirmed_attr = f"{item}_present_confirmed"
        if raw:
            present_streak = getattr(h, present_attr) + 1
            setattr(h, present_attr, present_streak)
            setattr(h, missing_attr, 0)
            if present_streak >= self._temporal_frames:
                setattr(h, confirmed_attr, True)
            return True
        # raw == False (model sees no PPE this frame)
        missing_streak = getattr(h, missing_attr) + 1
        setattr(h, missing_attr, missing_streak)
        if getattr(h, confirmed_attr):
            if missing_streak <= self._temporal_frames:
                # Still within grace period and track had prior presence — hold 'present'
                return True
            # Established presence exceeded its grace period: confirm absence now.
            setattr(h, present_attr, 0)
            setattr(h, confirmed_attr, False)
            return False

        # A fresh/unconfirmed track stays unknown until absence is repeated.
        setattr(h, present_attr, 0)
        return False if missing_streak >= self._temporal_frames else None


# ---------------------------------------------------------------------------
# Main Facade
# ---------------------------------------------------------------------------


class PpeVisionFacade:
    """Runs the single Safety checkpoint for canonical people, tracking and PPE."""

    SOURCE_CLASS_NAMES = {0: "hat", 1: "nohat", 2: "novest", 3: "person", 4: "vest"}
    EXPOSED_CLASS_NAMES = frozenset({"hat", "person", "vest"})
    _PPE_CLASS_TO_FIELD = {"hat": "hat", "vest": "vest"}

    # Geometric thresholds (fraction of person bbox height)
    _HAT_TOP_FRACTION: float = 0.40
    _VEST_BOTTOM_FRACTION: float = 0.85

    def __init__(
        self,
        model_path: str,
        confidence_threshold: float = 0.2,
        person_confidence_threshold: float = 0.6,
        inference_image_size: int = 960,
        session_ttl_seconds: float = 300.0,
        model_factory: Callable[[str], Any] | None = None,
        temporal_frames: int = 10,
    ) -> None:
        if not 0.0 < confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be in (0, 1]")
        if not 0.0 < person_confidence_threshold <= 1.0:
            raise ValueError("person_confidence_threshold must be in (0, 1]")
        if not 32 <= inference_image_size <= 4096 or inference_image_size % 32 != 0:
            raise ValueError("inference_image_size must be a multiple of 32 between 32 and 4096")
        if temporal_frames < 1:
            raise ValueError("temporal_frames must be at least 1")
        self._model_path = model_path
        self._confidence_threshold = confidence_threshold
        self._person_confidence_threshold = person_confidence_threshold
        self._inference_image_size = inference_image_size
        self._session_ttl_seconds = session_ttl_seconds
        self._model_factory = model_factory
        self._temporal_frames = temporal_frames
        self._model = None
        # session_id -> (model, last_seen_timestamp)
        self._sessions: dict[str, tuple[Any, float]] = {}
        # session_id -> PpeTemporalSmoother (only for tracked sessions)
        self._smoothers: dict[str, PpeTemporalSmoother] = {}
        self._sessions_lock = threading.RLock()
        self._session_locks: dict[str, threading.Lock] = {}

    @property
    def _model_confidence_threshold(self) -> float:
        """Lowest class threshold required for the shared YOLO inference call."""
        return min(self._confidence_threshold, self._person_confidence_threshold)

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
                conf=self._model_confidence_threshold,
                imgsz=self._inference_image_size,
                verbose=False,
            )[0]
            # Stateless: geometric validation only, no temporal smoothing
            return self._safety_result(result, require_track_ids=False, smoother=None)

        with self._sessions_lock:
            self._expire_sessions(now)
            session = self._sessions.get(monitoring_session_id)
            model = self._create_model() if session is None else session[0]
            self._validate_model_classes(model.names)
            self._sessions[monitoring_session_id] = (model, now)
            smoother = self._smoothers.setdefault(
                monitoring_session_id,
                PpeTemporalSmoother(temporal_frames=self._temporal_frames),
            )
            session_lock = self._session_locks.setdefault(monitoring_session_id, threading.Lock())
        with session_lock:
            result = model.track(
                frame,
                persist=True,
                tracker="bytetrack.yaml",
                classes=[0, 3, 4],
                conf=self._model_confidence_threshold,
                imgsz=self._inference_image_size,
                verbose=False,
            )[0]
            vision_result = self._safety_result(result, require_track_ids=True, smoother=smoother)
            present_track_ids = {person[5] for person in vision_result["canonical_people"]}
            smoother.advance_tracks(present_track_ids)
        return vision_result

    def observe(
        self,
        frame: np.ndarray,
        people: list[tuple[int, int, int, int, float]],
    ) -> PpeVisionResult:
        observations = [self._unknown_observations() for _ in people]
        detections = self._canonical_people(people)
        detections.extend(self._detect_ppe(frame, people))

        # Cardinality: keep only the highest-confidence PPE per (person, class)
        best: dict[int, dict[str, float]] = {}  # person_index -> {field -> confidence}
        for detection in detections:
            class_name = detection["class_name"]
            confidence = detection["confidence"]
            person_index = detection["person_index"]
            field = self._PPE_CLASS_TO_FIELD.get(class_name)
            if field is None or person_index is None:
                continue
            existing = best.setdefault(person_index, {})
            if field not in existing or confidence > existing[field]:
                existing[field] = confidence
                observations[person_index][field] = {"status": "present", "confidence": confidence}

        return {"people": observations, "detections": detections}

    def preload(self) -> None:
        self._load_model()

    def end_session(self, monitoring_session_id: str) -> None:
        with self._sessions_lock:
            self._sessions.pop(monitoring_session_id, None)
            self._smoothers.pop(monitoring_session_id, None)
            self._session_locks.pop(monitoring_session_id, None)

    # ------------------------------------------------------------------
    # Core detection + association
    # ------------------------------------------------------------------

    def _safety_result(
        self,
        result: Any,
        *,
        require_track_ids: bool,
        smoother: PpeTemporalSmoother | None,
    ) -> SafetyVisionResult:
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
                if confidence < self._person_confidence_threshold:
                    continue
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
                if confidence < self._confidence_threshold:
                    continue
                ppe_boxes.append((class_id, class_name, [x1, y1, x2, y2], confidence))

        people_without_tracks = [person[:5] for person in canonical_people]
        observations = [self._unknown_observations() for _ in canonical_people]
        absence_confirmed: list[PpeAbsenceConfirmation] = [{"hat": True, "vest": True} for _ in canonical_people]
        detections = self._canonical_people(people_without_tracks)

        ppe_detections = self._select_ppe_detections(ppe_boxes, people_without_tracks)
        detections.extend(ppe_detections)
        for detection in ppe_detections:
            person_index = detection["person_index"]
            if person_index is not None:
                observations[person_index][detection["class_name"]] = {
                    "status": "present",
                    "confidence": detection["confidence"],
                }

        # Apply temporal smoothing only for tracked sessions
        if smoother is not None:
            for idx, person in enumerate(canonical_people):
                track_id = person[5]
                raw_hat = observations[idx]["hat"]["status"] == "present"
                raw_vest = observations[idx]["vest"]["status"] == "present"
                smoothed_hat, smoothed_vest = smoother.smooth(track_id, raw_hat, raw_vest)
                absence_confirmed[idx] = {
                    "hat": smoothed_hat is False,
                    "vest": smoothed_vest is False,
                }
                if smoothed_hat and not raw_hat:
                    # Grace-period hold: keep present even though model missed
                    observations[idx]["hat"] = {"status": "present", "confidence": None}
                if smoothed_vest and not raw_vest:
                    observations[idx]["vest"] = {"status": "present", "confidence": None}

        return {
            "canonical_people": canonical_people,
            "people": observations,
            "detections": detections,
            "absence_confirmed": absence_confirmed,
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
            imgsz=self._inference_image_size,
            verbose=False,
        )[0]
        names = result.names
        selected_boxes: list[tuple[int, str, list[int], float]] = []
        for box in result.boxes:
            class_id = int(box.cls[0])
            class_name = str(names[class_id]).lower()
            if class_name not in self.EXPOSED_CLASS_NAMES:
                continue
            x1, y1, x2, y2 = (float(value) for value in box.xyxy[0].tolist())
            if class_name == "person":
                continue
            confidence = float(box.conf[0])
            if confidence < self._confidence_threshold:
                continue
            selected_boxes.append((class_id, class_name, [int(x1), int(y1), int(x2), int(y2)], confidence))
        return self._select_ppe_detections(selected_boxes, people)

    @classmethod
    def _select_ppe_detections(
        cls,
        ppe_boxes: list[tuple[int, str, list[int], float]],
        people: list[tuple[int, int, int, int, float]],
    ) -> list[ModelDetection]:
        """Associate PPE anatomically and expose at most one item per person/class."""
        best: dict[tuple[int, str], tuple[float, int, ModelDetection]] = {}
        for order, (class_id, class_name, bbox, confidence) in enumerate(ppe_boxes):
            person_index = cls._best_person_for_ppe(class_name, bbox, people)
            if person_index is None:
                continue
            detection: ModelDetection = {
                "class_id": class_id,
                "class_name": class_name,
                "bbox": bbox,
                "confidence": confidence,
                "person_index": person_index,
            }
            key = (person_index, class_name)
            existing = best.get(key)
            if existing is None or confidence > existing[0]:
                best[key] = (confidence, order, detection)

        selected = [(order, detection) for _, order, detection in best.values()]
        return [detection for _, detection in sorted(selected, key=lambda item: item[0])]

    @classmethod
    def _best_person_for_ppe(
        cls,
        class_name: str,
        ppe_bbox: list[int],
        people: list[tuple[int, int, int, int, float]],
    ) -> int | None:
        x1, y1, x2, y2 = ppe_bbox
        if x2 <= x1 or y2 <= y1:
            return None
        center_x = (x1 + x2) / 2.0
        center_y = (y1 + y2) / 2.0
        candidates: list[tuple[float, float, float, int]] = []
        for index, (person_x, person_y, width, height, confidence) in enumerate(people):
            person_bbox = [person_x, person_y, person_x + width, person_y + height]
            if class_name == "hat":
                valid = cls._is_valid_hat_geometry(person_bbox, center_x, center_y)
                region_bottom = person_y + cls._HAT_TOP_FRACTION * height
            elif class_name == "vest":
                valid = cls._is_valid_vest_geometry(person_bbox, center_x, center_y)
                region_bottom = person_y + cls._VEST_BOTTOM_FRACTION * height
            else:
                continue
            if not valid:
                continue
            anatomical_region = (float(person_x), float(person_y), float(person_x + width), float(region_bottom))
            score = cls._intersection_over_union(
                (float(x1), float(y1), float(x2), float(y2)),
                anatomical_region,
            )
            area = float(width * height)
            candidates.append((score, confidence, -area, index))
        return max(candidates)[3] if candidates else None

    # ------------------------------------------------------------------
    # Model lifecycle
    # ------------------------------------------------------------------

    def _load_model(self):
        if self._model is None:
            self._model = self._create_model()
        self._validate_model_classes(self._model.names)
        return self._model

    def _create_model(self) -> Any:
        if self._model_factory is not None:
            return self._model_factory(self._model_path)
        from ultralytics import YOLO

        return YOLO(str(Path(self._model_path)))

    def _expire_sessions(self, now: float) -> None:
        expired = [
            session_id
            for session_id, (_, last_seen) in self._sessions.items()
            if now - last_seen >= self._session_ttl_seconds
        ]
        for session_id in expired:
            self._sessions.pop(session_id, None)
            self._smoothers.pop(session_id, None)
            self._session_locks.pop(session_id, None)

    # ------------------------------------------------------------------
    # Geometry helpers (US-29)
    # ------------------------------------------------------------------

    @classmethod
    def _is_valid_hat_geometry(
        cls,
        person_bbox_xyxy: list[int],
        hat_cx: float,
        hat_cy: float,
    ) -> bool:
        """Hat center must be inside the person horizontally AND in the top 40%."""
        px1, py1, px2, py2 = person_bbox_xyxy
        person_height = py2 - py1
        if person_height <= 0 or (px2 - px1) <= 0:
            return False
        return (px1 <= hat_cx <= px2) and (py1 <= hat_cy <= py1 + cls._HAT_TOP_FRACTION * person_height)

    @classmethod
    def _is_valid_vest_geometry(
        cls,
        person_bbox_xyxy: list[int],
        vest_cx: float,
        vest_cy: float,
    ) -> bool:
        """Vest center must be inside the person bbox AND in the top 85% (torso)."""
        px1, py1, px2, py2 = person_bbox_xyxy
        person_height = py2 - py1
        if person_height <= 0 or (px2 - px1) <= 0:
            return False
        return (px1 <= vest_cx <= px2) and (py1 <= vest_cy <= py1 + cls._VEST_BOTTOM_FRACTION * person_height)

    # ------------------------------------------------------------------
    # Shared static helpers
    # ------------------------------------------------------------------

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
            raise RuntimeError(
                f"yolo11m_safety.pt class mapping must be {cls.SOURCE_CLASS_NAMES}, received {normalized}"
            )

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
    """Redacts YuNet faces with a per-person conservative fallback."""

    def __init__(
        self,
        model_path: str | None = None,
        *,
        score_threshold: float = 0.6,
        face_margin_ratio: float = 0.2,
        face_detector: FaceDetector | None = None,
    ) -> None:
        self._face_detector = face_detector or (
            YuNetFaceDetector(model_path, score_threshold=score_threshold) if model_path is not None else None
        )
        self._face_margin_ratio = face_margin_ratio

    def preload(self) -> None:
        if self._face_detector is not None:
            self._face_detector.preload()

    def redact_snapshot(
        self,
        frame: np.ndarray,
        people: list[SnapshotPerson],
    ) -> PrivacyRedactionResult:
        if self._face_detector is None:
            return redact_person_head_regions(frame, people)
        detector_failed = False
        try:
            faces = self._face_detector.detect(frame)
        except Exception as exc:
            detector_failed = True
            faces = []
            logger.warning(
                "YuNet face detection failed; using person-head fallback (%s).",
                type(exc).__name__,
            )
        return redact_identity_regions(
            frame,
            people,
            faces,
            face_margin_ratio=self._face_margin_ratio,
            face_detector_failed=detector_failed,
        )

    @staticmethod
    def annotate_snapshot(
        frame: np.ndarray,
        people: list[SnapshotPerson],
        detections: list[ModelDetection],
    ) -> np.ndarray:
        return annotate_snapshot(frame, people, detections)
