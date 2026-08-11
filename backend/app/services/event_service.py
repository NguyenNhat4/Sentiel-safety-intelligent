import base64
import binascii
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.integrations.ppe_vision import (
    ModelDetection,
    PrivacyRedactionResult,
    SnapshotPerson,
    get_ppe_vision_adapter,
)
from backend.app.models.event import EventOccurrence, SafetyEvent
from backend.app.schemas.analysis import ModelDetection as SnapshotDetection
from backend.app.schemas.analysis import PersonDetection as SnapshotPersonDetection
from backend.app.schemas.event import EventCreate, EventUpdate


class EventPersistenceError(RuntimeError):
    pass


class EventPrivacyError(RuntimeError):
    pass


SnapshotRedactor = Callable[[np.ndarray], PrivacyRedactionResult]
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
            self.db.refresh(db_event)
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

    def _events_for_occurrences(self, occurrence_ids: list[str]) -> list[SafetyEvent]:
        if not occurrence_ids:
            return []
        return (
            self.db.query(SafetyEvent)
            .join(EventOccurrence)
            .filter(EventOccurrence.occurrence_id.in_(occurrence_ids))
            .distinct()
            .all()
        )

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
            redaction = self._snapshot_redactor(frame)
            annotated = self._snapshot_annotator(
                redaction["image"],
                [
                    {
                        "bbox": person.bbox,
                        "confidence": person.confidence,
                        "inside_zone": person.inside_zone,
                    }
                    for person in snapshot_people
                ],
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
    def _default_snapshot_redactor(frame: np.ndarray) -> PrivacyRedactionResult:
        from backend.app.core.config import get_settings

        return get_ppe_vision_adapter(get_settings().ppe_model_path).redact_snapshot(frame)

    @staticmethod
    def _default_snapshot_annotator(
        frame: np.ndarray,
        people: list[SnapshotPerson],
        detections: list[ModelDetection],
    ) -> np.ndarray:
        from backend.app.core.config import get_settings

        return get_ppe_vision_adapter(get_settings().ppe_model_path).annotate_snapshot(frame, people, detections)

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
        self.db.refresh(db_event)
        return db_event
