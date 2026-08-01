from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.schemas.event import EventCreate, EventUpdate, EventResponse
from backend.app.services.event_service import EventService

router = APIRouter(prefix="/events", tags=["Safety Events"])


@router.get("", response_model=List[EventResponse])
async def list_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    zone_id: Optional[str] = None,
    status: Optional[str] = None,
    event_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Retrieve safety violation events with filtering."""
    service = EventService(db)
    return service.get_events(
        skip=skip,
        limit=limit,
        zone_id=zone_id,
        status=status,
        event_type=event_type,
    )


@router.post("", response_model=EventResponse, status_code=201)
async def create_event(
    event_in: EventCreate,
    db: Session = Depends(get_db),
):
    """Record a new safety violation event."""
    service = EventService(db)
    return service.create_event(event_in)


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int,
    db: Session = Depends(get_db),
):
    """Get details of a specific event."""
    service = EventService(db)
    event = service.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.patch("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    event_in: EventUpdate,
    db: Session = Depends(get_db),
):
    """Acknowledge or update status of an event."""
    service = EventService(db)
    updated = service.update_event(event_id, event_in)
    if not updated:
        raise HTTPException(status_code=404, detail="Event not found")
    return updated
