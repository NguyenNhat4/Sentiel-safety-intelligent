import base64
import re
from uuid import uuid4

import cv2
import numpy as np
import pytest

from backend.app.api.v1.analysis import frame_inference_service
from backend.app.schemas.analysis import FrameInferenceRequest
from backend.app.schemas.ppe_requirement import PpeRequirementResponse
from backend.app.services.violation_tracking_service import ViolationTrackingService


def jpeg_bytes(width=160, height=120):
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    encoded, buffer = cv2.imencode(".jpg", frame)
    assert encoded
    return buffer.tobytes()


@pytest.fixture(autouse=True)
def use_stubbed_vision_observations(monkeypatch):
    """Keep analysis rule tests independent from the installed vision model."""
    monkeypatch.setattr(frame_inference_service, "_violation_tracker", ViolationTrackingService(activation_frames=1))
    monkeypatch.setattr(frame_inference_service, "_vision_analyzer", None)
    monkeypatch.setattr(
        frame_inference_service,
        "_ppe_observer",
        lambda frame, people: [
            {
                "hat": {"status": "unknown", "confidence": None},
                "vest": {"status": "unknown", "confidence": None},
            }
            for _ in people
        ],
    )


def jpeg_data_url(width=160, height=120):
    return f"data:image/jpeg;base64,{base64.b64encode(jpeg_bytes(width, height)).decode()}"


def configure_inference_websocket(websocket, zone_points=None, monitoring_session_id=None):
    monitoring_session_id = monitoring_session_id or str(uuid4())
    websocket.send_json(
        {
            "type": "configure",
            "monitoring_session_id": monitoring_session_id,
            "zone_points": zone_points
            or [
                {"x": 0.1, "y": 0.1},
                {"x": 0.9, "y": 0.1},
                {"x": 0.9, "y": 0.95},
                {"x": 0.1, "y": 0.95},
            ],
            "machine_state": "running",
        }
    )
    assert websocket.receive_json() == {
        "type": "configured",
        "monitoring_session_id": monitoring_session_id,
    }
    return monitoring_session_id


def send_inference_websocket_frame(websocket, frame_id=1, video_time=1.5, frame=None):
    websocket.send_json({"type": "frame_meta", "frame_id": frame_id, "video_time": video_time})
    websocket.send_bytes(frame if frame is not None else jpeg_bytes())
    return websocket.receive_json()


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"ok", "degraded"}
    assert isinstance(data["ready"], bool)
    assert set(data["dependencies"]) == {"postgresql", "snapshot_storage"}


def test_frontend_is_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Sentinel" in response.text

    asset_path = re.search(r'(?:src|href)="(/assets/[^"]+\.js)"', response.text)
    assert asset_path is not None
    script = client.get(asset_path.group(1))
    assert script.status_code == 200
    assert "Sentinel" in script.text


