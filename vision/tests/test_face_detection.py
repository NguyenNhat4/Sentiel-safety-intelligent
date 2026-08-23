from pathlib import Path

import numpy as np
import pytest

from vision.face_detection import YuNetFaceDetector


class FakeOpenCvDetector:
    def __init__(self, faces):
        self.faces = faces
        self.input_sizes: list[tuple[int, int]] = []
        self.detect_calls = 0

    def setInputSize(self, size: tuple[int, int]) -> None:  # noqa: N802 - OpenCV API compatibility
        self.input_sizes.append(size)

    def detect(self, frame: np.ndarray):
        self.detect_calls += 1
        return 1, self.faces


def test_yunet_wrapper_converts_xywh_and_reuses_one_detector():
    faces = np.array(
        [[10.4, 20.4, 30.2, 40.2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.87]],
        dtype=np.float32,
    )
    fake = FakeOpenCvDetector(faces)
    factory_calls = []

    def factory(model_path: str, score_threshold: float, nms_threshold: float, top_k: int):
        factory_calls.append((model_path, score_threshold, nms_threshold, top_k))
        return fake

    detector = YuNetFaceDetector("yunet.onnx", detector_factory=factory)
    frame = np.zeros((100, 120, 3), dtype=np.uint8)

    first = detector.detect(frame)
    second = detector.detect(frame)

    assert first == [{"bbox": [10, 20, 41, 61], "confidence": pytest.approx(0.87)}]
    assert second == first
    assert factory_calls == [("yunet.onnx", 0.6, 0.3, 5000)]
    assert fake.input_sizes == [(120, 100), (120, 100)]
    assert fake.detect_calls == 2


def test_yunet_wrapper_returns_empty_when_opencv_has_no_faces():
    fake = FakeOpenCvDetector(None)
    detector = YuNetFaceDetector("yunet.onnx", detector_factory=lambda *_: fake)

    assert detector.detect(np.zeros((50, 60, 3), dtype=np.uint8)) == []


def test_project_yunet_artifact_loads_with_opencv_backend():
    model_path = Path("models/face_detection_yunet_2023mar.onnx")
    detector = YuNetFaceDetector(str(model_path))

    detector.preload()

    assert detector.detect(np.zeros((120, 160, 3), dtype=np.uint8)) == []
