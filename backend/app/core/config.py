from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    app_name: str = "PPE & Danger Zone Safety Monitoring System API"
    app_env: Literal["development", "production", "test"] = "development"
    app_port: int = Field(default=8000, ge=1, le=65535, validation_alias=AliasChoices("APP_PORT", "PORT"))
    app_host: str = "0.0.0.0"
    app_debug: bool = True
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    api_v1_prefix: str = "/api/v1"
    hls_token_secret: str = ""
    streamer_internal_origin: str = ""
    streamer_health_timeout_seconds: float = Field(default=3.0, ge=0.5, le=10.0)
    rtsp_inference_enabled: bool = False
    rtsp_reader_origin: str = ""
    rtsp_inference_max_fps: float = Field(default=2.0, gt=0.0, le=10.0)
    rtsp_mapping_poll_seconds: float = Field(default=5.0, ge=1.0, le=60.0)

    # Lightweight operational metrics persisted as rotated JSONL files.
    operational_metrics_log_path: str = "data/operational-metrics.jsonl"
    snapshot_dir: str = "data/snapshots"
    snapshot_storage_backend: Literal["filesystem", "s3"] = "filesystem"
    snapshot_storage_bucket: str = ""
    snapshot_storage_endpoint_url: str = ""
    snapshot_storage_region: str = "auto"
    snapshot_storage_access_key_id: str = ""
    snapshot_storage_secret_access_key: str = ""
    audit_retention_days: int = Field(default=365, ge=1, le=3650)
    snapshot_retention_days: int = Field(default=90, ge=1, le=3650)
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

    # Telegram alert delivery
    telegram_bot_token: str = ""
    telegram_request_timeout_seconds: float = Field(default=5.0, ge=1.0, le=30.0)

    # Database Settings
    database_url: str = "sqlite:///./data/safety_events.db"
    database_fallback_enabled: bool = True
    run_db_migrations_on_start: bool = True
    database_fallback_url: str = "sqlite:///./data/safety_events.db"
    database_connect_timeout_seconds: int = Field(default=5, ge=1, le=30)
    database_pool_pre_ping: bool = False
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_pool_max_overflow: int = Field(default=10, ge=0, le=100)
    database_pool_timeout_seconds: int = Field(default=10, ge=1, le=60)
    database_pool_recycle_seconds: int = Field(default=300, ge=30, le=3600)
    database_pool_use_lifo: bool = True

    # Video & Model paths
    demo_video_dir: str = "data/demo"
    model_dir: str = "models"
    ppe_model_path: str = "models/yolo11m_safety.pt"
    vision_provider: Literal["local", "remote"] = "local"
    vision_remote_url: str = ""
    vision_remote_api_key: SecretStr = SecretStr("")
    vision_remote_timeout_seconds: float = Field(default=5.0, ge=0.1, le=30.0)
    face_detector_model_path: str = "models/face_detection_yunet_2023mar.onnx"
    face_detector_score_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    face_redaction_margin_ratio: float = Field(default=0.2, ge=0.0, le=1.0)
    violation_frame: int = Field(default=5, ge=1, le=60)
    ppe_alert_confirm_frames: int = Field(default=6, ge=1, le=60)
    ppe_revoke_confirm_seconds: float = Field(default=2.0, ge=0.0, le=30.0)
    zone_alert_confirm_frames: int = Field(default=4, ge=1, le=60)

    model_config = SettingsConfigDict(
        env_file=(".env.production"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def validate_snapshot_storage(self) -> None:
        if self.snapshot_storage_backend != "s3":
            return
        missing = [
            name
            for name, value in (
                ("SNAPSHOT_STORAGE_BUCKET", self.snapshot_storage_bucket),
                ("SNAPSHOT_STORAGE_ENDPOINT_URL", self.snapshot_storage_endpoint_url),
                ("SNAPSHOT_STORAGE_ACCESS_KEY_ID", self.snapshot_storage_access_key_id),
                ("SNAPSHOT_STORAGE_SECRET_ACCESS_KEY", self.snapshot_storage_secret_access_key),
            )
            if not value
        ]
        if missing:
            raise ValueError(f"S3 snapshot storage requires {', '.join(missing)}")

    @model_validator(mode="after")
    def validate_remote_vision(self):
        if self.vision_provider == "remote" and not self.vision_remote_url:
            raise ValueError("VISION_REMOTE_URL is required when VISION_PROVIDER=remote")
        if (
            self.app_env == "production"
            and self.vision_provider == "remote"
            and not self.vision_remote_api_key.get_secret_value()
        ):
            raise ValueError("VISION_REMOTE_API_KEY is required for remote vision in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
