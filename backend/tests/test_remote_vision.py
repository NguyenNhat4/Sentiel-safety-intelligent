import json
from uuid import UUID

import httpx
import numpy as np
import pytest

from backend.app.integrations.remote_vision import RemoteVisionAdapter, RemoteVisionError


def response_payload(request_id: str) -> dict:
    return {
        "contract_version": "safety_vision_v1",
        "request_id": request_id,
        "model_version": "test-model",
        "canonical_people": [{"bbox": [10, 20, 30, 40], "confidence": 0.95, "track_id": 7}],
        "people": [
            {
                "hat": {"status": "present", "confidence": 0.91},
                "vest": {"status": "unknown", "confidence": None},
            }
        ],
        "detections": [
            {
                "class_id": 3,
                "class_name": "person",
                "bbox": [10, 20, 40, 60],
                "confidence": 0.95,
                "person_index": 0,
            }
        ],
    }


def empty_tracking_state() -> dict:
    return {
        "schema_version": "bytetrack_ppe_state_v1",
        "tracker": {"frame_id": 0, "last_track_id": 0, "tracked": [], "lost": []},
        "smoother": {"temporal_frames": 3, "tracks": []},
    }


def response_payload_v2(request_id: str, session_id: str, frame_id: int, revision: int) -> dict:
    return {
        **response_payload(request_id),
        "contract_version": "safety_vision_v2",
        "monitoring_session_id": session_id,
        "frame_id": frame_id,
        "base_state_revision": revision,
        "tracking_state": empty_tracking_state(),
    }


def test_remote_adapter_sends_jpeg_and_adapts_versioned_response():
    seen_request_id = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_request_id
        assert request.method == "POST"
        assert request.url.path == "/v1/infer"
        assert request.headers["authorization"] == "Bearer secret-token"
        assert request.headers["content-type"].startswith("multipart/form-data;")
        body = request.read()
        assert b'name="monitoring_session_id"' in body
        assert b"monitor-1" in body
        assert b"image/jpeg" in body
        marker = b'name="request_id"\r\n\r\n'
        seen_request_id = body.split(marker, 1)[1].split(b"\r\n", 1)[0].decode()
        UUID(seen_request_id)
        return httpx.Response(200, json=response_payload(seen_request_id))

    client = httpx.Client(base_url="https://vision.example", transport=httpx.MockTransport(handler))
    adapter = RemoteVisionAdapter(
        base_url="https://vision.example",
        api_key="secret-token",
        timeout_seconds=2.0,
        client=client,
    )

    result = adapter.analyze(np.zeros((80, 120, 3), dtype=np.uint8), "monitor-1", 123.0)

    assert seen_request_id is not None
    assert result == {
        "canonical_people": [(10, 20, 30, 40, 0.95, 7)],
        "people": [
            {
                "hat": {"status": "present", "confidence": 0.91},
                "vest": {"status": "unknown", "confidence": None},
            }
        ],
        "detections": [
            {
                "class_id": 3,
                "class_name": "person",
                "bbox": [10, 20, 40, 60],
                "confidence": 0.95,
                "person_index": 0,
            }
        ],
    }


def test_remote_adapter_rejects_malformed_contract():
    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read()
        marker = b'name="request_id"\r\n\r\n'
        request_id = body.split(marker, 1)[1].split(b"\r\n", 1)[0].decode()
        payload = response_payload(request_id)
        payload["detections"][0]["class_name"] = "forklift"
        return httpx.Response(200, content=json.dumps(payload), headers={"content-type": "application/json"})

    client = httpx.Client(base_url="https://vision.example", transport=httpx.MockTransport(handler))
    adapter = RemoteVisionAdapter(
        base_url="https://vision.example",
        api_key="secret-token",
        timeout_seconds=2.0,
        client=client,
    )

    with pytest.raises(RemoteVisionError, match="invalid response contract"):
        adapter.analyze(np.zeros((20, 20, 3), dtype=np.uint8), None, 123.0)


