from datetime import datetime

from pydantic import BaseModel


class LatencySummary(BaseModel):
    count: int
    min_ms: float | None = None
    mean_ms: float | None = None
    p50_ms: float | None = None
    p95_ms: float | None = None
    max_ms: float | None = None


class RequestMetricsGroup(BaseModel):
    method: str
    route: str
    status_class: str
    count: int
    latency: LatencySummary


class WebSocketMetricsGroup(BaseModel):
    route: str
    opened: int
    closed: int


class OperationalMetricsSummaryResponse(BaseModel):
    generated_at: datetime
    window_start: datetime
    window_end: datetime
    records_scanned: int
    skipped_malformed_records: int
    partial: bool
    partial_reasons: list[str]
    requests: list[RequestMetricsGroup]
    websocket_connections: list[WebSocketMetricsGroup]
    inference_outcomes: dict[str, int]
    errors_by_kind: dict[str, int]
