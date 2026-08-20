from backend.app.models.user import User, UserRole
from backend.app.services.auth_service import AuthService, hash_password


def _admin_headers(client, db_session):
    db_session.add(
        User(
            email="admin.stream@sentinel.local",
            full_name="Stream Admin",
            role=UserRole.SYSTEM_ADMIN.value,
            password_hash=hash_password("Sentinel123!"),
        )
    )
    db_session.commit()
    token, _, _ = AuthService(db_session).login("admin.stream@sentinel.local", "Sentinel123!")
    return {"Authorization": f"Bearer {token}"}


def test_stream_configuration_defaults_to_empty_for_authenticated_user(client):
    response = client.get("/api/v1/stream-config")
    assert response.status_code == 200
    assert response.json()["active_camera_id"] is None


def test_only_system_admin_can_update_stream_configuration(client, db_session):
    response = client.put("/api/v1/stream-config", json={"camera_id": "cam_1"})
    assert response.status_code == 403

    admin_headers = _admin_headers(client, db_session)
    saved = client.put("/api/v1/stream-config", headers=admin_headers, json={"camera_id": "cam_1"})
    assert saved.status_code == 200
    assert saved.json()["active_camera_id"] == "cam_1"

    disabled = client.put("/api/v1/stream-config", headers=admin_headers, json={"camera_id": None})
    assert disabled.status_code == 200
    assert disabled.json()["active_camera_id"] is None
