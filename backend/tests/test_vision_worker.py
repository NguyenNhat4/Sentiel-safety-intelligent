import json
from uuid import uuid4

import cv2
import numpy as np
import pytest
import torch
from fastapi.testclient import TestClient

from backend.app import vision_worker
from backend.app.vision_worker import MAX_IMAGE_BYTES, MAX_TRACKING_STATE_BYTES, create_app


class FakeVisionAnalyzer:
    def __init__(self) -> None:
        self.preload_calls = 0
        self.analyze_calls: list[tuple[tuple[int, ...], str | None]] = []

    def preload(self) -> None:
        self.preload_calls += 1

    def analyze(self, frame: np.ndarray, monitoring_session_id: str | None, now: float):
        assert now > 0
        self.analyze_calls.append((frame.shape, monitoring_session_id))
        return {
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
                },
                {
                    "class_id": 0,
                    "class_name": "hat",
                    "bbox": [15, 22, 30, 35],
                    "confidence": 0.91,
                    "person_index": 0,
                },
            ],
        }


def jpeg_bytes() -> bytes:
    encoded, buffer = cv2.imencode(".jpg", np.zeros((80, 120, 3), dtype=np.uint8))
    assert encoded
    return buffer.tobytes()


def empty_tracking_state() -> dict:
    return {
        "schema_version": "bytetrack_ppe_state_v1",
        "tracker": {"frame_id": 0, "last_track_id": 0, "tracked": [], "lost": []},
        "smoother": {"temporal_frames": 3, "tracks": []},
    }


def test_worker_preloads_model_and_returns_versioned_inference_contract():
    analyzer = FakeVisionAnalyzer()
    request_id = uuid4()

    with TestClient(create_app(analyzer=analyzer, model_version="test-model")) as client:
        assert client.get("/ping").json() == {
            "status": "healthy",
            "contract_version": "safety_vision_v1",
            "model_version": "test-model",
        }
        response = client.post(
            "/v1/infer",
            data={"request_id": str(request_id), "monitoring_session_id": "monitor-1"},
            files={"image": ("frame.jpg", jpeg_bytes(), "image/jpeg")},
        )

    assert response.status_code == 200
    assert analyzer.preload_calls == 1
    assert analyzer.analyze_calls == [((80, 120, 3), "monitor-1")]
    assert response.json() == {
        "contract_version": "safety_vision_v1",
        "request_id": str(request_id),
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
            },
            {
                "class_id": 0,
                "class_name": "hat",
                "bbox": [15, 22, 30, 35],
                "confidence": 0.91,
                "person_index": 0,
            },
        ],
    }


def test_worker_rejects_invalid_jpeg_without_running_inference():
    analyzer = FakeVisionAnalyzer()

    with TestClient(create_app(analyzer=analyzer, model_version="test-model")) as client:
        response = client.post(
            "/v1/infer",
            data={"request_id": str(uuid4())},
            files={"image": ("frame.jpg", b"not-a-jpeg", "image/jpeg")},
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid JPEG image"}
    assert analyzer.analyze_calls == []


def test_worker_rejects_oversized_image_without_loading_it_all_into_memory():
    analyzer = FakeVisionAnalyzer()

    with TestClient(create_app(analyzer=analyzer, model_version="test-model")) as client:
        response = client.post(
            "/v1/infer",
            data={"request_id": str(uuid4())},
            files={"image": ("frame.jpg", b"x" * (MAX_IMAGE_BYTES + 1), "image/jpeg")},
        )

    assert response.status_code == 413
    assert response.json() == {"detail": "JPEG image exceeds 8 MiB limit"}
    assert analyzer.analyze_calls == []


def test_worker_can_require_bearer_auth_for_direct_deployments():
    analyzer = FakeVisionAnalyzer()

    with TestClient(
        create_app(analyzer=analyzer, model_version="test-model", worker_api_key="worker-secret")
    ) as client:
        denied = client.post(
            "/v1/infer",
            data={"request_id": str(uuid4())},
            files={"image": ("frame.jpg", jpeg_bytes(), "image/jpeg")},
        )
        allowed = client.post(
            "/v1/infer",
            headers={"Authorization": "Bearer worker-secret"},
            data={"request_id": str(uuid4())},
            files={"image": ("frame.jpg", jpeg_bytes(), "image/jpeg")},
        )

    assert denied.status_code == 401
    assert allowed.status_code == 200
    assert len(analyzer.analyze_calls) == 1


def test_worker_fails_startup_when_cuda_is_required_but_unavailable(monkeypatch):
    analyzer = FakeVisionAnalyzer()
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)

    with pytest.raises(RuntimeError, match="cuda:0"):
        with TestClient(create_app(analyzer=analyzer, compute_device="cuda:0")):
            pass

    assert analyzer.preload_calls == 0