@pytest.mark.parametrize(
    ("field", "bbox"),
    [
        ("canonical_people", [-1, 20, 30, 40]),
        ("detections", [40, 20, 10, 60]),
    ],
)
def test_remote_adapter_rejects_invalid_bounding_boxes(field, bbox):
    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read()
        marker = b'name="request_id"\r\n\r\n'
        request_id = body.split(marker, 1)[1].split(b"\r\n", 1)[0].decode()
        payload = response_payload(request_id)
        payload[field][0]["bbox"] = bbox
        return httpx.Response(200, json=payload)

    client = httpx.Client(base_url="https://vision.example", transport=httpx.MockTransport(handler))
    adapter = RemoteVisionAdapter(
        base_url="https://vision.example",
        api_key="secret-token",
        timeout_seconds=2.0,
        client=client,
    )

    with pytest.raises(RemoteVisionError, match="invalid response contract"):
        adapter.analyze(np.zeros((20, 20, 3), dtype=np.uint8), None, 123.0)


def test_remote_adapter_fails_closed_on_http_error():
    client = httpx.Client(
        base_url="https://vision.example",
        transport=httpx.MockTransport(lambda request: httpx.Response(503, text="provider details")),
    )
    adapter = RemoteVisionAdapter(
        base_url="https://vision.example",
        api_key="secret-token",
        timeout_seconds=2.0,
        client=client,
    )

    with pytest.raises(RemoteVisionError, match="request failed") as exc_info:
        adapter.analyze(np.zeros((20, 20, 3), dtype=np.uint8), None, 123.0)

    assert "provider details" not in str(exc_info.value)


def test_remote_adapter_preload_checks_health_contract():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/ping"
        return httpx.Response(
            200,
            json={
                "status": "healthy",
                "contract_version": "safety_vision_v1",
                "model_version": "test-model",
            },
        )

    client = httpx.Client(base_url="https://vision.example", transport=httpx.MockTransport(handler))
    adapter = RemoteVisionAdapter(
        base_url="https://vision.example",
        api_key="secret-token",
        timeout_seconds=2.0,
        client=client,
    )

    adapter.preload()


def test_remote_adapter_v2_transfers_and_correlates_tracking_state():
    session_id = "3cddfe85-9428-44d7-afbf-0cd9e5fc0640"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/infer"
        body = request.read()
        assert b'name="frame_id"\r\n\r\n7' in body
        assert b'name="state_revision"\r\n\r\n3' in body
        assert b'"schema_version":"bytetrack_ppe_state_v1"' in body
        marker = b'name="request_id"\r\n\r\n'
        request_id = body.split(marker, 1)[1].split(b"\r\n", 1)[0].decode()
        return httpx.Response(200, json=response_payload_v2(request_id, session_id, 7, 3))

    client = httpx.Client(base_url="https://vision.example", transport=httpx.MockTransport(handler))
    adapter = RemoteVisionAdapter(
        base_url="https://vision.example",
        api_key="secret-token",
        timeout_seconds=2.0,
        client=client,
    )

    result, state = adapter.analyze_with_state(
        np.zeros((80, 120, 3), dtype=np.uint8),
        monitoring_session_id=session_id,
        frame_id=7,
        state_revision=3,
        tracking_state=empty_tracking_state(),
    )

    assert result["canonical_people"] == [(10, 20, 30, 40, 0.95, 7)]
    assert state == empty_tracking_state()


def test_remote_adapter_v2_rejects_mismatched_frame_correlation():
    session_id = "3cddfe85-9428-44d7-afbf-0cd9e5fc0640"

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read()
        marker = b'name="request_id"\r\n\r\n'
        request_id = body.split(marker, 1)[1].split(b"\r\n", 1)[0].decode()
        return httpx.Response(200, json=response_payload_v2(request_id, session_id, 8, 3))

    client = httpx.Client(base_url="https://vision.example", transport=httpx.MockTransport(handler))
    adapter = RemoteVisionAdapter(
        base_url="https://vision.example",
        api_key="secret-token",
        timeout_seconds=2.0,
        client=client,
    )

    with pytest.raises(RemoteVisionError, match="mismatched frame correlation"):
        adapter.analyze_with_state(
            np.zeros((20, 20, 3), dtype=np.uint8),
            monitoring_session_id=session_id,
            frame_id=7,
            state_revision=3,
            tracking_state=empty_tracking_state(),
        )


def test_remote_adapter_v2_preload_checks_v2_health_contract():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/ping"
        return httpx.Response(
            200,
            json={
                "status": "healthy",
                "contract_version": "safety_vision_v2",
                "model_version": "test-model",
            },
        )

    client = httpx.Client(base_url="https://vision.example", transport=httpx.MockTransport(handler))
    adapter = RemoteVisionAdapter(
        base_url="https://vision.example",
        api_key="secret-token",
        timeout_seconds=2.0,
        contract_version="safety_vision_v2",
        client=client,
    )

    adapter.preload()
