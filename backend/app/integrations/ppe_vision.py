from collections.abc import Callable

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


PpeObserver = Callable[
    [np.ndarray, list[tuple[int, int, int, int, float]]],
    PpeVisionResult,
]
