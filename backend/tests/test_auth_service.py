from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.api.v1.auth import require_admin
from backend.app.core.database import Base
from backend.app.models.user import User, UserRole
from backend.app.services.auth_service import (
    AuthService,
    InvalidCredentialsError,
    InvalidSessionError,
    UserManagementError,
    hash_password,
)


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


def test_system_admin_login_uses_supported_role_contract():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    service = AuthService(session)
    service.seed_demo_users()

    _, user, _ = service.login("admin@sentinel.local", "Sentinel123!")

    assert user.role == "system_admin"


def test_demo_seed_keeps_only_three_roles_and_removes_legacy_simulation_account():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(
        User(
            email="mophong@sentinel.local",
            full_name="Legacy Simulation Operator",
            role="simulation_operator",
            password_hash=hash_password("Sentinel123!"),
        )
    )
    session.commit()

    AuthService(session).seed_demo_users()

    users = session.query(User).order_by(User.email).all()
    assert {user.role for user in users} == {"system_admin", "safety_manager", "area_manager"}
    assert {user.email for user in users} == {
        "admin@sentinel.local",
        "antoan@sentinel.local",
        "khuvuc@sentinel.local",
    }


def test_system_admin_can_create_assign_reset_and_delete_user():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    service = AuthService(session)
    service.seed_demo_users()
    _, admin, _ = service.login("admin@sentinel.local", "Sentinel123!")

    created = service.create_user(
        full_name="Test User",
        email="test.user@sentinel.local",
        password="Initial123!",
        role=UserRole.AREA_MANAGER,
    )
    token, _, _ = service.login(created.email, "Initial123!")
    updated = service.update_role(actor=admin, target_user_id=created.id, role=UserRole.SAFETY_MANAGER)
    service.change_password(actor=admin, target_user_id=created.id, new_password="Changed123!", current_password=None)

    assert updated.role == UserRole.SAFETY_MANAGER.value
    assert [user.email for user in service.list_users(query="test.user", role=UserRole.SAFETY_MANAGER)] == [
        created.email
    ]
    try:
        service.get_current_user(token)
    except InvalidSessionError:
        pass
    else:
        raise AssertionError("Changing password must revoke existing sessions")

    service.login(created.email, "Changed123!")
    service.delete_user(actor=admin, target_user_id=created.id)
    assert service.list_users(query="test.user") == []


def test_admin_cannot_delete_self_or_demote_last_admin():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    service = AuthService(session)
    service.seed_demo_users()
    _, admin, _ = service.login("admin@sentinel.local", "Sentinel123!")

    for action in (
        lambda: service.delete_user(actor=admin, target_user_id=admin.id),
        lambda: service.update_role(actor=admin, target_user_id=admin.id, role=UserRole.SAFETY_MANAGER),
    ):
        try:
            action()
        except UserManagementError:
            pass
        else:
            raise AssertionError("The active administrator must not remove their own access")


def test_non_admin_is_forbidden_from_admin_dependency():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    service = AuthService(session)
    service.seed_demo_users()
    _, user, _ = service.login("antoan@sentinel.local", "Sentinel123!")

    try:
        require_admin(user)
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("Non-admin sessions must be forbidden")


def test_temporary_password_can_be_changed_once_and_admin_reset_reopens_flow():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    service = AuthService(session)
    service.seed_demo_users()
    _, admin, _ = service.login("admin@sentinel.local", "Sentinel123!")
    user = service.create_user(
        full_name="First Login User",
        email="first.login@sentinel.local",
        password="Temporary123!",
        role=UserRole.SAFETY_MANAGER,
    )

    assert user.must_change_password is True
    service.change_password(
        actor=user,
        target_user_id=user.id,
        new_password="Personal123!",
        current_password="Temporary123!",
    )
    assert user.must_change_password is False

    try:
        service.change_password(
            actor=user,
            target_user_id=user.id,
            new_password="Another123!",
            current_password="Personal123!",
        )
    except UserManagementError:
        pass
    else:
        raise AssertionError("A normal account must not change its password without a new admin reset")

    service.change_password(
        actor=admin,
        target_user_id=user.id,
        new_password="ResetByAdmin123!",
        current_password=None,
    )
    assert user.must_change_password is True
