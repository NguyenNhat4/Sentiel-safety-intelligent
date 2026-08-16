from functools import cache

import numpy as np

from backend.app.core.config import get_settings
from vision.api import ModelDetection, PrivacyRedactionFacade, PrivacyRedactionResult, SnapshotPerson


class PrivacyVisionAdapter:
    """Backend adapter for YuNet-first, fail-closed snapshot redaction."""

    def __init__(self, model_path: str, score_threshold: float, face_margin_ratio: float) -> None:
        self._facade = PrivacyRedactionFacade(
            model_path,
            score_threshold=score_threshold,
            face_margin_ratio=face_margin_ratio,
        )

    def preload(self) -> None:
        self._facade.preload()

    def redact_snapshot(
        self,
        frame: np.ndarray,
        people: list[SnapshotPerson],
    ) -> PrivacyRedactionResult:
        return self._facade.redact_snapshot(frame, people)

    def annotate_snapshot(
        self,
        frame: np.ndarray,
        people: list[SnapshotPerson],
        detections: list[ModelDetection],
    ) -> np.ndarray:
        return self._facade.annotate_snapshot(frame, people, detections)


@cache
def get_privacy_vision_adapter(
    model_path: str,
    score_threshold: float,
    face_margin_ratio: float,
) -> PrivacyVisionAdapter:
    return PrivacyVisionAdapter(model_path, score_threshold, face_margin_ratio)


def get_configured_privacy_vision_adapter() -> PrivacyVisionAdapter:
    settings = get_settings()
    return get_privacy_vision_adapter(
        settings.face_detector_model_path,
        settings.face_detector_score_threshold,
        settings.face_redaction_margin_ratio,
    )
