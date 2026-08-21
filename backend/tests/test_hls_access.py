import base64
import json

import pytest
from fastapi import HTTPException

from backend.app.api.v1.auth import create_hls_token, require_hls_viewer
from backend.app.models.stream_configuration import StreamConfiguration
from backend.app.models.user import User, UserRole
from backend.app.services.auth_service import hash_password


def _decode_payload(token: str) -> dict[str, object]:
    encoded = token.split(".", 1)[0]
    return json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))


def test_safety_manager_receives_fifteen_minute_hls_token_for_all_cameras(db_session, monkeypatch) -> None:
    monkeypatch.setenv("HLS_TOKEN_SECRET", "test-secret-that-is-at-least-thirty-two-bytes")
    db_session.add(
        StreamConfiguration(
            id=1,
            mappings=[{"camera_id": "cam_1", "stream_camera_id": "line_a"}],
        )
    )
    db_session.commit()

    actor = db_session.query(User).filter(User.email == "safety.test@sentinel.local").first()
    if actor is None:
        actor = User(
            email="safety.hls@sentinel.local",
            full_name="Safety HLS",
            role=UserRole.SAFETY_MANAGER.value,
            password_hash=hash_password("Sentinel123!"),
        )
        db_session.add(actor)
        db_session.commit()
    response = create_hls_token(actor=actor, db=db_session)

    assert response.expires_in == 900
    assert response.token_type == "bearer"
    payload = _decode_payload(response.access_token)
    assert payload["role"] == "safety_manager"
    assert payload["cameras"] == ["*"]
    assert int(payload["exp"]) - int(payload["iat"]) == 900


def test_area_manager_cannot_receive_hls_token(db_session) -> None:
    user = User(
        email="area.hls@sentinel.local",
        full_name="Area HLS",
        role=UserRole.AREA_MANAGER.value,
        password_hash=hash_password("Sentinel123!"),
        managed_area_id="zone_1",
    )
    db_session.add(user)
    db_session.commit()
    with pytest.raises(HTTPException) as error:
        require_hls_viewer(user)
    assert error.value.status_code == 403
