from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    app_name: str = "PPE & Danger Zone Safety Monitoring System API"
    app_env: Literal["development", "production", "test"] = "development"
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_host: str = "0.0.0.0"
    app_debug: bool = True
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    api_v1_prefix: str = "/api/v1"

    # Lightweight operational metrics persisted as rotated JSONL files.
    operational_metrics_log_path: str = "data/operational-metrics.jsonl"
    operational_metrics_log_max_bytes: int = Field(default=5 * 1024 * 1024, gt=0)
    operational_metrics_log_backup_count: int = Field(default=6, ge=1, le=30)
    operational_metrics_max_scan_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    operational_metrics_max_scan_lines: int = Field(default=100_000, gt=0)

    # CORS
    cors_origins: list[str] | str = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json

                return json.loads(v)
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # LLM Settings (for Safety Agent & Escalation reasoning)
    openai_api_key: str = ""
    model_name: str = "gpt-4o-mini"
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)

    # Database Settings
    database_url: str = "postgresql://postgres:postgres@localhost:5432/ppe_safety_db"

    # Video & Model paths
    demo_video_dir: str = "data/demo"
    model_dir: str = "models"
    person_model_path: str = "models/yolo11n.pt"
    ppe_model_path: str = "models/ppe_yolov8n.pt"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    # Violate frame least confidence threshold for PPE & Danger Zone detection


@lru_cache
def get_settings() -> Settings:
    return Settings()
