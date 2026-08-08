import base64
import binascii
from collections.abc import Callable

import cv2
import numpy as np

from backend.app.integrations.ppe_vision import PpeObserver, PpeVisionAdapter
from backend.app.schemas.analysis import (
    FrameInferenceRequest,
    FrameInferenceResponse,
    ModelDetection,
    PersonDetection,
    PersonPpeObservations,
)
from backend.app.schemas.ppe_requirement import PpeRequirementResponse
from backend.app.services.ppe_requirement_service import PpeStatus, should_alert_for_missing_ppe
from backend.app.services.safety_rule_engine import RulePersonObservation, SafetyRuleEngine


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
        from backend.app.core.config import get_settings

        settings = get_settings()
        ppe_model_path = settings.ppe_model_path
        self._person_model_path = person_model_path or ppe_model_path
        self._person_model = None
        adapter = PpeVisionAdapter(ppe_model_path)
        self._ppe_observer = ppe_observer or adapter.observe
        self._ppe_preloader = adapter.preload if ppe_observer is None else lambda: None
        self._requirement_loader = requirement_loader or self._load_requirements
        self._missing_ppe_threshold = missing_ppe_threshold
        self._rule_engine = SafetyRuleEngine(missing_ppe_threshold)

    def preload_models(self) -> None:
        self._load_person_model()
        self._ppe_preloader()

    def infer(self, request: FrameInferenceRequest) -> FrameInferenceResponse:
        frame = self._decode_frame(request.image_data)
        height, width = frame.shape[:2]
        polygon = np.array(
            [[point.x * width, point.y * height] for point in request.zone_points],
            dtype=np.float32,
        )

        detected_people = self._detect_people(frame)
        vision_result = self._ppe_observer(frame, detected_people)
        if isinstance(vision_result, dict) and "people" in vision_result:
            observations = vision_result["people"]
            detections = [ModelDetection.model_validate(item) for item in vision_result["detections"]]
        else:
            observations = vision_result
            detections = []
        requirements = self._requirement_loader(request.camera_id, request.zone_id)
        people = []
        rule_people = []
        for index, (x, y, box_width, box_height, confidence) in enumerate(detected_people):
            foot_point = [x + box_width // 2, y + box_height]
            inside_zone = len(polygon) == 4 and cv2.pointPolygonTest(polygon, tuple(foot_point), False) >= 0
            safety_shirt = self._has_safety_shirt(frame, x, y, box_width, box_height)
            obs_data = (
                observations[index]
                if index < len(observations)
                else {
                    "helmet": {"status": "unknown", "confidence": None},
                    "safety_glasses": {"status": "unknown", "confidence": None},
                    "gloves": {"status": "unknown", "confidence": None},
                }
            )
            ppe = self._derive_missing_ppe(
                PersonPpeObservations.model_validate(obs_data),
                person_confidence=confidence,
                box_width=box_width,
                box_height=box_height,
            )
            rule_people.append(RulePersonObservation(confidence=confidence, inside_zone=inside_zone, ppe=ppe))
            people.append(
                PersonDetection(
                    bbox=[x, y, x + box_width, y + box_height],
                    confidence=round(confidence, 3),
                    foot_point=foot_point,
                    inside_zone=inside_zone,
                    safety_shirt=safety_shirt,
                    ppe=ppe,
                    missing_required_ppe=[],
                )
            )

        decision = self._rule_engine.evaluate(
            people=rule_people,
            requirements=requirements,
            machine_state=request.machine_state,
            zone_active=len(polygon) == 4,
        )
        for person, missing in zip(people, decision.missing_required_ppe, strict=True):
            person.missing_required_ppe = missing

        return FrameInferenceResponse(
            result=decision.outcome,
            review_required=decision.review_required,
            people=people,
            detections=detections,
            snapshot_data=request.image_data if decision.review_required else None,
            rule={
                "person_inside_zone": decision.person_inside_zone,
                "machine_state": request.machine_state,
                "safety_shirt_required": True,
                "camera_id": request.camera_id,
                "zone_id": request.zone_id,
                "ppe_requirements": {
                    "helmet_required": requirements.helmet_required,
                    "safety_glasses_required": requirements.safety_glasses_required,
                    "gloves_required": requirements.gloves_required,
                },
                "ppe_alert": decision.ppe_alert,
            },
        )

    def _derive_missing_ppe(
        self,
        ppe: PersonPpeObservations,
        *,
        person_confidence: float,
        box_width: int,
        box_height: int,
    ) -> PersonPpeObservations:
        if person_confidence < self._missing_ppe_threshold or box_width <= 0 or box_height <= 0:
            return ppe
        values = ppe.model_dump()
        for name, observation in values.items():
            if observation["status"] == "unknown":
                values[name] = {"status": "missing", "confidence": None}
        return PersonPpeObservations.model_validate(values)

    def _missing_required_ppe(
        self,
        ppe: PersonPpeObservations,
        requirements: PpeRequirementResponse,
        *,
        person_confidence: float,
        association_is_valid: bool,
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
                person_confidence=person_confidence,
                threshold=self._missing_ppe_threshold,
                association_is_valid=association_is_valid,
            )
        ]

    @staticmethod
    def _load_requirements(camera_id: str, zone_id: str) -> PpeRequirementResponse:
        from backend.app.core.database import SessionLocal
        from backend.app.services.ppe_requirement_service import PpeRequirementService

        with SessionLocal() as db:
            return PpeRequirementService(db).get(camera_id, zone_id)

    def _detect_people(self, frame: np.ndarray) -> list[tuple[int, int, int, int, float]]:
        model = self._load_person_model()

        results = model.predict(frame, classes=[0], conf=0.35, verbose=False)
        people = []
        for box in results[0].boxes:
            x1, y1, x2, y2 = (int(value) for value in box.xyxy[0].tolist())
            people.append((x1, y1, x2 - x1, y2 - y1, float(box.conf[0])))
        return people

    def _load_person_model(self):
        if self._person_model is None:
            from pathlib import Path

            from ultralytics import YOLO

            model_path = Path(self._person_model_path)
            if not model_path.exists() and Path(model_path.name).exists():
                model_path = Path(model_path.name)

            self._person_model = YOLO(str(model_path))
        return self._person_model

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
