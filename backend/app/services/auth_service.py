import datetime
import hashlib
import hmac
import secrets

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models.user import User, UserRole, UserSession, utc_now

ROLE_LABELS = {
    UserRole.SAFETY_MANAGER: "Quản lý an toàn",
    UserRole.AREA_MANAGER: "Quản lý khu vực",
    UserRole.SIMULATION_OPERATOR: "Vận hành mô phỏng",
}
SESSION_TTL = datetime.timedelta(hours=8)
DEMO_USERS = (
    ("antoan@sentinel.local", "Nguyễn Anh Tuấn", UserRole.SAFETY_MANAGER),
    ("khuvuc@sentinel.local", "Trần Minh Hà", UserRole.AREA_MANAGER),
    ("mophong@sentinel.local", "Lê Gia Huy", UserRole.SIMULATION_OPERATOR),
)


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

    def get_current_user(self, token: str) -> tuple[User, datetime.datetime]:
        try:
            now = utc_now()
            session = (
                self.db.query(UserSession)
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
