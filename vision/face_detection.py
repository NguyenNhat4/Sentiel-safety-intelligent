from __future__ import annotations

from collections.abc import Callable
from threading import Lock
from typing import Any, Protocol, TypedDict

import cv2
import numpy as np


class FaceDetection(TypedDict):
    bbox: list[int]
    confidence: float


class FaceDetector(Protocol):
    def preload(self) -> None: ...

    def detect(self, frame: np.ndarray) -> list[FaceDetection]: ...


DetectorFactory = Callable[[str, float, float, int], Any]


class YuNetFaceDetector:
    """Thread-safe OpenCV YuNet wrapper returning bounded-ready xyxy boxes."""

    def __init__(
        self,
        model_path: str,
        *,
        score_threshold: float = 0.6,
        nms_threshold: float = 0.3,
        top_k: int = 5000,
        detector_factory: DetectorFactory | None = None,
    ) -> None:
        self._model_path = model_path
        self._score_threshold = score_threshold
        self._nms_threshold = nms_threshold
        self._top_k = top_k
        self._detector_factory = detector_factory or self._create_detector
        self._detector: Any | None = None
        self._lock = Lock()

    def preload(self) -> None:
        with self._lock:
            self._load_detector()

    def detect(self, frame: np.ndarray) -> list[FaceDetection]:
        if frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError("face detector input must be a three-channel image")
        height, width = frame.shape[:2]
        with self._lock:
            detector = self._load_detector()
            detector.setInputSize((width, height))
            _, faces = detector.detect(frame)

        if faces is None:
            return []

        detections: list[FaceDetection] = []
        for face in faces:
            if len(face) < 15:
                continue
            x, y, face_width, face_height = (float(value) for value in face[:4])
            if face_width <= 0 or face_height <= 0:
                continue
            detections.append(
                {
                    "bbox": [
                        round(x),
                        round(y),
                        round(x + face_width),
                        round(y + face_height),
                    ],
                    "confidence": float(face[14]),
                }
            )
        return detections

    def _load_detector(self):
        if self._detector is None:
            self._detector = self._detector_factory(
                self._model_path,
                self._score_threshold,
                self._nms_threshold,
                self._top_k,
            )
        return self._detector

    @staticmethod
    def _create_detector(model_path: str, score_threshold: float, nms_threshold: float, top_k: int):
        return cv2.FaceDetectorYN_create(
            model_path,
            "",
            (320, 320),
            score_threshold,
            nms_threshold,
            top_k,
            cv2.dnn.DNN_BACKEND_OPENCV,
            cv2.dnn.DNN_TARGET_CPU,
        )
