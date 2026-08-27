import base64
import binascii
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import cv2
import numpy as np
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings
from backend.app.core.operational_metrics import record_operational_event
from backend.app.integrations.privacy_vision import get_configured_privacy_vision_adapter
from backend.app.models.event import EventOccurrence, SafetyEvent
from backend.app.models.user import User
from backend.app.schemas.analysis import ModelDetection as SnapshotDetection
from backend.app.schemas.analysis import PersonDetection as SnapshotPersonDetection
from backend.app.schemas.event import (
    DecisionContextInput,
    EventBatchCreate,
    EventCreate,
    EventHumanReviewContext,
    EventUpdate,
    StoredDecisionContext,
    StoredEventRuleContext,
    StoredEventSceneContext,
    StoredEventSystemDecision,
)
from vision.api import ModelDetection, PrivacyRedactionResult, SnapshotPerson


class EventPersistenceError(RuntimeError):
    pass


class EventPrivacyError(RuntimeError):
    pass


def _privacy_redaction_outcome(redaction: PrivacyRedactionResult) -> str:
    if redaction["detected_face_count"] and redaction["fallback_person_count"]:
        return "face_and_person_fallback"
    if redaction["detected_face_count"]:
        return "face"
    return "person_fallback"


SnapshotRedactor = Callable[[np.ndarray, list[SnapshotPerson]], PrivacyRedactionResult]
SnapshotAnnotator = Callable[[np.ndarray, list[SnapshotPerson], list[ModelDetection]], np.ndarray]


class EventConflictError(RuntimeError):
    pass


