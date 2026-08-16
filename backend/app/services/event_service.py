import base64
import binascii
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.operational_metrics import record_operational_event
from backend.app.integrations.privacy_vision import get_configured_privacy_vision_adapter
from backend.app.models.event import EventOccurrence, SafetyEvent
from backend.app.schemas.analysis import ModelDetection as SnapshotDetection
from backend.app.schemas.analysis import PersonDetection as SnapshotPersonDetection
from backend.app.schemas.event import EventBatchCreate, EventCreate, EventUpdate
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
    ):
        self.db = db
        self._snapshot_redactor = snapshot_redactor or self._default_snapshot_redactor
        self._snapshot_annotator = snapshot_annotator or self._default_snapshot_annotator
        self._snapshot_dir = snapshot_dir or Path(__file__).resolve().parents[3] / "data" / "snapshots"

    def create_event(self, event_in: EventCreate) -> SafetyEvent:
        occurrence_ids = [str(value) for value in event_in.occurrence_ids]
        existing = self._events_for_occurrences(occurrence_ids)
        if existing:
            if len(existing) == 1 and self._matches_retry(existing[0], event_in, occurrence_ids):
                return existing[0]
            raise EventConflictError("One or more occurrences already belong to another event")
        reviewed = event_in.status in {"acknowledged", "false_alarm"}
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
            status=event_in.status,
            acknowledged_by=event_in.acknowledged_by,
            acknowledged_at=datetime.now(UTC) if reviewed else None,
            timestamp=datetime.now(UTC),
            monitoring_session_id=(str(event_in.monitoring_session_id) if event_in.monitoring_session_id else None),
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
                return existing[0]
            raise EventConflictError("One or more occurrences already belong to another event") from exc
        except Exception as exc:
            self.db.rollback()
            if event_in.snapshot_data and snapshot_path:
                self._snapshot_file(snapshot_path).unlink(missing_ok=True)
            raise EventPersistenceError("Could not save the event to the database") from exc
        return db_event

    def create_batch(self, batch_in: EventBatchCreate) -> tuple[str, str | None, list[SafetyEvent]]:
        occurrence_ids = [str(value) for item in batch_in.events for value in item.occurrence_ids]
        existing = self._events_for_occurrences(occurrence_ids)
        retried = self._matching_batch_retry(existing, batch_in)
        if retried is not None:
            return retried
        if existing:
            raise EventConflictError("One or more occurrences already belong to another event")

        snapshot_path = None
        if batch_in.snapshot_data:
            snapshot_path = self._save_snapshot(
                batch_in.snapshot_data,
                batch_in.snapshot_people,
                batch_in.snapshot_detections,
            )
        batch_id = self._batch_id(occurrence_ids)
        now = datetime.now(UTC)
        events: list[SafetyEvent] = []
        for item in batch_in.events:
            event = SafetyEvent(
                zone_id=item.zone_id,
                camera_id=batch_in.camera_id,
                event_type=item.event_type,
                severity=item.severity,
                snapshot_path=snapshot_path,
                privacy_blurred=snapshot_path is not None,
                details=item.details,
                status=batch_in.status,
                acknowledged_by=batch_in.acknowledged_by,
                acknowledged_at=now,
                timestamp=now,
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
                return retried
            raise EventConflictError("One or more occurrences already belong to another event") from exc
        except Exception as exc:
            self.db.rollback()
            if snapshot_path:
                self._snapshot_file(snapshot_path).unlink(missing_ok=True)
            raise EventPersistenceError("Could not save the event batch to the database") from exc
        return batch_id, snapshot_path, events

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
        )

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
