import base64
import binascii
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.models.event import SafetyEvent
from backend.app.schemas.event import EventCreate, EventUpdate


class EventService:
    def __init__(self, db: Session):
        self.db = db

    def create_event(self, event_in: EventCreate) -> SafetyEvent:
        reviewed = event_in.status in {"acknowledged", "false_alarm"}
        snapshot_path = event_in.snapshot_path
        if event_in.snapshot_data:
            snapshot_path = self._save_snapshot(event_in.snapshot_data)
        db_event = SafetyEvent(
            zone_id=event_in.zone_id,
            camera_id=event_in.camera_id,
            event_type=event_in.event_type,
            severity=event_in.severity,
            snapshot_path=snapshot_path,
            privacy_blurred=event_in.privacy_blurred,
            details=event_in.details,
            status=event_in.status,
            acknowledged_by=event_in.acknowledged_by,
            acknowledged_at=datetime.now(UTC) if reviewed else None,
            timestamp=datetime.now(UTC),
        )
        self.db.add(db_event)
        self.db.commit()
        self.db.refresh(db_event)
        return db_event

    @staticmethod
    def _save_snapshot(snapshot_data: str) -> str:
        encoded = snapshot_data.split(",", 1)[-1]
        try:
            image_bytes = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("snapshot_data must be a valid base64 image") from exc

        snapshot_dir = Path(__file__).resolve().parents[3] / "data" / "snapshots"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        filename = f"event-{uuid.uuid4().hex}.jpg"
        (snapshot_dir / filename).write_bytes(image_bytes)
        return f"/snapshots/{filename}"

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
            db_event.status = event_in.status
            if event_in.status in ["acknowledged", "false_alarm"]:
                db_event.acknowledged_at = datetime.now(UTC)
        if event_in.acknowledged_by is not None:
            db_event.acknowledged_by = event_in.acknowledged_by

        self.db.commit()
        self.db.refresh(db_event)
        return db_event
