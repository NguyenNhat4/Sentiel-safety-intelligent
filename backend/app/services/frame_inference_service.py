import base64
import binascii
import threading
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
from backend.app.integrations.remote_vision import get_remote_vision_adapter
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
    """Evaluate one frame for browser compatibility and server-side camera flows."""

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
        self._inference_size = (settings.inference_frame_width, settings.inference_frame_height)
        self._model_path = model_path or settings.ppe_model_path
        self._fallback_model = None
        if vision_analyzer is not None:
            self._vision_analyzer = vision_analyzer
            self._ppe_observer = ppe_observer
            self._model_preloader = lambda: None
        elif ppe_observer is not None:
            self._vision_analyzer = None
            self._ppe_observer = ppe_observer
            self._model_preloader = lambda: None
        elif settings.vision_provider == "remote":
            adapter = get_remote_vision_adapter(
                base_url=settings.vision_remote_url,
                api_key=settings.vision_remote_api_key.get_secret_value(),
                timeout_seconds=settings.vision_remote_timeout_seconds,
            )
            self._vision_analyzer = adapter.analyze
            self._ppe_observer = None
            self._model_preloader = adapter.preload
        else:
            adapter = get_ppe_vision_adapter(self._model_path)
            self._vision_analyzer = adapter.analyze
            self._ppe_observer = adapter.observe
            self._model_preloader = adapter.preload
        self._requirement_loader = requirement_loader or self._load_requirements
        self._missing_ppe_threshold = missing_ppe_threshold
        self._rule_engine = SafetyRuleEngine(missing_ppe_threshold)
        self._tracker_lock = threading.RLock()
        self._violation_tracker = ViolationTrackingService(
            activation_frames=settings.violation_frame,
            ppe_confirmation_frames=settings.ppe_alert_confirm_frames,
            ppe_revoke_confirmation_seconds=settings.ppe_revoke_confirm_seconds,
            zone_activation_frames=settings.zone_alert_confirm_frames,
        )

    def preload_models(self) -> None:
        self._model_preloader()

    def occurrences_belong_to_zone(self, session_id: str, zone_id: str, occurrence_ids: list[str]) -> bool:
        expected_rule = f"zone_intrusion:{zone_id}"
        return all(
            (context := self._violation_tracker.occurrence_context(occurrence_id)) is not None
            and context[0] == session_id
            and context[2] == expected_rule
            for occurrence_id in occurrence_ids
        )

    def occurrences_belong_to_track(
        self,
        session_id: str,
        track_id: int,
        occurrence_ids: list[str],
    ) -> bool:
        return all(
            (context := self._violation_tracker.occurrence_context(occurrence_id)) is not None
            and context[0] == session_id
            and context[1] == track_id
            for occurrence_id in occurrence_ids
        )

    def infer(
        self,
        request: FrameInferenceRequest,
        *,
        requirements: PpeRequirementResponse | None = None,
        requirements_by_zone: dict[str, PpeRequirementResponse] | None = None,
    ) -> FrameInferenceResponse:
        frame = self._decode_frame(request.image_data)
        return self.infer_decoded_frame(
            request,
            frame,
            requirements=requirements,
            requirements_by_zone=requirements_by_zone,
        )

    def infer_decoded_frame(
        self,
        request: FrameInferenceRequest,
        frame: np.ndarray,
        *,
        requirements: PpeRequirementResponse | None = None,
        requirements_by_zone: dict[str, PpeRequirementResponse] | None = None,
        bypass_confirmation: bool = False,
    ) -> FrameInferenceResponse:
        """Infer from an existing BGR frame without a JPEG/Base64 round trip."""
        source_height, source_width = frame.shape[:2]
        if frame.shape[1] > self._inference_size[0] or frame.shape[0] > self._inference_size[1]:
            frame = cv2.resize(frame, self._inference_size, interpolation=cv2.INTER_AREA)
        now = time.monotonic()
        if request.monitoring_session_id is not None and request.frame_id is not None:
            with self._tracker_lock:
                accepted = self._violation_tracker.accept_frame(
                    str(request.monitoring_session_id), request.frame_id, now=now
                )
            if not accepted:
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

        if requirements_by_zone is None:
            decision = self._rule_engine.evaluate(
                people=rule_people,
                requirements=requirements,
                machine_state=request.machine_state,
                zone_active=False,
            )
            for person, missing in zip(people, decision.missing_required_ppe, strict=True):
                person.missing_required_ppe = missing
        else:
            for person, rule_person in zip(people, rule_people, strict=True):
                inside_zone_ids = {item.zone_id for item in person.zone_memberships if item.inside}
                applicable = [
                    requirement for zone_id, requirement in requirements_by_zone.items() if zone_id in inside_zone_ids
                ]
                if not applicable:
                    applicable = list(requirements_by_zone.values())
                missing: set[str] = set()
                if request.machine_state == "running":
                    for requirement in applicable:
                        evaluated = self._rule_engine.evaluate(
                            people=[rule_person],
                            requirements=requirement,
                            machine_state=request.machine_state,
                            zone_active=False,
                        )
                        missing.update(evaluated.missing_required_ppe[0])
                person.missing_required_ppe = sorted(missing)

        observed_rules: dict[int, set[str]] = {}
        applicable_ppe_rules: set[tuple[int, str]] = set()
        for person in people:
            rules = {f"missing_ppe:{item}" for item in person.missing_required_ppe}
            membership_by_id = {item.zone_id: item.inside for item in person.zone_memberships}
            if requirements_by_zone is None:
                if requirements.restricted_area_detection_enabled:
                    rules.add("restricted_area_person")
                for zone in active_zones:
                    if membership_by_id.get(zone.zone_id) and requirements.zone_intrusion_enabled:
                        rules.add(f"zone_intrusion:{zone.zone_id}" if multi_zone_mode else "zone_intrusion")
            else:
                if request.machine_state == "running":
                    for zone in active_zones:
                        zone_requirement = requirements_by_zone.get(zone.zone_id)
                        if zone_requirement is None:
                            continue
                        if zone_requirement.hat_required:
                            applicable_ppe_rules.add((person.track_id, "missing_ppe:hat"))
                        if zone_requirement.vest_required:
                            applicable_ppe_rules.add((person.track_id, "missing_ppe:vest"))
                for zone in active_zones:
                    zone_requirement = requirements_by_zone.get(zone.zone_id)
                    if zone_requirement is None:
                        continue
                    if zone_requirement.restricted_area_detection_enabled:
                        rules.add(f"restricted_area_person:{zone.zone_id}")
                    if membership_by_id.get(zone.zone_id) and zone_requirement.zone_intrusion_enabled:
                        rules.add(f"zone_intrusion:{zone.zone_id}")
            observed_rules[person.track_id] = rules

        if request.monitoring_session_id is not None:
            ppe_present_items = {
                person.track_id: {item for item in ("hat", "vest") if getattr(person.ppe, item).status == "present"}
                for person in people
            }
            with self._tracker_lock:
                active = self._violation_tracker.evaluate(
                    str(request.monitoring_session_id),
                    observed_rules,
                    {person.track_id for person in people},
                    track_positions={
                        person.track_id: (person.foot_point[0] / width, person.foot_point[1] / height)
                        for person in people
                    },
                    ppe_present_items=ppe_present_items,
                    applicable_ppe_rules=applicable_ppe_rules if requirements_by_zone is not None else None,
                    bypass_confirmation=bypass_confirmation,
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
                "machine_state": request.machine_state,
                "person_inside_zone": any(
                    membership.zone_id == zone.zone_id and membership.inside
                    for person in people
                    for membership in person.zone_memberships
                ),
                "violation": (
                    requirements_by_zone.get(zone.zone_id).zone_intrusion_enabled
                    if requirements_by_zone is not None and requirements_by_zone.get(zone.zone_id) is not None
                    else True
                )
                and any(
                    membership.zone_id == zone.zone_id and membership.inside
                    for person in people
                    for membership in person.zone_memberships
                ),
            }
            for zone in active_zones
        ]
        person_inside_zone = any(item["person_inside_zone"] for item in zone_results)
        primary_zone = self._primary_zone(active_zones, people)
        primary_machine_state = request.machine_state
        primary_zone_id = primary_zone.zone_id if primary_zone else request.zone_id

        response = FrameInferenceResponse(
            result="violate" if has_active_violation else "normal",
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
                    "restricted_area_detection_enabled": requirements.restricted_area_detection_enabled,
                    "zone_intrusion_enabled": requirements.zone_intrusion_enabled,
                },
                "zone_requirements": {
                    zone_id: requirement.model_dump(mode="json")
                    for zone_id, requirement in (requirements_by_zone or {}).items()
                },
                "restricted_area_alert": any(
                    violation.rule_key.startswith("restricted_area_person")
                    for person in people
                    for violation in person.active_violations
                ),
                "ppe_alert": any(
                    violation.rule_key.startswith("missing_ppe:")
                    for person in people
                    for violation in person.active_violations
                ),
            },
        )
        self._restore_source_coordinates(response, source_width, source_height, width, height)
        return response

    def end_session(self, session_id: str) -> None:
        with self._tracker_lock:
            self._violation_tracker.end_session(session_id)
        self.release_vision_session(session_id)

    def release_vision_session(self, session_id: str) -> None:
        analyzer_owner = getattr(self._vision_analyzer, "__self__", None)
        if analyzer_owner is not None and hasattr(analyzer_owner, "end_session"):
            analyzer_owner.end_session(session_id)

    @staticmethod
    def _restore_source_coordinates(
        response: FrameInferenceResponse,
        source_width: int,
        source_height: int,
        inference_width: int,
        inference_height: int,
    ) -> None:
        if source_width == inference_width and source_height == inference_height:
            return
        scale_x = source_width / inference_width
        scale_y = source_height / inference_height

        def scale_box(box: list[int]) -> list[int]:
            return [
                round(box[0] * scale_x),
                round(box[1] * scale_y),
                round(box[2] * scale_x),
                round(box[3] * scale_y),
            ]

        for person in response.people:
            person.bbox = scale_box(person.bbox)
            person.foot_point = [
                round(person.foot_point[0] * scale_x),
                round(person.foot_point[1] * scale_y),
            ]
        for detection in response.detections:
            detection.bbox = scale_box(detection.bbox)

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
        if rule_key == "restricted_area_person":
            return legacy_zone_id
        if rule_key.startswith("restricted_area_person:"):
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
