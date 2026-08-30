from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.dependencies import require_authenticated_user, require_system_admin, require_token
from backend.app.core.database import get_db
from backend.app.models.user import User, UserRole
from backend.app.schemas.auth import (
    AuthUser,
    LoginRequest,
    LoginResponse,
    ManagedUser,
    PasswordChangeRequest,
    SessionResponse,
    TelegramLinkComplete,
    TelegramLinkStart,
    UserCreate,
    UserRoleUpdate,
)
from backend.app.services.auth_service import (
    ROLE_LABELS,
    AccountInactiveError,
    AuthenticationUnavailableError,
    AuthService,
    DuplicateEmailError,
    InvalidCredentialsError,
    InvalidSessionError,
    UserManagementError,
)
from backend.app.services.telegram_link_service import TelegramLinkError, TelegramLinkService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def as_auth_user(user) -> AuthUser:
    try:
        role = user.role if hasattr(user.role, "value") else user.role
        return AuthUser(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            role=role,
            role_label=ROLE_LABELS[role],
            must_change_password=user.must_change_password,
            managed_area_id=user.managed_area_id,
            managed_camera_ids=user.managed_camera_ids or [],
            telegram_username=user.telegram_username,
            telegram_chat_id=user.telegram_chat_id,
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=500, detail="Account has an unsupported role") from exc


def as_managed_user(user) -> ManagedUser:
    auth_user = as_auth_user(user)
    return ManagedUser(**auth_user.model_dump(), is_active=user.is_active, created_at=user.created_at)


require_admin = require_system_admin


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


@router.put("/password", response_model=AuthUser)
def change_own_password(
    payload: PasswordChangeRequest,
    actor: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    try:
        return as_auth_user(
            AuthService(db).change_password(
                actor=actor,
                target_user_id=actor.id,
                new_password=payload.new_password,
                current_password=payload.current_password,
            )
        )
    except UserManagementError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AuthenticationUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/users", response_model=list[ManagedUser])
def list_users(
    query: str | None = None,
    role: UserRole | None = None,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return [as_managed_user(user) for user in AuthService(db).list_users(query=query, role=role)]
    except AuthenticationUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/users", response_model=ManagedUser, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    try:
        user = AuthService(db).create_user(
            full_name=payload.full_name,
            email=payload.email,
            password=payload.password,
            role=payload.role,
            managed_area_id=payload.managed_area_id,
            telegram_username=payload.telegram_username,
            telegram_chat_id=payload.telegram_chat_id,
        )
        return as_managed_user(user)
    except DuplicateEmailError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except UserManagementError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AuthenticationUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.put("/users/{user_id}/role", response_model=ManagedUser)
def update_user_role(
    user_id: str,
    payload: UserRoleUpdate,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return as_managed_user(
            AuthService(db).update_role(
                actor=actor,
                target_user_id=user_id,
                role=payload.role,
                managed_area_id=payload.managed_area_id,
                telegram_username=payload.telegram_username,
                telegram_chat_id=payload.telegram_chat_id,
                update_telegram=bool({"telegram_username", "telegram_chat_id"} & payload.model_fields_set),
                managed_camera_ids=payload.managed_camera_ids,
            )
        )
    except UserManagementError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AuthenticationUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/users/{user_id}/telegram-link", response_model=TelegramLinkStart)
def start_telegram_link(user_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    try:
        link_url, expires_at = TelegramLinkService(db).start(user_id)
        return TelegramLinkStart(link_url=link_url, expires_at=expires_at)
    except TelegramLinkError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/users/{user_id}/telegram-link/complete", response_model=TelegramLinkComplete)
def complete_telegram_link(user_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    try:
        status_value, chat_id, username = TelegramLinkService(db).complete(user_id)
        return TelegramLinkComplete(status=status_value, chat_id=chat_id, telegram_username=username)
    except TelegramLinkError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.delete("/users/{user_id}/telegram-link", response_model=ManagedUser)
def disconnect_telegram_link(user_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    try:
        return as_managed_user(AuthService(db).disconnect_telegram(target_user_id=user_id))
    except UserManagementError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AuthenticationUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.put("/users/{user_id}/password", response_model=AuthUser)
def change_user_password(
    user_id: str,
    payload: PasswordChangeRequest,
    actor: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        return as_auth_user(
            AuthService(db).change_password(
                actor=actor,
                target_user_id=user_id,
                new_password=payload.new_password,
                current_password=payload.current_password,
            )
        )
    except UserManagementError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AuthenticationUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: str, actor: User = Depends(require_admin), db: Session = Depends(get_db)):
    try:
        AuthService(db).delete_user(actor=actor, target_user_id=user_id)
    except UserManagementError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AuthenticationUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
