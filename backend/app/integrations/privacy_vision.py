from functools import cache

import numpy as np

from vision.api import ModelDetection, PrivacyRedactionFacade, PrivacyRedactionResult, SnapshotPerson


class PrivacyVisionAdapter:
    """Backend adapter for model-independent, fail-closed snapshot redaction."""

    def __init__(self) -> None:
        self._facade = PrivacyRedactionFacade()

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
def get_privacy_vision_adapter() -> PrivacyVisionAdapter:
    return PrivacyVisionAdapter()
