from backend.app.models.monitoring_zone import MonitoringZoneCollection
from backend.app.models.ppe_requirement import PpeRequirement
from backend.app.models.user import User, UserRole
from backend.app.services.auth_service import AuthService, hash_password


# ==========================================
# FIXTURES & HELPERS (Tạo dữ liệu chuẩn, cô lập)
# ==========================================
def _create_user_and_get_headers(client, db_session, email: str, role: UserRole):
    """Helper dùng chung: Tạo user độc lập trong DB và lấy JWT Token."""
    user = User(
        email=email,
        full_name=f"Test {role.value}",
        role=role.value,
        password_hash=hash_password("Sentinel123!"),
    )
    db_session.add(user)
    db_session.commit()
    token, _, _ = AuthService(db_session).login(email, "Sentinel123!")
    return {"Authorization": f"Bearer {token}"}


def _admin_headers(client, db_session):
    return _create_user_and_get_headers(client, db_session, "admin.stream@sentinel.local", UserRole.SYSTEM_ADMIN)


def _safety_manager_headers(client, db_session):
    # ĐÃ FIX: Tự tạo user độc lập, không dựa dẫm vào DB seed sẵn
    return _create_user_and_get_headers(client, db_session, "safety.stream@sentinel.local", UserRole.SAFETY_MANAGER)


# ==========================================
# TEST CASES
# ==========================================


def test_stream_configuration_defaults_to_empty_for_authenticated_user(client, db_session):
    """User đã đăng nhập khi chưa cấu hình gì sẽ nhận về danh sách rỗng."""
    # ĐÃ FIX: Truyền token hợp lệ đúng như tên hàm
    sm_headers = _safety_manager_headers(client, db_session)
    response = client.get("/api/v1/stream-config", headers=sm_headers)

    assert response.status_code == 200
    assert response.json().get("mappings", []) == []


def test_unauthenticated_request_is_rejected(client):
    """Chưa đăng nhập mà cố tình thay đổi cấu hình phải bị chặn (401 Unauthorized)."""
    # ĐÃ THÊM: Kiểm tra bảo mật tầng Authentication
    response = client.put(
        "/api/v1/stream-config",
        headers={"Authorization": ""},
        json={"camera_id": "cam_1"},
    )
    assert response.status_code == 401


def test_system_admin_can_persist_four_unique_camera_stream_mappings(client, db_session):
    """Admin lưu thành công 4 camera và dữ liệu tồn tại bền vững trong DB."""
    admin_headers = _admin_headers(client, db_session)
    mappings = [
        {"camera_id": "cam_1", "stream_camera_id": "stream_warehouse"},
        {"camera_id": "cam_2", "stream_camera_id": "stream_gate"},
        {"camera_id": "cam_3", "stream_camera_id": "stream_line"},
        {"camera_id": "cam_4", "stream_camera_id": "stream_loading"},
    ]

    saved = client.put("/api/v1/stream-config", headers=admin_headers, json={"mappings": mappings})
    assert saved.status_code == 200
    assert saved.json()["mappings"] == [{**mapping, "machine_state": "stopped"} for mapping in mappings]

    # Kiểm tra tính bền vững qua GET
    reread = client.get("/api/v1/stream-config", headers=admin_headers)
    assert reread.status_code == 200
    assert reread.json()["mappings"] == [{**mapping, "machine_state": "stopped"} for mapping in mappings]


def test_machine_state_is_persisted_per_camera(client, db_session):
    admin_headers = _admin_headers(client, db_session)
    response = client.put(
        "/api/v1/stream-config",
        headers=admin_headers,
        json={"mappings": [{"camera_id": "cam_1", "stream_camera_id": "stream_gate", "machine_state": "running"}]},
    )
    assert response.status_code == 200
    assert response.json()["mappings"] == [
        {"camera_id": "cam_1", "stream_camera_id": "stream_gate", "machine_state": "running"}
    ]


def test_stream_configuration_rejects_a_stream_assigned_to_two_cameras(client, db_session):
    """Từ chối 409 Conflict nếu gán 1 stream cho 2 camera khác nhau."""
    admin_headers = _admin_headers(client, db_session)
    duplicate = {
        "mappings": [
            {"camera_id": "cam_1", "stream_camera_id": "stream_gate"},
            {"camera_id": "cam_2", "stream_camera_id": "stream_gate"},
        ]
    }

    response = client.put("/api/v1/stream-config", headers=admin_headers, json=duplicate)
    assert response.status_code == 409


