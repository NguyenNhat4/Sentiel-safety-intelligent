from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from backend.app.models.event import SafetyEvent
from backend.app.schemas.event import EventCreate, EventUpdate


class EventService:
    def __init__(self, db: Session):
        self.db = db

    def create_event(self, event_in: EventCreate) -> SafetyEvent:
        db_event = SafetyEvent(
            zone_id=event_in.zone_id,
            camera_id=event_in.camera_id,
            event_type=event_in.event_type,
            severity=event_in.severity,
            snapshot_path=event_in.snapshot_path,
            privacy_blurred=event_in.privacy_blurred,
            details=event_in.details,
            status="unacknowledged",
            timestamp=datetime.now(timezone.utc),
        )
        self.db.add(db_event)
        self.db.commit()
        self.db.refresh(db_event)
        return db_event

    def get_event(self, event_id: int) -> Optional[SafetyEvent]:
        return self.db.query(SafetyEvent).filter(SafetyEvent.id == event_id).first()

    def get_events(
        self,
        skip: int = 0,
        limit: int = 100,
        zone_id: Optional[str] = None,
        status: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> List[SafetyEvent]:
        query = self.db.query(SafetyEvent)
        if zone_id:
            query = query.filter(SafetyEvent.zone_id == zone_id)
        if status:
            query = query.filter(SafetyEvent.status == status)
        if event_type:
            query = query.filter(SafetyEvent.event_type == event_type)
        return query.order_by(SafetyEvent.timestamp.desc()).offset(skip).limit(limit).all()

    def update_event(self, event_id: int, event_in: EventUpdate) -> Optional[SafetyEvent]:
        db_event = self.get_event(event_id)
        if not db_event:
            return None

        if event_in.status is not None:
            db_event.status = event_in.status
            if event_in.status in ["acknowledged", "false_alarm"]:
                db_event.acknowledged_at = datetime.now(timezone.utc)
        if event_in.acknowledged_by is not None:
            db_event.acknowledged_by = event_in.acknowledged_by

        self.db.commit()
        self.db.refresh(db_event)
        return db_event