def test_worker_constructs_facade_with_device_from_environment(monkeypatch):
    captured = {}

    class CapturingAnalyzer(FakeVisionAnalyzer):
        def __init__(self, model_path: str, *, device: str | None = None) -> None:
            super().__init__()
            captured.update(model_path=model_path, device=device)

    monkeypatch.setenv("VISION_DEVICE", "cuda:0")
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(vision_worker, "PpeVisionFacade", CapturingAnalyzer)

    with TestClient(vision_worker.create_app(model_version="gpu-test")) as client:
        assert client.get("/ping").status_code == 200

    assert captured == {"model_path": "models/yolo11m_safety.pt", "device": "cuda:0"}


def test_v2_worker_returns_correlated_result_and_next_tracking_state():
    class PortableAnalyzer(FakeVisionAnalyzer):
        def __init__(self):
            super().__init__()
            self.portable_calls = []

        def analyze_with_state(self, frame, state):
            self.portable_calls.append((frame.shape, state))
            return self.analyze(frame, None, 1.0), empty_tracking_state()

    analyzer = PortableAnalyzer()
    request_id = uuid4()
    session_id = uuid4()

    with TestClient(create_app(analyzer=analyzer, model_version="test-model")) as client:
        assert client.get("/v2/ping").json() == {
            "status": "healthy",
            "contract_version": "safety_vision_v2",
            "model_version": "test-model",
        }
        response = client.post(
            "/v2/infer",
            data={
                "request_id": str(request_id),
                "monitoring_session_id": str(session_id),
                "frame_id": "7",
                "state_revision": "3",
                "tracking_state": json.dumps(empty_tracking_state()),
            },
            files={"image": ("frame.jpg", jpeg_bytes(), "image/jpeg")},
        )

    assert response.status_code == 200
    assert analyzer.portable_calls == [((80, 120, 3), empty_tracking_state())]
    assert response.json()["contract_version"] == "safety_vision_v2"
    assert response.json()["request_id"] == str(request_id)
    assert response.json()["monitoring_session_id"] == str(session_id)
    assert response.json()["frame_id"] == 7
    assert response.json()["base_state_revision"] == 3
    assert response.json()["tracking_state"] == empty_tracking_state()


def test_v2_worker_accepts_initial_revision_without_tracking_state():
    class PortableAnalyzer(FakeVisionAnalyzer):
        def analyze_with_state(self, frame, state):
            assert state is None
            return self.analyze(frame, None, 1.0), empty_tracking_state()

    analyzer = PortableAnalyzer()
    with TestClient(create_app(analyzer=analyzer, model_version="test-model")) as client:
        response = client.post(
            "/v2/infer",
            data={
                "request_id": str(uuid4()),
                "monitoring_session_id": str(uuid4()),
                "frame_id": "1",
                "state_revision": "0",
            },
            files={"image": ("frame.jpg", jpeg_bytes(), "image/jpeg")},
        )

    assert response.status_code == 200


def test_v2_worker_requires_same_bearer_authentication_as_v1():
    analyzer = FakeVisionAnalyzer()
    with TestClient(create_app(analyzer=analyzer, model_version="test-model", worker_api_key="secret-token")) as client:
        response = client.post(
            "/v2/infer",
            data={
                "request_id": str(uuid4()),
                "monitoring_session_id": str(uuid4()),
                "frame_id": "1",
                "state_revision": "0",
            },
            files={"image": ("frame.jpg", jpeg_bytes(), "image/jpeg")},
        )

    assert response.status_code == 401
    assert analyzer.analyze_calls == []


def test_v2_worker_rejects_oversized_state_before_inference():
    analyzer = FakeVisionAnalyzer()

    with TestClient(create_app(analyzer=analyzer, model_version="test-model")) as client:
        response = client.post(
            "/v2/infer",
            data={
                "request_id": str(uuid4()),
                "monitoring_session_id": str(uuid4()),
                "frame_id": "1",
                "state_revision": "1",
                "tracking_state": "x" * (MAX_TRACKING_STATE_BYTES + 1),
            },
            files={"image": ("frame.jpg", jpeg_bytes(), "image/jpeg")},
        )

    assert response.status_code == 413
    assert analyzer.analyze_calls == []


def test_v2_worker_rejects_non_finite_kalman_state():
    analyzer = FakeVisionAnalyzer()
    state = empty_tracking_state()
    state["tracker"]["tracked"] = [
        {
            "track_id": 1,
            "tlwh": [0.0, 0.0, 10.0, 20.0],
            "mean": [float("nan")] + [0.0] * 7,
            "covariance": [[0.0] * 8 for _ in range(8)],
            "is_activated": True,
            "state": 1,
            "score": 0.9,
            "start_frame": 1,
            "frame_id": 1,
            "tracklet_len": 0,
            "class_id": 3,
            "detection_index": 0,
            "angle": None,
        }
    ]
    state["tracker"]["last_track_id"] = 1

    with TestClient(create_app(analyzer=analyzer, model_version="test-model")) as client:
        response = client.post(
            "/v2/infer",
            data={
                "request_id": str(uuid4()),
                "monitoring_session_id": str(uuid4()),
                "frame_id": "2",
                "state_revision": "1",
                "tracking_state": json.dumps(state),
            },
            files={"image": ("frame.jpg", jpeg_bytes(), "image/jpeg")},
        )

    assert response.status_code == 422
    assert analyzer.analyze_calls == []