def test_start_analysis(client):
    payload = {
        "source_type": "demo",
        "source_path": "data/demo/test.mp4",
        "zone_ids": ["zone_01"],
        "enable_privacy_blur": True,
        "conf_threshold": 0.5,
    }
    response = client.post("/api/v1/analysis/start", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["status"] == "running"


def test_stop_analysis(client):
    start_resp = client.post(
        "/api/v1/analysis/start",
        json={"source_type": "demo", "source_path": "data/demo/test.mp4", "zone_ids": ["zone_01"]},
    )
    session_id = start_resp.json()["session_id"]

    stop_resp = client.post(f"/api/v1/analysis/stop/{session_id}")
    assert stop_resp.status_code == 200
    assert stop_resp.json()["status"] == "stopped"


def test_frame_inference_returns_normal_without_people(client, monkeypatch):
    monkeypatch.setattr(frame_inference_service, "_detect_people", lambda frame: [])
    response = client.post(
        "/api/v1/analysis/frame",
        json={
            "image_data": jpeg_data_url(),
            "zone_points": [
                {"x": 0.1, "y": 0.1},
                {"x": 0.9, "y": 0.1},
                {"x": 0.9, "y": 0.9},
                {"x": 0.1, "y": 0.9},
            ],
            "machine_state": "running",
        },
    )
    assert response.status_code == 200
    assert response.json()["result"] == "normal"
    assert response.json()["review_required"] is False
    assert response.json()["people"] == []


def test_frame_inference_violates_for_person_inside_zone(client, monkeypatch):
    monkeypatch.setattr(
        frame_inference_service,
        "_detect_people",
        lambda frame: [(40, 10, 40, 90, 0.91)],
    )
    response = client.post(
        "/api/v1/analysis/frame",
        json={
            "image_data": jpeg_data_url(),
            "zone_points": [
                {"x": 0.1, "y": 0.1},
                {"x": 0.9, "y": 0.1},
                {"x": 0.9, "y": 0.95},
                {"x": 0.1, "y": 0.95},
            ],
            "machine_state": "running",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["result"] == "violate"
    assert body["review_required"] is True
    assert body["people"][0]["inside_zone"] is True
    assert body["snapshot_data"].startswith("data:image/jpeg;base64,")


def test_frame_inference_violates_for_zone_entry(client, monkeypatch):
    monkeypatch.setattr(
        frame_inference_service,
        "_detect_people",
        lambda frame: [(40, 10, 40, 90, 0.91)],
    )
    response = client.post(
        "/api/v1/analysis/frame",
        json={
            "image_data": jpeg_data_url(),
            "zone_points": [
                {"x": 0.1, "y": 0.1},
                {"x": 0.9, "y": 0.1},
                {"x": 0.9, "y": 0.95},
                {"x": 0.1, "y": 0.95},
            ],
            "machine_state": "running",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["result"] == "violate"
    assert body["review_required"] is True
    assert body["snapshot_data"].startswith("data:image/jpeg;base64,")


def test_frame_inference_rejects_invalid_image(client):
    response = client.post(
        "/api/v1/analysis/frame",
        json={
            "image_data": "not-base64",
            "zone_points": [
                {"x": 0.1, "y": 0.1},
                {"x": 0.9, "y": 0.1},
                {"x": 0.9, "y": 0.9},
                {"x": 0.1, "y": 0.9},
            ],
        },
    )
    assert response.status_code == 400


def test_zone_entry_requests_review_when_machine_is_stopped(monkeypatch):
    monkeypatch.setattr(
        frame_inference_service,
        "_detect_people",
        lambda frame: [(40, 10, 40, 90, 0.91)],
    )
    monkeypatch.setattr(
        frame_inference_service,
        "_requirement_loader",
        lambda camera_id, zone_id: PpeRequirementResponse(
            camera_id=camera_id,
            zone_id=zone_id,
            profile="hat_vest_v1",
            hat_required=False,
            vest_required=False,
            is_configured=False,
            updated_at=None,
        ),
    )
    result = frame_inference_service.infer(
        FrameInferenceRequest(
            image_data=jpeg_data_url(),
            zone_points=[
                {"x": 0.1, "y": 0.1},
                {"x": 0.9, "y": 0.1},
                {"x": 0.9, "y": 0.95},
                {"x": 0.1, "y": 0.95},
            ],
            machine_state="stopped",
        )
    )

    assert result.people[0].foot_point == [60, 100]
    assert result.people[0].inside_zone is True
    assert result.review_required is True
    assert result.result == "violate"
    assert result.snapshot_data.startswith("data:image/jpeg;base64,")


def test_inference_websocket_returns_empty_people(client, monkeypatch):
    monkeypatch.setattr(frame_inference_service, "_track_people", lambda session_id, frame: [])
    with client.websocket_connect("/api/v1/ws/inference") as websocket:
        configure_inference_websocket(websocket)
        body = send_inference_websocket_frame(websocket, frame_id=7, video_time=4.25)

    assert body["type"] == "inference_result"
    assert body["frame_id"] == 7
    assert body["video_time"] == 4.25
    assert body["people"] == []
    assert body["review_required"] is False


def test_inference_websocket_returns_person_outside_zone(client, monkeypatch):
    monkeypatch.setattr(
        frame_inference_service,
        "_track_people",
        lambda session_id, frame: [(40, 60, 40, 50, 0.91, 7)],
    )
    upper_zone = [
        {"x": 0.1, "y": 0.05},
        {"x": 0.9, "y": 0.05},
        {"x": 0.9, "y": 0.5},
        {"x": 0.1, "y": 0.5},
    ]
    with client.websocket_connect("/api/v1/ws/inference") as websocket:
        configure_inference_websocket(websocket, upper_zone)
        body = send_inference_websocket_frame(websocket)

    assert body["people"][0]["bbox"] == [40, 60, 80, 110]
    assert body["people"][0]["inside_zone"] is False
    assert body["review_required"] is False


def test_inference_websocket_requests_review_for_person_inside_zone(client, monkeypatch):
    monkeypatch.setattr(frame_inference_service, "_track_people", lambda session_id, frame: [(40, 10, 40, 90, 0.91, 7)])
    with client.websocket_connect("/api/v1/ws/inference") as websocket:
        configure_inference_websocket(websocket)
        body = send_inference_websocket_frame(websocket)

    assert body["people"][0]["bbox"] == [40, 10, 80, 100]
    assert body["people"][0]["inside_zone"] is True
    assert body["people"][0]["track_id"] == 7
    assert body["people"][0]["active_violations"][0]["rule_key"] == "zone_intrusion"
    assert body["review_required"] is True
    assert body["has_active_violation"] is True
    assert body["snapshot_data"].startswith("data:image/jpeg;base64,")


def test_inference_websocket_rejects_frame_before_configuration(client):
    with client.websocket_connect("/api/v1/ws/inference") as websocket:
        websocket.send_bytes(jpeg_bytes())
        body = websocket.receive_json()

    assert body["type"] == "error"
    assert body["code"] == "not_configured"


def test_inference_websocket_rejects_invalid_configuration(client):
    with client.websocket_connect("/api/v1/ws/inference") as websocket:
        websocket.send_json(
            {
                "type": "configure",
                "zone_points": [
                    {"x": 0.1, "y": 0.1},
                    {"x": 0.9, "y": 0.1},
                    {"x": 0.9, "y": 0.9},
                ],
                "machine_state": "running",
            }
        )
        body = websocket.receive_json()

    assert body["type"] == "error"
    assert body["code"] == "validation_error"


def test_inference_websocket_rejects_invalid_jpeg(client):
    with client.websocket_connect("/api/v1/ws/inference") as websocket:
        configure_inference_websocket(websocket)
        body = send_inference_websocket_frame(websocket, frame=b"not-a-jpeg")

    assert body["type"] == "error"
    assert body["code"] == "invalid_frame"


def test_inference_websocket_deduplicates_a_continuous_violation(client, monkeypatch):
    monkeypatch.setattr(frame_inference_service, "_track_people", lambda session_id, frame: [(40, 10, 40, 90, 0.91, 7)])
    with client.websocket_connect("/api/v1/ws/inference") as websocket:
        configure_inference_websocket(websocket)
        first = send_inference_websocket_frame(websocket, frame_id=1)
        repeated = send_inference_websocket_frame(websocket, frame_id=2)

    assert first["review_required"] is True
    assert repeated["review_required"] is False
    assert repeated["result"] == "violate"
    assert (
        repeated["people"][0]["active_violations"][0]["occurrence_id"]
        == first["people"][0]["active_violations"][0]["occurrence_id"]
    )


def test_inference_websocket_rejects_stale_frame_id(client, monkeypatch):
    monkeypatch.setattr(frame_inference_service, "_track_people", lambda session_id, frame: [])
    with client.websocket_connect("/api/v1/ws/inference") as websocket:
        configure_inference_websocket(websocket)
        assert send_inference_websocket_frame(websocket, frame_id=4)["type"] == "inference_result"
        stale = send_inference_websocket_frame(websocket, frame_id=4)

    assert stale["type"] == "error"
    assert stale["code"] == "stale_frame"
