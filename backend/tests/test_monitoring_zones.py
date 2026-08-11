import base64
from uuid import uuid4

import cv2
import numpy as np

from backend.app.schemas.analysis import FrameInferenceRequest
from backend.app.schemas.ppe_requirement import PpeRequirementResponse
from backend.app.services.frame_inference_service import FrameInferenceService


def _zone(zone_id: str, points: list[tuple[float, float]], *, state: str = "stopped", order: int = 0):
    return {
        "zone_id": zone_id,
        "display_name": f"Vùng {zone_id}",
        "points": [{"x": x, "y": y} for x, y in points],
        "machine_state": state,
        "enabled": True,
        "order": order,
    }


def _rect(zone_id: str, left: float, top: float, right: float, bottom: float, **kwargs):
    return _zone(zone_id, [(left, top), (right, top), (right, bottom), (left, bottom)], **kwargs)


def _jpeg_data_url(width: int = 200, height: int = 100) -> str:
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    encoded, buffer = cv2.imencode(".jpg", frame)
    assert encoded
    return f"data:image/jpeg;base64,{base64.b64encode(buffer.tobytes()).decode()}"


def _no_ppe_requirements(camera_id: str, zone_id: str) -> PpeRequirementResponse:
    return PpeRequirementResponse(
        camera_id=camera_id,
        zone_id=zone_id,
        helmet_required=False,
        safety_glasses_required=False,
        gloves_required=False,
        is_configured=False,
        updated_at=None,
    )


def test_zone_collection_defaults_to_empty_and_saves_without_a_product_count_limit(client):
    empty = client.get("/api/v1/cameras/uploaded_video/monitoring-zones")
    assert empty.status_code == 200
    assert empty.json() == {
        "camera_id": "uploaded_video",
        "revision": 0,
        "zones": [],
        "updated_at": None,
    }

    zones = [_rect(f"zone_{index}", index / 30, 0.1, index / 30 + 0.02, 0.2, order=index) for index in range(20)]
    saved = client.put(
        "/api/v1/cameras/uploaded_video/monitoring-zones",
        json={"expected_revision": 0, "zones": zones},
    )

    assert saved.status_code == 200
    assert saved.json()["revision"] == 1
    assert len(saved.json()["zones"]) == 20


def test_zone_collection_save_is_idempotent_and_rejects_stale_revision(client):
    zones = [_rect("press_01", 0.1, 0.1, 0.3, 0.4)]
    first = client.put(
        "/api/v1/cameras/uploaded_video/monitoring-zones",
        json={"expected_revision": 0, "zones": zones},
    )
    retry = client.put(
        "/api/v1/cameras/uploaded_video/monitoring-zones",
        json={"expected_revision": 0, "zones": zones},
    )
    conflict = client.put(
        "/api/v1/cameras/uploaded_video/monitoring-zones",
        json={"expected_revision": 0, "zones": [_rect("press_01", 0.1, 0.1, 0.4, 0.4)]},
    )

    assert first.status_code == 200
    assert retry.status_code == 200
    assert retry.json()["revision"] == 1
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "revision_conflict"


def test_zone_collection_rejects_overlap_touch_and_containment_atomically(client):
    original = [_rect("safe", 0.05, 0.05, 0.2, 0.2)]
    assert (
        client.put(
            "/api/v1/cameras/uploaded_video/monitoring-zones",
            json={"expected_revision": 0, "zones": original},
        ).status_code
        == 200
    )

    invalid_pairs = [
        [_rect("a", 0.1, 0.1, 0.4, 0.4), _rect("b", 0.3, 0.3, 0.6, 0.6, order=1)],
        [_rect("a", 0.1, 0.1, 0.4, 0.4), _rect("b", 0.4, 0.2, 0.7, 0.5, order=1)],
        [_rect("a", 0.1, 0.1, 0.8, 0.8), _rect("b", 0.2, 0.2, 0.3, 0.3, order=1)],
    ]
    for zones in invalid_pairs:
        response = client.put(
            "/api/v1/cameras/uploaded_video/monitoring-zones",
            json={"expected_revision": 1, "zones": zones},
        )
        assert response.status_code == 422
        assert response.json()["detail"] == {
            "code": "zone_geometry_conflict",
            "zone_ids": ["a", "b"],
        }

    loaded = client.get("/api/v1/cameras/uploaded_video/monitoring-zones").json()
    assert loaded["revision"] == 1
    assert loaded["zones"] == original


