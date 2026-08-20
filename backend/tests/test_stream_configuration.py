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


def _safety_manager_headers(db_session):
    token, _, _ = AuthService(db_session).login("safety.test@sentinel.local", "Sentinel123!")
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


def test_system_admin_can_persist_four_unique_camera_stream_mappings(client, db_session):
    admin_headers = _admin_headers(client, db_session)
    mappings = [
        {"camera_id": "cam_1", "stream_id": "stream_warehouse"},
        {"camera_id": "cam_2", "stream_id": "stream_gate"},
        {"camera_id": "cam_3", "stream_id": "stream_line"},
        {"camera_id": "cam_4", "stream_id": "stream_loading"},
    ]

    saved = client.put("/api/v1/stream-config", headers=admin_headers, json={"mappings": mappings})

    assert saved.status_code == 200
    assert saved.json()["mappings"] == mappings
    reread = client.get("/api/v1/stream-config")
    assert reread.json()["mappings"] == mappings


def test_stream_configuration_rejects_a_stream_assigned_to_two_cameras(client, db_session):
    admin_headers = _admin_headers(client, db_session)
    duplicate = {
        "mappings": [
            {"camera_id": "cam_1", "stream_id": "stream_gate"},
            {"camera_id": "cam_2", "stream_id": "stream_gate"},
        ]
    }

    response = client.put("/api/v1/stream-config", headers=admin_headers, json=duplicate)

    assert response.status_code == 409


def test_safety_manager_cannot_change_multi_camera_mapping(client, db_session):
    response = client.put(
        "/api/v1/stream-config",
        headers=_safety_manager_headers(db_session),
        json={"mappings": [{"camera_id": "cam_1", "stream_id": "stream_gate"}]},
    )

    assert response.status_code == 403


def test_stream_configuration_rejects_more_than_four_camera_mappings(client, db_session):
    admin_headers = _admin_headers(client, db_session)
    mappings = [
        {"camera_id": f"cam_{index}", "stream_id": f"stream_{index}"}
        for index in range(1, 6)
    ]

    response = client.put("/api/v1/stream-config", headers=admin_headers, json={"mappings": mappings})

    assert response.status_code == 400


def test_safety_manager_cannot_disconnect_a_camera(client, db_session):
    response = client.delete(
        "/api/v1/stream-config/cam_1",
        headers=_safety_manager_headers(db_session),
    )

    assert response.status_code == 403


def test_disconnect_removes_only_the_selected_camera_mapping(client, db_session):
    admin_headers = _admin_headers(client, db_session)
    client.put(
        "/api/v1/stream-config",
        headers=admin_headers,
        json={
            "mappings": [
                {"camera_id": "cam_1", "stream_id": "stream_gate"},
                {"camera_id": "cam_2", "stream_id": "stream_line"},
            ]
        },
    )

    disconnected = client.delete("/api/v1/stream-config/cam_1", headers=admin_headers)

    assert disconnected.status_code == 200
    assert disconnected.json()["mappings"] == [{"camera_id": "cam_2", "stream_id": "stream_line"}]
