from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.api.dependencies import require_roles
from backend.app.core.database import get_db
from backend.app.models.event import SafetyEvent
from backend.app.models.user import User, UserRole
from backend.app.schemas.event import (
    EventBatchCreate,
    EventBatchResponse,
    EventCreate,
    EventDetailResponse,
    EventResponse,
    EventUpdate,
)
from backend.app.services.alert_notification_service import alert_notification_service
from backend.app.services.event_service import (
    EventConflictError,
    EventPersistenceError,
    EventPrivacyError,
    EventService,
)
from backend.app.services.llm_service import SafetyAgentService

router = APIRouter(prefix="/events", tags=["Safety Events"])
batch_router = APIRouter(prefix="/event-batches", tags=["Safety Events"])


@batch_router.post("", response_model=EventBatchResponse, status_code=201)
async def create_event_batch(
    batch_in: EventBatchCreate,
    actor: User = Depends(require_roles(UserRole.SAFETY_MANAGER, UserRole.SYSTEM_ADMIN)),
    db: Session = Depends(get_db),
):
    from backend.app.services.frame_inference_service import frame_inference_service

    service = EventService(db)
    all_occurrence_ids = [str(value) for item in batch_in.events for value in item.occurrence_ids]
    try:
        if not service.has_persisted_occurrences(all_occurrence_ids):
            for item in batch_in.events:
                if not frame_inference_service.occurrences_belong_to_zone(
                    str(batch_in.monitoring_session_id),
                    item.zone_id,
                    [str(value) for value in item.occurrence_ids],
                ):
                    raise HTTPException(
                        status_code=409,
                        detail="Occurrence does not belong to the requested session and zone",
                    )
        batch_id, snapshot_path, events = service.create_batch(batch_in, actor=actor)
        if batch_in.status == "acknowledged":
            alert_notification_service.queue_confirmed_events(
                db, [event for event in events if getattr(event, "_became_acknowledged", False)]
            )
        return {"batch_id": batch_id, "snapshot_path": snapshot_path, "events": events}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except EventPrivacyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except EventConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except EventPersistenceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("", response_model=list[EventResponse])
async def list_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    camera_id: str | None = None,
    zone_id: str | None = None,
    status: str | None = None,
    event_type: str | None = None,
    actor: User = Depends(require_roles(UserRole.SYSTEM_ADMIN, UserRole.SAFETY_MANAGER, UserRole.AREA_MANAGER)),
    db: Session = Depends(get_db),
):
    """Retrieve safety violation events with filtering."""
    is_area_manager = actor.role == UserRole.AREA_MANAGER.value
    managed_camera_ids = actor.managed_camera_ids or [] if is_area_manager else []
    if is_area_manager and not managed_camera_ids and not actor.managed_area_id:
        raise HTTPException(status_code=403, detail="Area manager has no assigned area")
    service = EventService(db)
    return service.get_events(
        skip=skip,
        limit=limit,
        camera_id=camera_id,
        camera_ids=managed_camera_ids or None,
        zone_id=actor.managed_area_id if is_area_manager and not managed_camera_ids else zone_id,
        status=status,
        event_type=event_type,
    )


@router.post("", response_model=EventResponse, status_code=201)
async def create_event(
    event_in: EventCreate,
    actor: User = Depends(require_roles(UserRole.SAFETY_MANAGER, UserRole.SYSTEM_ADMIN)),
    db: Session = Depends(get_db),
):
    """Record a new safety violation event."""
    from backend.app.services.frame_inference_service import frame_inference_service

    service = EventService(db)
    try:
        occurrence_ids = [str(value) for value in event_in.occurrence_ids]
        if (
            event_in.camera_id in {"cam_1", "cam_2", "cam_3", "cam_4"}
            and occurrence_ids
            and not service.has_persisted_occurrences(occurrence_ids)
            and (
                event_in.monitoring_session_id is None
                or event_in.track_id is None
                or not frame_inference_service.occurrences_belong_to_track(
                    str(event_in.monitoring_session_id), event_in.track_id, occurrence_ids
                )
            )
        ):
            raise HTTPException(status_code=409, detail="Occurrence does not belong to the requested session and track")
        event = service.create_event(event_in, actor=actor)
        if event_in.status == "acknowledged" and getattr(event, "_became_acknowledged", False):
            alert_notification_service.queue_confirmed_events(db, [event])
        return event
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except EventPrivacyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except EventConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except EventPersistenceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/{event_id}", response_model=EventDetailResponse)
def get_event(
    event_id: int,
    actor: User = Depends(require_roles(UserRole.SYSTEM_ADMIN, UserRole.SAFETY_MANAGER, UserRole.AREA_MANAGER)),
    db: Session = Depends(get_db),
):
    """Get details of a specific event."""
    service = EventService(db)
    event = service.get_event(event_id)
    if event and actor.role == UserRole.AREA_MANAGER.value and not _area_manager_can_access_event(actor, event):
        raise HTTPException(status_code=404, detail="Event not found")
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    summary = SafetyAgentService().generate_incident_summary(
        decision_context=event.decision_context,
        event_type=event.event_type,
        zone_id=event.zone_id,
    )
    return EventDetailResponse(
        **EventResponse.model_validate(event).model_dump(),
        summary=summary,
    )


@router.patch("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    event_in: EventUpdate,
    actor: User = Depends(require_roles(UserRole.SAFETY_MANAGER, UserRole.SYSTEM_ADMIN, UserRole.AREA_MANAGER)),
    db: Session = Depends(get_db),
):
    """Acknowledge or update status of an event."""
    service = EventService(db)
    existing = service.get_event(event_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Event not found")
    if actor.role == UserRole.AREA_MANAGER.value:
        if not _area_manager_can_access_event(actor, existing):
            raise HTTPException(status_code=404, detail="Event not found")
        if event_in.status not in {"resolved", "false_alarm"}:
            raise HTTPException(
                status_code=403, detail="Area managers may only resolve or reject their own area events"
            )
        event_in.acknowledged_by = actor.full_name
    was_acknowledged = existing.status == "acknowledged"
    try:
        updated = service.update_event(event_id, event_in)
    except EventPrivacyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except EventConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=404, detail="Event not found")
    if event_in.status == "acknowledged" and not was_acknowledged:
        alert_notification_service.queue_confirmed_events(db, [updated])
    return updated


def _area_manager_can_access_event(actor: User, event: SafetyEvent) -> bool:
    managed_camera_ids = actor.managed_camera_ids or []
    if managed_camera_ids:
        return event.camera_id in managed_camera_ids
    return bool(actor.managed_area_id and event.zone_id == actor.managed_area_id)