def test_multi_zone_inference_evaluates_each_zone_and_runs_ppe_once(monkeypatch):
    observer_calls = 0

    def observe(frame, people):
        nonlocal observer_calls
        observer_calls += 1
        present = {
            "helmet": {"status": "present", "confidence": 0.9},
            "safety_glasses": {"status": "present", "confidence": 0.9},
            "gloves": {"status": "present", "confidence": 0.9},
        }
        return [present for _ in people]

    service = FrameInferenceService(ppe_observer=observe, requirement_loader=_no_ppe_requirements)
    monkeypatch.setattr(
        service,
        "_track_people",
        lambda session_id, frame: [
            (20, 10, 20, 40, 0.95, 1),
            (140, 10, 20, 40, 0.95, 2),
        ],
    )
    monkeypatch.setattr(service, "_has_safety_shirt", lambda *args: True)

    result = service.infer(
        FrameInferenceRequest(
            image_data=_jpeg_data_url(),
            monitoring_session_id=uuid4(),
            frame_id=1,
            zones=[
                _rect("left", 0.05, 0.1, 0.3, 0.8, state="stopped", order=0),
                _rect("right", 0.65, 0.1, 0.9, 0.8, state="running", order=1),
            ],
            zone_revision=3,
        )
    )

    assert observer_calls == 1
    assert result.review_required is True
    assert [item.model_dump() for item in result.people[0].zone_memberships] == [
        {"zone_id": "left", "inside": True},
        {"zone_id": "right", "inside": False},
    ]
    assert result.people[0].active_violations == []
    assert result.people[1].active_violations[0].rule_key == "zone_intrusion:right"
    assert result.people[1].active_violations[0].zone_id == "right"
    assert result.rule["zone_results"] == [
        {
            "zone_id": "left",
            "machine_state": "stopped",
            "person_inside_zone": True,
            "violation": False,
        },
        {
            "zone_id": "right",
            "machine_state": "running",
            "person_inside_zone": True,
            "violation": True,
        },
    ]


def test_multi_zone_request_rejects_legacy_and_new_configuration_together(client):
    response = client.post(
        "/api/v1/analysis/frame",
        json={
            "image_data": _jpeg_data_url(),
            "zone_points": [{"x": 0.1, "y": 0.1}] * 4,
            "zones": [_rect("left", 0.05, 0.1, 0.3, 0.8)],
        },
    )
    assert response.status_code == 422


def test_websocket_accepts_only_the_saved_zone_revision(client):
    zones = [
        _rect("left", 0.05, 0.1, 0.3, 0.8, order=0),
        _rect("right", 0.65, 0.1, 0.9, 0.8, state="running", order=1),
    ]
    saved = client.put(
        "/api/v1/cameras/uploaded_video/monitoring-zones",
        json={"expected_revision": 0, "zones": zones},
    ).json()

    with client.websocket_connect("/api/v1/ws/inference") as websocket:
        websocket.send_json(
            {
                "type": "configure",
                "monitoring_session_id": str(uuid4()),
                "camera_id": "uploaded_video",
                "zone_revision": 0,
                "zones": zones,
            }
        )
        stale = websocket.receive_json()
        websocket.send_json(
            {
                "type": "configure",
                "monitoring_session_id": str(uuid4()),
                "camera_id": "uploaded_video",
                "zone_revision": saved["revision"],
                "zones": zones,
            }
        )
        configured = websocket.receive_json()

    assert stale["code"] == "zone_revision_conflict"
    assert configured["type"] == "configured"
    assert configured["zone_revision"] == 1
