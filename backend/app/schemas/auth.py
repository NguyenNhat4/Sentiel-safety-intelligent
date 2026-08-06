from datetime import datetime

from pydantic import BaseModel, Field, field_validator

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


class AuthUser(BaseModel):
    id: str
    full_name: str
    email: str
    role: UserRole
    role_label: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUser


class SessionResponse(BaseModel):
    user: AuthUser
    expires_at: datetime
