from fastapi import APIRouter, Depends
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
    is_area_manager = actor.role == UserRole.AREA_MANAGER.value
    managed_camera_ids = actor.managed_camera_ids or [] if is_area_manager else []
    if is_area_manager and not managed_camera_ids and not actor.managed_area_id:
        return StatisticsSummaryResponse(
            total_events=0,
            unacknowledged_events=0,
            false_alarm_events=0,
            camera_stats=[],
            overall_compliance_rate=None,
            violations_by_type={},
            violations_by_severity={},
            zone_stats=[],
        )
    service = StatisticsService(db)
    return service.get_summary(
        zone_id=actor.managed_area_id if is_area_manager and not managed_camera_ids else None,
        camera_ids=managed_camera_ids or None,
    )
