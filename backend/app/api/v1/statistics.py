from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.schemas.statistics import StatisticsSummaryResponse
from backend.app.services.statistics_service import StatisticsService

router = APIRouter(prefix="/statistics", tags=["Statistics & Compliance"])


@router.get("/summary", response_model=StatisticsSummaryResponse)
async def get_summary_statistics(db: Session = Depends(get_db)):
    """Get overall safety compliance & violation statistics."""
    service = StatisticsService(db)
    return service.get_summary()