def test_stream_configuration_rejects_more_than_four_camera_mappings(client, db_session):
    """Từ chối 422 Unprocessable Entity nếu gửi cấu hình vượt quá 4 camera."""
    admin_headers = _admin_headers(client, db_session)
    mappings = [
        {"camera_id": f"cam_{index}", "stream_camera_id": f"stream_{index}"}
        for index in range(1, 6)  # 5 camera
    ]

    response = client.put("/api/v1/stream-config", headers=admin_headers, json={"mappings": mappings})
    assert response.status_code == 422


def test_safety_manager_cannot_change_multi_camera_mapping(client, db_session):
    """Safety Manager đã đăng nhập nhưng không có quyền sửa cấu hình (403 Forbidden)."""
    sm_headers = _safety_manager_headers(client, db_session)
    response = client.put(
        "/api/v1/stream-config",
        headers=sm_headers,
        json={"mappings": [{"camera_id": "cam_1", "stream_camera_id": "stream_gate"}]},
    )
    assert response.status_code == 403


def test_safety_manager_cannot_disconnect_a_camera(client, db_session):
    """Safety Manager không có quyền ngắt kết nối camera (403 Forbidden)."""
    sm_headers = _safety_manager_headers(client, db_session)
    response = client.delete("/api/v1/stream-config/cam_1", headers=sm_headers)
    assert response.status_code == 403


def test_disconnect_removes_only_the_selected_camera_mapping(client, db_session):
    """Ngắt kết nối chỉ xoá camera chỉ định, camera khác giữ nguyên và DB cập nhật thật."""
    admin_headers = _admin_headers(client, db_session)
    client.put(
        "/api/v1/stream-config",
        headers=admin_headers,
        json={
            "mappings": [
                {"camera_id": "cam_1", "stream_camera_id": "stream_gate"},
                {"camera_id": "cam_2", "stream_camera_id": "stream_line"},
            ]
        },
    )

    # Thực hiện disconnect cam_1
    disconnected = client.delete("/api/v1/stream-config/cam_1", headers=admin_headers)
    assert disconnected.status_code == 200
    assert disconnected.json()["mappings"] == [
        {"camera_id": "cam_2", "stream_camera_id": "stream_line", "machine_state": "stopped"}
    ]

    # ĐÃ FIX: Đọc lại DB qua GET để chứng minh cam_1 đã biến mất hoàn toàn
    reread = client.get("/api/v1/stream-config", headers=admin_headers)
    assert reread.json()["mappings"] == [
        {"camera_id": "cam_2", "stream_camera_id": "stream_line", "machine_state": "stopped"}
    ]


def test_disconnect_deletes_selected_camera_rules_and_zones(client, db_session):
    admin_headers = _admin_headers(client, db_session)
    db_session.add(MonitoringZoneCollection(camera_id="cam_1"))
    db_session.add(PpeRequirement(camera_id="cam_1", zone_id="press", hat_required=True, vest_required=False))
    db_session.add(PpeRequirement(camera_id="cam_2", zone_id="gate", hat_required=True, vest_required=False))
    db_session.commit()
    client.put(
        "/api/v1/stream-config",
        headers=admin_headers,
        json={
            "mappings": [
                {"camera_id": "cam_1", "stream_camera_id": "stream_gate"},
                {"camera_id": "cam_2", "stream_camera_id": "stream_line"},
            ]
        },
    )
    client.delete("/api/v1/stream-config/cam_1", headers=admin_headers)
    assert db_session.get(MonitoringZoneCollection, "cam_1") is None
    assert db_session.query(PpeRequirement).filter_by(camera_id="cam_1").count() == 0
    assert db_session.query(PpeRequirement).filter_by(camera_id="cam_2").count() == 1


def test_admin_disconnect_of_unknown_camera_is_idempotent(client, db_session):
    admin_headers = _admin_headers(client, db_session)

    response = client.delete("/api/v1/stream-config/cam_999", headers=admin_headers)

    assert response.status_code == 200
