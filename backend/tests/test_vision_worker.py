from uuid import uuid4

import cv2
import numpy as np
from fastapi.testclient import TestClient

from backend.app.vision_worker import MAX_IMAGE_BYTES, create_app


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
