from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.app.models.user import UserRole


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=256)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("email must be a valid email address")
        return normalized


class UserCreate(LoginRequest):
    full_name: str = Field(min_length=1, max_length=120)
    role: UserRole
    managed_area_id: str | None = Field(default=None, min_length=1, max_length=50)
    telegram_username: str | None = Field(default=None, min_length=6, max_length=33, pattern=r"^@[A-Za-z0-9_]{5,32}$")
    telegram_chat_id: str | None = Field(default=None, min_length=1, max_length=64, pattern=r"^-?[0-9]+$")

    @model_validator(mode="after")
    def require_area_for_area_manager(self):
        if self.role == UserRole.AREA_MANAGER and not self.managed_area_id:
            raise ValueError("managed_area_id is required for area_manager")
        return self


class UserRoleUpdate(BaseModel):
    role: UserRole
    managed_area_id: str | None = Field(default=None, min_length=1, max_length=50)
    telegram_username: str | None = Field(default=None, min_length=6, max_length=33, pattern=r"^@[A-Za-z0-9_]{5,32}$")
    telegram_chat_id: str | None = Field(default=None, min_length=1, max_length=64, pattern=r"^-?[0-9]+$")
    managed_camera_ids: list[str] | None = None

    @model_validator(mode="after")
    def require_area_for_area_manager(self):
        if self.role == UserRole.AREA_MANAGER and not self.managed_area_id:
            raise ValueError("managed_area_id is required for area_manager")
        return self


class PasswordChangeRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=256)
    current_password: str | None = Field(default=None, min_length=8, max_length=256)


class AuthUser(BaseModel):
    id: str
    full_name: str
    email: str
    role: UserRole
    role_label: str
    must_change_password: bool
    managed_area_id: str | None = None
    managed_camera_ids: list[str] = Field(default_factory=list)
    telegram_username: str | None = None
    telegram_chat_id: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUser


class SessionResponse(BaseModel):
    user: AuthUser
    expires_at: datetime


class ManagedUser(AuthUser):
    is_active: bool
    created_at: datetime


class TelegramLinkStart(BaseModel):
    link_url: str
    expires_at: datetime


class TelegramLinkComplete(BaseModel):
    status: str
    chat_id: str | None = None
    telegram_username: str | None = None
