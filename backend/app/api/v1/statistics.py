from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.api.dependencies import require_roles
from backend.app.core.database import get_db
from backend.app.models.user import User, UserRole
from backend.app.schemas.statistics import StatisticsSummaryResponse
from backend.app.services.statistics_service import StatisticsService

router = APIRouter(prefix="/statistics", tags=["Statistics & Compliance"])


@router.get("/summary", response_model=StatisticsSummaryResponse)
async def get_summary_statistics(
    actor: User = Depends(require_roles(UserRole.SYSTEM_ADMIN, UserRole.SAFETY_MANAGER, UserRole.AREA_MANAGER)),
    db: Session = Depends(get_db),
):
    """Get overall safety compliance & violation statistics."""
    if actor.role == UserRole.AREA_MANAGER.value and not actor.managed_area_id:
        raise HTTPException(status_code=403, detail="Area manager has no assigned area")
    service = StatisticsService(db)
    return service.get_summary(zone_id=actor.managed_area_id if actor.role == UserRole.AREA_MANAGER.value else None)
