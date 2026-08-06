from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.schemas.ppe_requirement import (
    PpeRequirementResponse,
    PpeRequirementUpdate,
)
from backend.app.services.ppe_requirement_service import (
    PpeRequirementPersistenceError,
    PpeRequirementService,
)

router = APIRouter(prefix="/ppe-requirements", tags=["PPE Requirements"])

ResourceId = Annotated[
    str,
    Path(min_length=1, max_length=50, pattern=r"^[A-Za-z0-9_.:-]+$"),
]


@router.get("/{camera_id}/{zone_id}", response_model=PpeRequirementResponse)
async def get_ppe_requirement(
    camera_id: ResourceId,
    zone_id: ResourceId,
    db: Session = Depends(get_db),
) -> PpeRequirementResponse:
    return PpeRequirementService(db).get(camera_id, zone_id)


@router.put("/{camera_id}/{zone_id}", response_model=PpeRequirementResponse)
async def save_ppe_requirement(
    requirement: PpeRequirementUpdate,
    camera_id: ResourceId,
    zone_id: ResourceId,
    db: Session = Depends(get_db),
) -> PpeRequirementResponse:
    try:
        return PpeRequirementService(db).save(camera_id, zone_id, requirement)
    except PpeRequirementPersistenceError as exc:
        raise HTTPException(status_code=503, detail="Could not save PPE requirements") from exc
