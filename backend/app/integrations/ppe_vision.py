from collections.abc import Callable
from functools import cache

import numpy as np

from vision.api import PpeVisionFacade, PpeVisionResult, PrivacyRedactionResult


class PpeVisionAdapter:
    """Backend-facing adapter for the public PPE vision facade."""

    def __init__(self, model_path: str) -> None:
        self._facade = PpeVisionFacade(model_path)

    def observe(
        self,
        frame: np.ndarray,
        people: list[tuple[int, int, int, int, float]],
    ) -> PpeVisionResult:
        return self._facade.observe(frame, people)

    def preload(self) -> None:
        self._facade.preload()

    def redact_snapshot(self, frame: np.ndarray) -> PrivacyRedactionResult:
        return self._facade.redact_snapshot(frame)


@cache
def get_ppe_vision_adapter(model_path: str) -> PpeVisionAdapter:
    """Reuse the SH17 facade for frame inference and on-demand snapshot redaction."""
    return PpeVisionAdapter(model_path)


PpeObserver = Callable[
    [np.ndarray, list[tuple[int, int, int, int, float]]],
    PpeVisionResult,
]
