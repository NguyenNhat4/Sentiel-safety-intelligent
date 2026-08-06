from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base
from backend.app.services.auth_service import AuthService, InvalidCredentialsError, InvalidSessionError


def test_login_session_lookup_and_logout():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    service = AuthService(session)
    service.seed_demo_users()
    token, user, _ = service.login("antoan@sentinel.local", "Sentinel123!")
    current_user, _ = service.get_current_user(token)
    assert current_user.id == user.id
    service.logout(token)
    try:
        service.get_current_user(token)
    except InvalidSessionError:
        pass
    else:
        raise AssertionError("A logged-out token must be rejected")


def test_login_rejects_invalid_credentials():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    service = AuthService(session)
    service.seed_demo_users()
    try:
        service.login("antoan@sentinel.local", "invalid-password")
    except InvalidCredentialsError:
        pass
    else:
        raise AssertionError("Invalid credentials must be rejected")
