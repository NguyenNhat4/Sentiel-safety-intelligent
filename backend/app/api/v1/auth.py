from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.schemas.auth import AuthUser, LoginRequest, LoginResponse, SessionResponse
from backend.app.services.auth_service import (
    ROLE_LABELS,
    AccountInactiveError,
    AuthenticationUnavailableError,
    AuthService,
    InvalidCredentialsError,
    InvalidSessionError,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
bearer_scheme = HTTPBearer(auto_error=False)


def as_auth_user(user) -> AuthUser:
    try:
        role = user.role if hasattr(user.role, "value") else user.role
        return AuthUser(id=user.id, full_name=user.full_name, email=user.email, role=role, role_label=ROLE_LABELS[role])
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=500, detail="Account has an unsupported role") from exc


def require_token(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> str:
    if not credentials or credentials.scheme.lower() != "bearer" or not credentials.credentials.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer authentication is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    try:
        token, user, _ = service.login(payload.email, payload.password)
        return LoginResponse(access_token=token, user=as_auth_user(user))
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=401, detail="Invalid email or password", headers={"WWW-Authenticate": "Bearer"}
        ) from exc
    except AccountInactiveError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except AuthenticationUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/me", response_model=SessionResponse)
def get_me(token: str = Depends(require_token), db: Session = Depends(get_db)):
    try:
        user, expires_at = AuthService(db).get_current_user(token)
        return SessionResponse(user=as_auth_user(user), expires_at=expires_at)
    except InvalidSessionError as exc:
        raise HTTPException(status_code=401, detail=str(exc), headers={"WWW-Authenticate": "Bearer"}) from exc
    except AuthenticationUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/logout", status_code=204)
def logout(token: str = Depends(require_token), db: Session = Depends(get_db)):
    try:
        AuthService(db).logout(token)
    except InvalidSessionError as exc:
        raise HTTPException(status_code=401, detail=str(exc), headers={"WWW-Authenticate": "Bearer"}) from exc
    except AuthenticationUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
