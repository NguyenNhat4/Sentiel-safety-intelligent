import datetime
import hashlib
import hmac
import secrets

from sqlalchemy import or_, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from backend.app.models.monitoring_zone import MonitoringZoneRecord
from backend.app.models.user import User, UserRole, UserSession, utc_now

ROLE_LABELS = {
    UserRole.SYSTEM_ADMIN: "Quản trị hệ thống",
    UserRole.SAFETY_MANAGER: "Cán bộ an toàn",
    UserRole.AREA_MANAGER: "Quản lý khu vực",
}
SESSION_TTL = datetime.timedelta(hours=8)
DEMO_USERS = (
    ("admin@sentinel.local", "System Admin", UserRole.SYSTEM_ADMIN),
    ("antoan@sentinel.local", "Nguyễn Anh Tuấn", UserRole.SAFETY_MANAGER),
    ("khuvuc@sentinel.local", "Trần Minh Hà", UserRole.AREA_MANAGER),
)
LEGACY_SIMULATION_EMAIL = "mophong@sentinel.local"
LEGACY_SIMULATION_ROLE = "simulation_operator"


class AuthError(Exception):
    """Base exception for controlled authentication failures."""


class InvalidCredentialsError(AuthError):
    pass


class AccountInactiveError(AuthError):
    pass


class InvalidSessionError(AuthError):
    pass


class AuthenticationUnavailableError(AuthError):
    pass


class DuplicateEmailError(AuthError):
    pass


