import base64
import binascii
from collections.abc import Callable

import cv2
import numpy as np

from backend.app.integrations.ppe_vision import PpeObserver, PpeVisionAdapter
from backend.app.schemas.analysis import (
    FrameInferenceRequest,
    FrameInferenceResponse,
    PersonDetection,
    PersonPpeObservations,
)
from backend.app.schemas.ppe_requirement import PpeRequirementResponse
from backend.app.services.ppe_requirement_service import PpeStatus, should_alert_for_missing_ppe


class InvalidFrameError(ValueError):
    pass


class FrameInferenceService:
    """Small baseline detector for the browser video review flow."""

    def __init__(
        self,
        person_model_path: str | None = None,
        ppe_observer: PpeObserver | None = None,
        requirement_loader: Callable[[str, str], PpeRequirementResponse] | None = None,
        missing_ppe_threshold: float = 0.5,
    ) -> None:
        if person_model_path is None:
            from backend.app.core.config import get_settings

            settings = get_settings()
            person_model_path = settings.person_model_path
            ppe_model_path = settings.ppe_model_path
        else:
            from backend.app.core.config import get_settings

            ppe_model_path = get_settings().ppe_model_path
        self._person_model_path = person_model_path
        self._person_model = None
        self._ppe_observer = ppe_observer or PpeVisionAdapter(ppe_model_path).observe
        self._requirement_loader = requirement_loader or self._load_requirements
        self._missing_ppe_threshold = missing_ppe_threshold

    def infer(self, request: FrameInferenceRequest) -> FrameInferenceResponse:
        frame = self._decode_frame(request.image_data)
        height, width = frame.shape[:2]
        polygon = np.array(
            [[point.x * width, point.y * height] for point in request.zone_points],
            dtype=np.float32,
        )

        detected_people = self._detect_people(frame)
        observations = self._ppe_observer(frame, detected_people)
        requirements = self._requirement_loader(request.camera_id, request.zone_id)
        people = []
        for index, (x, y, box_width, box_height, confidence) in enumerate(detected_people):
            foot_point = [x + box_width // 2, y + box_height]
            inside_zone = cv2.pointPolygonTest(polygon, tuple(foot_point), False) >= 0
            safety_shirt = self._has_safety_shirt(frame, x, y, box_width, box_height)
            ppe = PersonPpeObservations.model_validate(observations[index])
            missing_required_ppe = self._missing_required_ppe(ppe, requirements)
            people.append(
                PersonDetection(
                    bbox=[x, y, x + box_width, y + box_height],
                    confidence=round(confidence, 3),
                    foot_point=foot_point,
                    inside_zone=inside_zone,
                    safety_shirt=safety_shirt,
                    ppe=ppe,
                    missing_required_ppe=missing_required_ppe,
                )
            )

        person_inside_zone = any(person.inside_zone for person in people)
        ppe_alert = any(person.missing_required_ppe for person in people)
        review_required = (person_inside_zone and request.machine_state == "running") or ppe_alert
        violation = review_required

        return FrameInferenceResponse(
            result="violate" if violation else "normal",
            review_required=review_required,
            people=people,
            snapshot_data=request.image_data if review_required else None,
            rule={
                "person_inside_zone": person_inside_zone,
                "machine_state": request.machine_state,
                "safety_shirt_required": True,
                "camera_id": request.camera_id,
                "zone_id": request.zone_id,
                "ppe_alert": ppe_alert,
            },
        )

    def _missing_required_ppe(
        self,
        ppe: PersonPpeObservations,
        requirements: PpeRequirementResponse,
    ) -> list[str]:
        fields = (
            ("helmet", requirements.helmet_required, ppe.helmet),
            ("safety_glasses", requirements.safety_glasses_required, ppe.safety_glasses),
            ("gloves", requirements.gloves_required, ppe.gloves),
        )
        return [
            name
            for name, required, observation in fields
            if should_alert_for_missing_ppe(
                required=required,
                status=PpeStatus(observation.status),
                confidence=observation.confidence,
                threshold=self._missing_ppe_threshold,
            )
        ]

    @staticmethod
    def _load_requirements(camera_id: str, zone_id: str) -> PpeRequirementResponse:
        from backend.app.core.database import SessionLocal
        from backend.app.services.ppe_requirement_service import PpeRequirementService

        with SessionLocal() as db:
            return PpeRequirementService(db).get(camera_id, zone_id)

    def _detect_people(self, frame: np.ndarray) -> list[tuple[int, int, int, int, float]]:
        if self._person_model is None:
            from pathlib import Path

            from ultralytics import YOLO

            model_path = Path(self._person_model_path)
            if not model_path.exists() and Path(model_path.name).exists():
                model_path = Path(model_path.name)

            self._person_model = YOLO(str(model_path))

        results = self._person_model.predict(frame, classes=[0], conf=0.35, verbose=False)
        people = []
        for box in results[0].boxes:
            x1, y1, x2, y2 = (int(value) for value in box.xyxy[0].tolist())
            people.append((x1, y1, x2 - x1, y2 - y1, float(box.conf[0])))
        return people

    @staticmethod
    def _has_safety_shirt(
        frame: np.ndarray,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> bool:
        frame_height, frame_width = frame.shape[:2]
        x1 = max(0, x + int(width * 0.18))
        x2 = min(frame_width, x + int(width * 0.82))
        y1 = max(0, y + int(height * 0.2))
        y2 = min(frame_height, y + int(height * 0.62))
        torso = frame[y1:y2, x1:x2]
        if torso.size == 0:
            return False

        hsv = cv2.cvtColor(torso, cv2.COLOR_BGR2HSV)
        high_visibility = cv2.inRange(
            hsv,
            np.array([12, 80, 90], dtype=np.uint8),
            np.array([95, 255, 255], dtype=np.uint8),
        )
        visible_ratio = cv2.countNonZero(high_visibility) / high_visibility.size
        return visible_ratio >= 0.08

    @staticmethod
    def _decode_frame(image_data: str) -> np.ndarray:
        encoded = image_data.split(",", 1)[-1]
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise InvalidFrameError("image_data must be a valid base64 image") from exc

        frame = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            raise InvalidFrameError("image_data could not be decoded as an image")
        return frame


frame_inference_service = FrameInferenceService()
