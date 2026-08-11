from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.schemas.event import EventCreate, EventResponse, EventUpdate
from backend.app.services.event_service import (
    EventConflictError,
    EventPersistenceError,
    EventPrivacyError,
    EventService,
)

router = APIRouter(prefix="/events", tags=["Safety Events"])


@router.get("", response_model=list[EventResponse])
async def list_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    zone_id: str | None = None,
    status: str | None = None,
    event_type: str | None = None,
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
    try:
        return service.create_event(event_in)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except EventPrivacyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except EventConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except EventPersistenceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


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
    try:
        updated = service.update_event(event_id, event_in)
    except EventPrivacyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=404, detail="Event not found")
    return updated