class UserManagementError(AuthError):
    pass


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    rounds = 310_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), rounds)
    return f"pbkdf2_sha256${rounds}${salt}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(rounds))
        return hmac.compare_digest(digest.hex(), expected)
    except (TypeError, ValueError):
        return False


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def seed_demo_users(self) -> None:
        try:
            legacy_user = (
                self.db.query(User)
                .filter(
                    User.email == LEGACY_SIMULATION_EMAIL,
                    User.role == LEGACY_SIMULATION_ROLE,
                )
                .first()
            )
            if legacy_user:
                self.db.delete(legacy_user)
            for email, full_name, role in DEMO_USERS:
                if not self.db.query(User).filter(User.email == email).first():
                    self.db.add(
                        User(
                            email=email,
                            full_name=full_name,
                            role=role.value,
                            password_hash=hash_password("Sentinel123!"),
                        )
                    )
            self.db.commit()
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise AuthenticationUnavailableError("Authentication storage is unavailable") from exc

    def login(self, email: str, password: str) -> tuple[str, User, datetime.datetime]:
        try:
            user = self.db.query(User).filter(User.email == email).first()
            if not user or not verify_password(password, user.password_hash):
                raise InvalidCredentialsError("Invalid email or password")
            if not user.is_active:
                raise AccountInactiveError("This account is inactive")
            token = secrets.token_urlsafe(48)
            expires_at = utc_now() + SESSION_TTL
            self.db.add(UserSession(user_id=user.id, token_digest=token_digest(token), expires_at=expires_at))
            self.db.commit()
            return token, user, expires_at
        except AuthError:
            raise
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise AuthenticationUnavailableError("Authentication storage is unavailable") from exc

    def list_users(self, query: str | None = None, role: UserRole | None = None) -> list[User]:
        try:
            users = self.db.query(User)
            if query:
                pattern = f"%{query.strip().lower()}%"
                users = users.filter(or_(User.email.ilike(pattern), User.full_name.ilike(pattern)))
            if role:
                users = users.filter(User.role == role.value)
            return users.order_by(User.full_name.asc(), User.email.asc()).all()
        except SQLAlchemyError as exc:
            raise AuthenticationUnavailableError("Authentication storage is unavailable") from exc

    def create_user(
        self,
        *,
        full_name: str,
        email: str,
        password: str,
        role: UserRole,
        managed_area_id: str | None = None,
        telegram_username: str | None = None,
        telegram_chat_id: str | None = None,
    ) -> User:
        try:
            self._validate_area_assignment(role, managed_area_id)
            normalized_email = email.strip().lower()
            if self.db.query(User.id).filter(User.email == normalized_email).first():
                raise DuplicateEmailError("An account with this email already exists")
            user = User(
                email=normalized_email,
                full_name=full_name.strip(),
                role=role.value,
                password_hash=hash_password(password),
                must_change_password=True,
                managed_area_id=managed_area_id if role == UserRole.AREA_MANAGER else None,
                telegram_username=telegram_username,
                telegram_chat_id=telegram_chat_id,
            )
            self.db.add(user)
            self.db.commit()
            return user
        except AuthError:
            raise
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise AuthenticationUnavailableError("Authentication storage is unavailable") from exc

    def update_role(
        self,
        *,
        actor: User,
        target_user_id: str,
        role: UserRole,
        managed_area_id: str | None = None,
        telegram_username: str | None = None,
        telegram_chat_id: str | None = None,
        update_telegram: bool = False,
        managed_camera_ids: list[str] | None = None,
    ) -> User:
        try:
            target = self._get_managed_user(target_user_id)
            if target.id == actor.id:
                raise UserManagementError("You cannot change your own role")
            if target.role == UserRole.SYSTEM_ADMIN.value and role != UserRole.SYSTEM_ADMIN:
                self._require_another_admin(target.id)
            self._validate_area_assignment(role, managed_area_id)
            target.role = role.value
            target.managed_area_id = managed_area_id if role == UserRole.AREA_MANAGER else None
            if managed_camera_ids is not None:
                allowed = {"cam_1", "cam_2", "cam_3", "cam_4"}
                if not set(managed_camera_ids).issubset(allowed):
                    raise UserManagementError("Unsupported camera assignment")
                target.managed_camera_ids = sorted(set(managed_camera_ids)) if role == UserRole.AREA_MANAGER else []
            if update_telegram:
                target.telegram_username = telegram_username
                target.telegram_chat_id = telegram_chat_id
            self._revoke_sessions(target)
            self.db.commit()
            return target
        except AuthError:
            raise
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise AuthenticationUnavailableError("Authentication storage is unavailable") from exc

    def change_password(
        self, *, actor: User, target_user_id: str, new_password: str, current_password: str | None
    ) -> User:
        try:
            target = self._get_managed_user(target_user_id)
            if target.id == actor.id:
                if not target.must_change_password:
                    raise UserManagementError(
                        "Password change requires a new temporary password from a system administrator"
                    )
                if not current_password or not verify_password(current_password, actor.password_hash):
                    raise UserManagementError("The current temporary password is required")
                target.must_change_password = False
            else:
                target.must_change_password = True
            target.password_hash = hash_password(new_password)
            self._revoke_sessions(target)
            self.db.commit()
            return target
        except AuthError:
            raise
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise AuthenticationUnavailableError("Authentication storage is unavailable") from exc

    def delete_user(self, *, actor: User, target_user_id: str) -> None:
        try:
            target = self._get_managed_user(target_user_id)
            if target.id == actor.id:
                raise UserManagementError("You cannot delete your own account")
            if target.role == UserRole.SYSTEM_ADMIN.value:
                self._require_another_admin(target.id)
            self.db.delete(target)
            self.db.commit()
        except AuthError:
            raise
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise AuthenticationUnavailableError("Authentication storage is unavailable") from exc

    def disconnect_telegram(self, *, target_user_id: str) -> User:
        try:
            target = self._get_managed_user(target_user_id)
            target.telegram_chat_id = None
            target.telegram_username = None
            self.db.commit()
            return target
        except AuthError:
            raise
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise AuthenticationUnavailableError("Authentication storage is unavailable") from exc

    def get_current_user(self, token: str) -> tuple[User, datetime.datetime]:
        try:
            now = utc_now()
            session = (
                self.db.query(UserSession)
                .options(joinedload(UserSession.user))
                .filter(
                    UserSession.token_digest == token_digest(token),
                    UserSession.revoked_at.is_(None),
                    UserSession.expires_at > now,
                )
                .first()
            )
            if not session or not session.user or not session.user.is_active:
                raise InvalidSessionError("Session is invalid, expired, or revoked")
            return session.user, session.expires_at
        except AuthError:
            raise
        except SQLAlchemyError as exc:
            raise AuthenticationUnavailableError("Authentication storage is unavailable") from exc

    def logout(self, token: str) -> None:
        try:
            session = (
                self.db.query(UserSession)
                .filter(UserSession.token_digest == token_digest(token), UserSession.revoked_at.is_(None))
                .first()
            )
            if not session:
                raise InvalidSessionError("Session is invalid, expired, or revoked")
            session.revoked_at = utc_now()
            self.db.commit()
        except AuthError:
            raise
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise AuthenticationUnavailableError("Authentication storage is unavailable") from exc

    def _get_managed_user(self, user_id: str) -> User:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserManagementError("Account was not found")
        return user

    def _require_another_admin(self, excluded_user_id: str) -> None:
        another_admin = (
            self.db.query(User.id)
            .filter(
                User.role == UserRole.SYSTEM_ADMIN.value,
                User.id != excluded_user_id,
                User.is_active.is_(True),
            )
            .first()
        )
        if not another_admin:
            raise UserManagementError("The last active system administrator cannot be removed")

    def _validate_area_assignment(self, role: UserRole, managed_area_id: str | None) -> None:
        if role != UserRole.AREA_MANAGER:
            return
        if not managed_area_id:
            raise UserManagementError("Area managers must be assigned to a monitoring area")
        exists = (
            self.db.query(MonitoringZoneRecord.id)
            .filter(
                MonitoringZoneRecord.zone_id == managed_area_id,
            )
            .first()
        )
        if not exists:
            raise UserManagementError("The assigned monitoring area does not exist")

    def _revoke_sessions(self, user: User) -> None:
        revoked_at = utc_now()
        self.db.execute(
            update(UserSession)
            .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
            .values(revoked_at=revoked_at)
        )