class EventService:
    def __init__(
        self,
        db: Session,
        *,
        snapshot_redactor: SnapshotRedactor | None = None,
        snapshot_annotator: SnapshotAnnotator | None = None,
        snapshot_dir: Path | None = None,
        settings: Settings | None = None,
    ):
        self.db = db
        self._settings = settings or get_settings()
        self._snapshot_redactor = snapshot_redactor or self._default_snapshot_redactor
        self._snapshot_annotator = snapshot_annotator or self._default_snapshot_annotator
        self._snapshot_dir = snapshot_dir or Path(__file__).resolve().parents[3] / "data" / "snapshots"

    def create_event(self, event_in: EventCreate, *, actor: User | None = None) -> SafetyEvent:
        occurrence_ids = [str(value) for value in event_in.occurrence_ids]
        person_event = self._event_for_track(event_in)
        if person_event is not None:
            return self._merge_person_event(person_event, event_in, occurrence_ids, actor=actor)
        existing = self._events_for_occurrences(occurrence_ids)
        if existing:
            if len(existing) == 1 and self._matches_retry(existing[0], event_in, occurrence_ids):
                existing[0]._was_created = False
                existing[0]._became_acknowledged = False
                return existing[0]
            raise EventConflictError("One or more occurrences already belong to another event")
        reviewed = event_in.status in {"acknowledged", "false_alarm"}
        now = datetime.now(UTC)
        acknowledged_by = actor.full_name if actor else event_in.acknowledged_by
        decision_context = self._build_decision_context(
            event_in.decision_context,
            camera_id=event_in.camera_id,
            zone_id=event_in.zone_id,
            severity=event_in.severity,
            status=event_in.status,
            acknowledged_by=acknowledged_by,
            actor=actor,
            reviewed_at=now,
        )
        snapshot_path = None
        if event_in.snapshot_data:
            snapshot_path = self._save_snapshot(
                event_in.snapshot_data,
                event_in.snapshot_people,
                event_in.snapshot_detections,
            )
        db_event = SafetyEvent(
            zone_id=event_in.zone_id,
            camera_id=event_in.camera_id,
            event_type=event_in.event_type,
            severity=event_in.severity,
            snapshot_path=snapshot_path,
            privacy_blurred=snapshot_path is not None,
            details=event_in.details,
            decision_context=decision_context,
            status=event_in.status,
            acknowledged_by=acknowledged_by,
            acknowledged_at=now if reviewed else None,
            timestamp=now,
            audit_retention_until=now + timedelta(days=self._settings.audit_retention_days),
            snapshot_retention_until=(
                now + timedelta(days=self._settings.snapshot_retention_days) if snapshot_path else None
            ),
            monitoring_session_id=(str(event_in.monitoring_session_id) if event_in.monitoring_session_id else None),
            track_id=event_in.track_id,
        )
        self.db.add(db_event)
        for occurrence_id in occurrence_ids:
            db_event.occurrences.append(EventOccurrence(occurrence_id=occurrence_id))
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            if event_in.snapshot_data and snapshot_path:
                self._snapshot_file(snapshot_path).unlink(missing_ok=True)
            existing = self._events_for_occurrences(occurrence_ids)
            if len(existing) == 1 and self._matches_retry(existing[0], event_in, occurrence_ids):
                existing[0]._was_created = False
                existing[0]._became_acknowledged = False
                return existing[0]
            raise EventConflictError("One or more occurrences already belong to another event") from exc
        except Exception as exc:
            self.db.rollback()
            if event_in.snapshot_data and snapshot_path:
                self._snapshot_file(snapshot_path).unlink(missing_ok=True)
            raise EventPersistenceError("Could not save the event to the database") from exc
        db_event._was_created = True
        db_event._became_acknowledged = event_in.status == "acknowledged"
        return db_event

    def _event_for_track(self, event_in: EventCreate) -> SafetyEvent | None:
        if event_in.monitoring_session_id is None or event_in.track_id is None:
            return None
        return (
            self.db.query(SafetyEvent)
            .filter(
                SafetyEvent.monitoring_session_id == str(event_in.monitoring_session_id),
                SafetyEvent.track_id == event_in.track_id,
            )
            .first()
        )

    def _merge_person_event(
        self,
        event: SafetyEvent,
        event_in: EventCreate,
        occurrence_ids: list[str],
        *,
        actor: User | None = None,
    ) -> SafetyEvent:
        conflicts = [item for item in self._events_for_occurrences(occurrence_ids) if item.id != event.id]
        if conflicts:
            raise EventConflictError("One or more occurrences already belong to another event")
        existing_ids = set(event.occurrence_ids)
        for occurrence_id in occurrence_ids:
            if occurrence_id not in existing_ids:
                event.occurrences.append(EventOccurrence(occurrence_id=occurrence_id))
        existing_details = event.details or {}
        incoming_details = event_in.details or {}
        violations = sorted(set(existing_details.get("violations", [])) | set(incoming_details.get("violations", [])))
        event.details = {**existing_details, **incoming_details, "violations": violations}
        was_acknowledged = event.status == "acknowledged"
        event.status = event_in.status
        now = datetime.now(UTC)
        acknowledged_by = actor.full_name if actor else event_in.acknowledged_by
        had_decision_context = event.decision_context is not None
        if not had_decision_context:
            event.decision_context = self._build_decision_context(
                event_in.decision_context,
                camera_id=event_in.camera_id,
                zone_id=event_in.zone_id,
                severity=event_in.severity,
                status=event_in.status,
                acknowledged_by=acknowledged_by,
                actor=actor,
                reviewed_at=now,
            )
            if event.decision_context is not None:
                event.audit_retention_until = now + timedelta(days=self._settings.audit_retention_days)
        if not had_decision_context:
            event.acknowledged_by = acknowledged_by or event.acknowledged_by
        if event_in.status in {"acknowledged", "false_alarm"}:
            event.acknowledged_at = now
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise EventConflictError("One or more occurrences already belong to another event") from exc
        except Exception as exc:
            self.db.rollback()
            raise EventPersistenceError("Could not update the person's event") from exc
        event._was_created = False
        event._became_acknowledged = event_in.status == "acknowledged" and not was_acknowledged
        return event

    def create_batch(
        self,
        batch_in: EventBatchCreate,
        *,
        actor: User | None = None,
    ) -> tuple[str, str | None, list[SafetyEvent]]:
        occurrence_ids = [str(value) for item in batch_in.events for value in item.occurrence_ids]
        existing = self._events_for_occurrences(occurrence_ids)
        retried = self._matching_batch_retry(existing, batch_in)
        if retried is not None:
            for event in retried[2]:
                event._was_created = False
                event._became_acknowledged = False
            return retried
        if existing:
            raise EventConflictError("One or more occurrences already belong to another event")

        batch_id = self._batch_id(occurrence_ids)
        now = datetime.now(UTC)
        acknowledged_by = actor.full_name if actor else batch_in.acknowledged_by
        decision_contexts = [
            self._build_decision_context(
                item.decision_context,
                camera_id=batch_in.camera_id,
                zone_id=item.zone_id,
                severity=item.severity,
                status=batch_in.status,
                acknowledged_by=acknowledged_by,
                actor=actor,
                reviewed_at=now,
            )
            for item in batch_in.events
        ]
        snapshot_path = None
        if batch_in.snapshot_data:
            snapshot_path = self._save_snapshot(
                batch_in.snapshot_data,
                batch_in.snapshot_people,
                batch_in.snapshot_detections,
            )
        events: list[SafetyEvent] = []
        for item, decision_context in zip(batch_in.events, decision_contexts, strict=True):
            event = SafetyEvent(
                zone_id=item.zone_id,
                camera_id=batch_in.camera_id,
                event_type=item.event_type,
                severity=item.severity,
                snapshot_path=snapshot_path,
                privacy_blurred=snapshot_path is not None,
                details=item.details,
                decision_context=decision_context,
                status=batch_in.status,
                acknowledged_by=acknowledged_by,
                acknowledged_at=now,
                timestamp=now,
                audit_retention_until=now + timedelta(days=self._settings.audit_retention_days),
                snapshot_retention_until=(
                    now + timedelta(days=self._settings.snapshot_retention_days) if snapshot_path else None
                ),
                monitoring_session_id=str(batch_in.monitoring_session_id),
                batch_id=batch_id,
            )
            event.occurrences = [EventOccurrence(occurrence_id=str(value)) for value in item.occurrence_ids]
            event.batch_id = batch_id
            self.db.add(event)
            events.append(event)
        try:
            self.db.commit()
            for event in events:
                self.db.refresh(event)
        except IntegrityError as exc:
            self.db.rollback()
            if snapshot_path:
                self._snapshot_file(snapshot_path).unlink(missing_ok=True)
            existing = self._events_for_occurrences(occurrence_ids)
            retried = self._matching_batch_retry(existing, batch_in)
            if retried is not None:
                for event in retried[2]:
                    event._was_created = False
                    event._became_acknowledged = False
                return retried
            raise EventConflictError("One or more occurrences already belong to another event") from exc
        except Exception as exc:
            self.db.rollback()
            if snapshot_path:
                self._snapshot_file(snapshot_path).unlink(missing_ok=True)
            raise EventPersistenceError("Could not save the event batch to the database") from exc
        for event in events:
            event._was_created = True
            event._became_acknowledged = batch_in.status == "acknowledged"
        return batch_id, snapshot_path, events

    def _build_decision_context(
        self,
        context: DecisionContextInput | None,
        *,
        camera_id: str,
        zone_id: str,
        severity: str,
        status: str,
        acknowledged_by: str | None,
        actor: User | None,
        reviewed_at: datetime,
    ) -> dict | None:
        if context is None:
            return None
        if status not in {"acknowledged", "false_alarm"}:
            raise ValueError("decision_context requires a completed human review")
        if severity not in {"low", "medium", "high", "critical"}:
            raise ValueError("decision_context requires a supported severity")
        actor_name = acknowledged_by or "Unknown reviewer"
        stored = StoredDecisionContext(
            rule=StoredEventRuleContext(
                **context.rule.model_dump(),
                violation_frame_count=self._decision_frame_count(context),
            ),
            scene=StoredEventSceneContext(
                **context.scene.model_dump(),
                camera_id=camera_id,
                zone_id=zone_id,
            ),
            system_decision=StoredEventSystemDecision(
                **context.system_decision.model_dump(),
                severity=severity,
            ),
            human_review=EventHumanReviewContext(
                outcome="actual_violation" if status == "acknowledged" else "false_alarm",
                actor_user_id=actor.id if actor else None,
                actor_name=actor_name,
                actor_role=actor.role if actor else None,
                reviewed_at=reviewed_at,
            ),
        )
        return stored.model_dump(mode="json")

    def _decision_frame_count(self, context: DecisionContextInput) -> int:
        rule_keys = context.rule.triggered_rule_keys
        if any(rule.startswith("zone_intrusion") for rule in rule_keys):
            return self._settings.zone_alert_confirm_frames
        if rule_keys and all(rule.startswith("missing_ppe:") for rule in rule_keys):
            return self._settings.ppe_alert_confirm_frames
        if "restricted_area_person" in rule_keys:
            return 1
        return self._settings.violation_frame

    @staticmethod
    def _matching_batch_retry(
        events: list[SafetyEvent], batch_in: EventBatchCreate
    ) -> tuple[str, str | None, list[SafetyEvent]] | None:
        if len(events) != len(batch_in.events) or not events:
            return None
        by_zone = {event.zone_id.casefold(): event for event in events}
        if len(by_zone) != len(events):
            return None
        for item in batch_in.events:
            event = by_zone.get(item.zone_id.casefold())
            if event is None or (
                set(event.occurrence_ids) != {str(value) for value in item.occurrence_ids}
                or event.camera_id != batch_in.camera_id
                or event.event_type != item.event_type
                or event.severity != item.severity
                or event.status != batch_in.status
                or event.monitoring_session_id != str(batch_in.monitoring_session_id)
                or not EventService._matches_decision_context(event.decision_context, item.decision_context)
            ):
                return None
        ordered = [by_zone[item.zone_id.casefold()] for item in batch_in.events]
        batch_id = EventService._batch_id([str(value) for item in batch_in.events for value in item.occurrence_ids])
        for event in ordered:
            event.batch_id = batch_id
        return batch_id, ordered[0].snapshot_path, ordered

    @staticmethod
    def _batch_id(occurrence_ids: list[str]) -> str:
        stable_key = "p047:event-batch:" + ",".join(sorted(occurrence_ids))
        return str(uuid.uuid5(uuid.NAMESPACE_URL, stable_key))

    def _events_for_occurrences(self, occurrence_ids: list[str]) -> list[SafetyEvent]:
        if not occurrence_ids:
            return []
        try:
            return (
                self.db.query(SafetyEvent)
                .filter(SafetyEvent.occurrences.any(EventOccurrence.occurrence_id.in_(occurrence_ids)))
                .all()
            )
        except SQLAlchemyError as exc:
            raise EventPersistenceError("Could not query event occurrences from the database") from exc

    def has_persisted_occurrences(self, occurrence_ids: list[str]) -> bool:
        return bool(self._events_for_occurrences(occurrence_ids))

    @staticmethod
    def _matches_retry(event: SafetyEvent, event_in: EventCreate, occurrence_ids: list[str]) -> bool:
        return (
            set(event.occurrence_ids) == set(occurrence_ids)
            and event.zone_id == event_in.zone_id
            and event.camera_id == event_in.camera_id
            and event.event_type == event_in.event_type
            and event.severity == event_in.severity
            and event.status == event_in.status
            and event.monitoring_session_id
            == (str(event_in.monitoring_session_id) if event_in.monitoring_session_id else None)
            and event.track_id == event_in.track_id
            and EventService._matches_decision_context(event.decision_context, event_in.decision_context)
        )

    @staticmethod
    def _matches_decision_context(stored: dict | None, submitted: DecisionContextInput | None) -> bool:
        if stored is None or submitted is None:
            return stored is None and submitted is None
        submitted_data = submitted.model_dump(mode="json")
        stored_client_fields = {
            "rule": {
                key: stored["rule"].get(key) for key in ("triggered_rule_keys", "ppe_profile", "ppe_requirements")
            },
            "scene": {
                key: stored["scene"].get(key)
                for key in (
                    "frame_id",
                    "video_timestamp_seconds",
                    "machine_state",
                    "zone_name",
                    "zone_revision",
                    "zone_points",
                    "people",
                    "detections",
                )
            },
            "system_decision": {key: stored["system_decision"].get(key) for key in ("result", "reason_codes")},
        }
        return stored_client_fields == submitted_data

    def _save_snapshot(
        self,
        snapshot_data: str,
        snapshot_people: list[SnapshotPersonDetection],
        snapshot_detections: list[SnapshotDetection],
    ) -> str:
        encoded = snapshot_data.split(",", 1)[-1]
        try:
            image_bytes = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("snapshot_data must be a valid base64 image") from exc

        frame = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("snapshot_data could not be decoded as an image")

        try:
            people = [
                {
                    "bbox": person.bbox,
                    "confidence": person.confidence,
                    "inside_zone": person.inside_zone,
                }
                for person in snapshot_people
            ]
            redaction = self._snapshot_redactor(frame, people)
            record_operational_event(
                "privacy_redaction_completed",
                outcome=_privacy_redaction_outcome(redaction),
                error_kind="yunet_inference_failed" if redaction["face_detector_failed"] else None,
            )
            annotated = self._snapshot_annotator(
                redaction["image"],
                people,
                [detection.model_dump() for detection in snapshot_detections],
            )
            success, redacted_bytes = cv2.imencode(".jpg", annotated)
        except Exception as exc:
            raise EventPrivacyError("Privacy processing failed; the snapshot was not saved") from exc
        if not success:
            raise EventPrivacyError("Privacy processing could not encode the redacted snapshot")

        self._snapshot_dir.mkdir(parents=True, exist_ok=True)
        filename = f"event-{uuid.uuid4().hex}.jpg"
        snapshot_file = self._snapshot_dir / filename
        try:
            snapshot_file.write_bytes(redacted_bytes.tobytes())
        except OSError as exc:
            snapshot_file.unlink(missing_ok=True)
            raise EventPersistenceError("Could not persist the redacted snapshot") from exc
        return f"/snapshots/{filename}"

    @staticmethod
    def _default_snapshot_redactor(
        frame: np.ndarray,
        people: list[SnapshotPerson],
    ) -> PrivacyRedactionResult:
        return get_configured_privacy_vision_adapter().redact_snapshot(frame, people)

    @staticmethod
    def _default_snapshot_annotator(
        frame: np.ndarray,
        people: list[SnapshotPerson],
        detections: list[ModelDetection],
    ) -> np.ndarray:
        return get_configured_privacy_vision_adapter().annotate_snapshot(frame, people, detections)

    def _snapshot_file(self, snapshot_path: str) -> Path:
        return self._snapshot_dir / Path(snapshot_path).name

    def get_event(self, event_id: int) -> SafetyEvent | None:
        return self.db.query(SafetyEvent).filter(SafetyEvent.id == event_id).first()

    def get_events(
        self,
        skip: int = 0,
        limit: int = 100,
        zone_id: str | None = None,
        status: str | None = None,
        event_type: str | None = None,
    ) -> list[SafetyEvent]:
        query = self.db.query(SafetyEvent)
        if zone_id:
            query = query.filter(SafetyEvent.zone_id == zone_id)
        if status:
            query = query.filter(SafetyEvent.status == status)
        if event_type:
            query = query.filter(SafetyEvent.event_type == event_type)
        return query.order_by(SafetyEvent.timestamp.desc()).offset(skip).limit(limit).all()

    def update_event(self, event_id: int, event_in: EventUpdate) -> SafetyEvent | None:
        db_event = self.get_event(event_id)
        if not db_event:
            return None

        if event_in.status is not None:
            if (
                event_in.status in {"acknowledged", "false_alarm"}
                and db_event.snapshot_path
                and not db_event.privacy_blurred
            ):
                raise EventPrivacyError("An event with an unredacted snapshot cannot be reviewed")
            db_event.status = event_in.status
            if event_in.status in ["acknowledged", "false_alarm"]:
                db_event.acknowledged_at = datetime.now(UTC)
        if event_in.acknowledged_by is not None:
            db_event.acknowledged_by = event_in.acknowledged_by

        self.db.commit()
        return db_event
