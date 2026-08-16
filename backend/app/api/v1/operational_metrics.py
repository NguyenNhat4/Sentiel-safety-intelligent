from typing import Annotated

from fastapi import APIRouter, Query

from backend.app.core.config import get_settings
from backend.app.schemas.operational_metrics import OperationalMetricsSummaryResponse
from backend.app.services.operational_metrics_service import OperationalMetricsService

router = APIRouter(prefix="/operational-metrics", tags=["Operational Metrics"])


@router.get("", response_model=OperationalMetricsSummaryResponse)
async def get_operational_metrics(
    window_minutes: Annotated[int, Query(ge=1, le=1440)] = 60,
) -> OperationalMetricsSummaryResponse:
    """Return bounded aggregates from privacy-safe operational JSONL events."""
    return OperationalMetricsService(get_settings()).summary(window_minutes)
