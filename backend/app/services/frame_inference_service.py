import base64
import binascii
import time
from collections.abc import Callable
from uuid import uuid4

import cv2
import numpy as np

from backend.app.integrations.ppe_vision import (
    PpeObserver,
    SafetyVisionAnalyzer,
    get_ppe_vision_adapter,
)
from backend.app.schemas.analysis import (
    ActiveViolation as ActiveViolationSchema,
)
from backend.app.schemas.analysis import (
    FrameInferenceRequest,
    FrameInferenceResponse,
    ModelDetection,
    PersonDetection,
    PersonPpeObservations,
    ZoneMembership,
)
from backend.app.schemas.monitoring_zone import MonitoringZone
from backend.app.schemas.ppe_requirement import PpeRequirementResponse
from backend.app.services.monitoring_zone_service import validate_zone_geometry
from backend.app.services.safety_rule_engine import RulePersonObservation, SafetyRuleEngine
from backend.app.services.violation_tracking_service import ViolationTrackingService


class InvalidFrameError(ValueError):
    pass


class StaleFrameError(ValueError):
    pass


class FrameInferenceService:
    """Small baseline detector for the browser video review flow."""

    def __init__(
        self,
        model_path: str | None = None,
        vision_analyzer: SafetyVisionAnalyzer | None = None,
        ppe_observer: PpeObserver | None = None,
        requirement_loader: Callable[[str, str], PpeRequirementResponse] | None = None,
        missing_ppe_threshold: float = 0.5,
    ) -> None:
        from backend.app.core.config import get_settings

        settings = get_settings()
        self._model_path = model_path or settings.ppe_model_path
        self._fallback_model = None
        adapter = get_ppe_vision_adapter(self._model_path)
        self._vision_analyzer = vision_analyzer or (adapter.analyze if ppe_observer is None else None)
        self._ppe_observer = ppe_observer or adapter.observe
        self._model_preloader = adapter.preload if vision_analyzer is None and ppe_observer is None else lambda: None
        self._requirement_loader = requirement_loader or self._load_requirements
        self._missing_ppe_threshold = missing_ppe_threshold
        self._rule_engine = SafetyRuleEngine(missing_ppe_threshold)
        self._violation_tracker = ViolationTrackingService(activation_frames=settings.violation_frame)

    def preload_models(self) -> None:
        self._model_preloader()

    def occurrences_belong_to_zone(self, session_id: str, zone_id: str, occurrence_ids: list[str]) -> bool:
        expected = (session_id, f"zone_intrusion:{zone_id}")
        return all(
            self._violation_tracker.occurrence_context(occurrence_id) == expected for occurrence_id in occurrence_ids
        )

    def infer(
        self,
        request: FrameInferenceRequest,
        *,
        requirements: PpeRequirementResponse | None = None,
    ) -> FrameInferenceResponse:
        frame = self._decode_frame(request.image_data)
        now = time.monotonic()
        if (
            request.monitoring_session_id is not None
            and request.frame_id is not None
            and not self._violation_tracker.accept_frame(str(request.monitoring_session_id), request.frame_id, now=now)
        ):
            raise StaleFrameError("frame_id must increase within a monitoring session")
        height, width = frame.shape[:2]
        multi_zone_mode = request.zones is not None
        zones = self._normalized_zones(request)
        validate_zone_geometry(zones)
        active_zones = [zone for zone in sorted(zones, key=lambda item: item.order) if zone.enabled]
        polygons = {
            zone.zone_id: np.array(
                [[point.x * width, point.y * height] for point in zone.points],
                dtype=np.float32,
            )
            for zone in active_zones
        }

        if self._vision_analyzer is not None:
            vision_result = self._vision_analyzer(
                frame,
                str(request.monitoring_session_id) if request.monitoring_session_id is not None else None,
                now,
            )
            detected_people = vision_result["canonical_people"]
            observations = vision_result["people"]
            detections = [ModelDetection.model_validate(item) for item in vision_result["detections"]]
        else:
            if request.monitoring_session_id is None:
                detected_people = [(*person, index + 1) for index, person in enumerate(self._detect_people(frame))]
            else:
                detected_people = self._track_people(str(request.monitoring_session_id), frame)
            vision_result = self._ppe_observer(frame, [person[:5] for person in detected_people])
            if isinstance(vision_result, dict) and "people" in vision_result:
                observations = vision_result["people"]
                detections = [ModelDetection.model_validate(item) for item in vision_result["detections"]]
            else:
                observations = vision_result
                detections = []
        requirements = requirements or self._requirement_loader(request.camera_id, request.zone_id)
        people = []
        rule_people = []
        for index, (x, y, box_width, box_height, confidence, track_id) in enumerate(detected_people):
            foot_point = [x + box_width // 2, y + box_height]
            memberships = [
                ZoneMembership(
                    zone_id=zone.zone_id,
                    inside=cv2.pointPolygonTest(polygons[zone.zone_id], tuple(foot_point), False) >= 0,
                )
                for zone in active_zones
            ]
            inside_zone = any(item.inside for item in memberships)
            obs_data = (
                observations[index]
                if index < len(observations)
                else {
                    "hat": {"status": "unknown", "confidence": None},
                    "vest": {"status": "unknown", "confidence": None},
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
                    track_id=track_id,
                    bbox=[x, y, x + box_width, y + box_height],
                    confidence=round(confidence, 3),
                    foot_point=foot_point,
                    inside_zone=inside_zone,
                    zone_memberships=memberships,
                    ppe=ppe,
                    missing_required_ppe=[],
                )
            )

        decision = self._rule_engine.evaluate(
            people=rule_people,
            requirements=requirements,
            machine_state="stopped",
            zone_active=False,
        )
        for person, missing in zip(people, decision.missing_required_ppe, strict=True):
            person.missing_required_ppe = missing

        observed_rules: dict[int, set[str]] = {}
        for person in people:
            rules = {f"missing_ppe:{item}" for item in person.missing_required_ppe}
            membership_by_id = {item.zone_id: item.inside for item in person.zone_memberships}
            for zone in active_zones:
                if membership_by_id.get(zone.zone_id):
                    rules.add(f"zone_intrusion:{zone.zone_id}" if multi_zone_mode else "zone_intrusion")
            observed_rules[person.track_id] = rules

        if request.monitoring_session_id is not None:
            active = self._violation_tracker.evaluate(
                str(request.monitoring_session_id),
                observed_rules,
                {person.track_id for person in people},
                track_positions={
                    person.track_id: (person.foot_point[0] / width, person.foot_point[1] / height) for person in people
                },
                now=now,
            )
            for person in people:
                person.active_violations = [
                    ActiveViolationSchema(
                        occurrence_id=item.occurrence_id,
                        rule_key=item.rule_key,
                        zone_id=self._zone_id_for_rule(item.rule_key, request.zone_id),
                        is_new=item.is_new,
                    )
                    for item in active.get(person.track_id, [])
                ]
        else:
            for person in people:
                person.active_violations = [
                    ActiveViolationSchema(
                        occurrence_id=uuid4(),
                        rule_key=rule,
                        zone_id=self._zone_id_for_rule(rule, request.zone_id),
                        is_new=True,
                    )
                    for rule in sorted(observed_rules[person.track_id])
                ]

        has_active_violation = any(person.active_violations for person in people)
        review_required = any(violation.is_new for person in people for violation in person.active_violations)

        zone_results = [
            {
                "zone_id": zone.zone_id,
                "machine_state": zone.machine_state,
                "person_inside_zone": any(
                    membership.zone_id == zone.zone_id and membership.inside
                    for person in people
                    for membership in person.zone_memberships
                ),
                "violation": any(
                    membership.zone_id == zone.zone_id and membership.inside
                    for person in people
                    for membership in person.zone_memberships
                ),
            }
            for zone in active_zones
        ]
        zone_violation = any(item["violation"] for item in zone_results)
        person_inside_zone = any(item["person_inside_zone"] for item in zone_results)
        primary_zone = self._primary_zone(active_zones, people)
        primary_machine_state = primary_zone.machine_state if primary_zone else request.machine_state
        primary_zone_id = primary_zone.zone_id if primary_zone else request.zone_id

        return FrameInferenceResponse(
            result="violate" if decision.ppe_alert or zone_violation else "normal",
            review_required=review_required,
            has_active_violation=has_active_violation,
            people=people,
            detections=detections,
            snapshot_data=request.image_data if review_required else None,
            rule={
                "person_inside_zone": person_inside_zone,
                "machine_state": primary_machine_state,
                "ppe_profile": requirements.profile,
                "camera_id": request.camera_id,
                "zone_id": primary_zone_id,
                "zone_revision": request.zone_revision,
                "zone_results": zone_results,
                "ppe_requirements": {
                    "profile": requirements.profile,
                    "hat_required": requirements.hat_required,
                    "vest_required": requirements.vest_required,
                },
                "ppe_alert": decision.ppe_alert,
            },
        )

    @staticmethod
    def _normalized_zones(request: FrameInferenceRequest) -> list[MonitoringZone]:
        if request.zones is not None:
            return request.zones
        if len(request.zone_points) != 4:
            return []
        return [
            MonitoringZone(
                zone_id=request.zone_id,
                display_name=request.zone_id,
                points=request.zone_points,
                machine_state=request.machine_state,
                enabled=True,
                order=0,
            )
        ]

    @staticmethod
    def _zone_id_for_rule(rule_key: str, legacy_zone_id: str) -> str | None:
        if rule_key == "zone_intrusion":
            return legacy_zone_id
        if rule_key.startswith("zone_intrusion:"):
            return rule_key.split(":", 1)[1]
        return None

    @staticmethod
    def _primary_zone(zones: list[MonitoringZone], people: list[PersonDetection]) -> MonitoringZone | None:
        new_zone_ids = {
            violation.zone_id
            for person in people
            for violation in person.active_violations
            if violation.is_new and violation.zone_id is not None
        }
        return next((zone for zone in zones if zone.zone_id in new_zone_ids), zones[0] if zones else None)

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

    def _track_people(self, session_id: str, frame: np.ndarray):
        return [(*person, index + 1) for index, person in enumerate(self._detect_people(frame))]

    @staticmethod
    def _load_requirements(camera_id: str, zone_id: str) -> PpeRequirementResponse:
        from backend.app.core.database import SessionLocal
        from backend.app.services.ppe_requirement_service import PpeRequirementService

        with SessionLocal() as db:
            return PpeRequirementService(db).get(camera_id, zone_id)

    def _detect_people(self, frame: np.ndarray) -> list[tuple[int, int, int, int, float]]:
        model = self._load_fallback_model()

        results = model.predict(frame, classes=[3], conf=0.35, verbose=False)
        people = []
        for box in results[0].boxes:
            x1, y1, x2, y2 = (int(value) for value in box.xyxy[0].tolist())
            people.append((x1, y1, x2 - x1, y2 - y1, float(box.conf[0])))
        return people

    def _load_fallback_model(self):
        if self._fallback_model is None:
            from pathlib import Path

            from ultralytics import YOLO

            model_path = Path(self._model_path)
            if not model_path.exists() and Path(model_path.name).exists():
                model_path = Path(model_path.name)

            self._fallback_model = YOLO(str(model_path))
        return self._fallback_model

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
