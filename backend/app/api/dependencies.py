from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.user import User, UserRole
from backend.app.services.auth_service import AuthenticationUnavailableError, AuthService, InvalidSessionError

bearer_scheme = HTTPBearer(auto_error=False)


def require_token(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> str:
    if not credentials or credentials.scheme.lower() != "bearer" or not credentials.credentials.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer authentication is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def require_authenticated_user(token: str = Depends(require_token), db: Session = Depends(get_db)) -> User:
    try:
        user, _ = AuthService(db).get_current_user(token)
        return user
    except InvalidSessionError as exc:
        raise HTTPException(status_code=401, detail=str(exc), headers={"WWW-Authenticate": "Bearer"}) from exc
    except AuthenticationUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def require_roles(*allowed_roles: UserRole) -> Callable:
    def dependency(user: User = Depends(require_authenticated_user)) -> User:
        if user.must_change_password:
            raise HTTPException(status_code=403, detail="Password change is required before using the application")
        try:
            role = UserRole(user.role)
        except ValueError as exc:
            raise HTTPException(status_code=403, detail="Account role is not supported") from exc
        if role not in allowed_roles:
            raise HTTPException(status_code=403, detail="This role is not permitted to perform this action")
        return user

    return dependency


require_system_admin = require_roles(UserRole.SYSTEM_ADMIN)
