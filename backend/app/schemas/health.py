from typing import Literal

from pydantic import BaseModel


class DependencyReadiness(BaseModel):
    ready: bool
    reason: Literal["connection_failed", "not_configured", "postgresql_required", "s3_required"] | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    ready: bool
    env: str
    service: str
    database: str
    database_fallback_active: bool
    dependencies: dict[str, DependencyReadiness]
    runtime_files: dict[str, bool]
