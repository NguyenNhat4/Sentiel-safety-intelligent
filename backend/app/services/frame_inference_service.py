import base64
import binascii
import time
from collections.abc import Callable
from uuid import uuid4

import cv2
import numpy as np

from backend.app.integrations.person_tracking import PersonTrackingAdapter
from backend.app.integrations.ppe_vision import PpeObserver, get_ppe_vision_adapter
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
from backend.app.services.ppe_requirement_service import PpeStatus, should_alert_for_missing_ppe
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
        person_model_path: str | None = None,
        ppe_observer: PpeObserver | None = None,
        requirement_loader: Callable[[str, str], PpeRequirementResponse] | None = None,
        missing_ppe_threshold: float = 0.5,
    ) -> None:
        from backend.app.core.config import get_settings

        settings = get_settings()
        ppe_model_path = settings.ppe_model_path
        self._person_model_path = person_model_path or settings.person_model_path
        self._person_model = None
        adapter = get_ppe_vision_adapter(ppe_model_path)
        self._ppe_observer = ppe_observer or adapter.observe
        self._ppe_preloader = adapter.preload if ppe_observer is None else lambda: None
        self._requirement_loader = requirement_loader or self._load_requirements
        self._missing_ppe_threshold = missing_ppe_threshold
        self._rule_engine = SafetyRuleEngine(missing_ppe_threshold)
        self._person_tracker = PersonTrackingAdapter(person_model_path or self._person_model_path)
        self._violation_tracker = ViolationTrackingService()

    def preload_models(self) -> None:
        self._load_person_model()
        self._ppe_preloader()
        self._person_tracker.preload()

    def occurrences_belong_to_zone(self, session_id: str, zone_id: str, occurrence_ids: list[str]) -> bool:
        expected = (session_id, f"zone_intrusion:{zone_id}")
        return all(
            self._violation_tracker.occurrence_context(occurrence_id) == expected for occurrence_id in occurrence_ids
        )

    def infer(self, request: FrameInferenceRequest) -> FrameInferenceResponse:
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
        requirements = self._requirement_loader(request.camera_id, request.zone_id)
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
                    track_id=track_id,
                    bbox=[x, y, x + box_width, y + box_height],
                    confidence=round(confidence, 3),
                    foot_point=foot_point,
                    inside_zone=inside_zone,
                    zone_memberships=memberships,
                    safety_shirt=safety_shirt,
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
                if membership_by_id.get(zone.zone_id) and zone.machine_state == "running":
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
                "violation": zone.machine_state == "running"
                and any(
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
                "safety_shirt_required": True,
                "camera_id": request.camera_id,
                "zone_id": primary_zone_id,
                "zone_revision": request.zone_revision,
                "zone_results": zone_results,
                "ppe_requirements": {
                    "helmet_required": requirements.helmet_required,
                    "safety_glasses_required": requirements.safety_glasses_required,
                    "gloves_required": requirements.gloves_required,
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
        return self._person_tracker.track(session_id, frame)

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
