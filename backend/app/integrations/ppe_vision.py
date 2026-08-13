from collections.abc import Callable
from functools import cache

import numpy as np

from vision.api import PpeVisionFacade, PpeVisionResult


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


@cache
def get_ppe_vision_adapter(model_path: str) -> PpeVisionAdapter:
    """Reuse the validated three-class PPE facade for frame inference."""
    return PpeVisionAdapter(model_path)


PpeObserver = Callable[
    [np.ndarray, list[tuple[int, int, int, int, float]]],
    PpeVisionResult,
]
