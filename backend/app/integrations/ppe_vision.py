from collections.abc import Callable
from functools import cache

import numpy as np

from vision.api import PpeVisionFacade, PpeVisionResult, SafetyVisionResult


class PpeVisionAdapter:
    """Backend adapter for unified person/tracking/PPE Safety inference."""

    def __init__(
        self,
        model_path: str,
        person_confidence_threshold: float = 0.6,
        ppe_confidence_threshold: float = 0.2,
        inference_image_size: int = 960,
        temporal_frames: int = 10,
    ) -> None:
        self._facade = PpeVisionFacade(
            model_path,
            confidence_threshold=ppe_confidence_threshold,
            person_confidence_threshold=person_confidence_threshold,
            inference_image_size=inference_image_size,
            temporal_frames=temporal_frames,
        )

    def observe(
        self,
        frame: np.ndarray,
        people: list[tuple[int, int, int, int, float]],
    ) -> PpeVisionResult:
        return self._facade.observe(frame, people)

    def analyze(
        self,
        frame: np.ndarray,
        monitoring_session_id: str | None,
        now: float,
    ) -> SafetyVisionResult:
        return self._facade.analyze(frame, monitoring_session_id, now=now)

    def preload(self) -> None:
        self._facade.preload()

    def end_session(self, monitoring_session_id: str) -> None:
        self._facade.end_session(monitoring_session_id)


@cache
def get_ppe_vision_adapter(
    model_path: str,
    person_confidence_threshold: float = 0.6,
    ppe_confidence_threshold: float = 0.2,
    inference_image_size: int = 960,
    temporal_frames: int = 10,
) -> PpeVisionAdapter:
    """Reuse the validated three-class PPE facade for frame inference."""
    return PpeVisionAdapter(
        model_path,
        person_confidence_threshold=person_confidence_threshold,
        ppe_confidence_threshold=ppe_confidence_threshold,
        inference_image_size=inference_image_size,
        temporal_frames=temporal_frames,
    )


PpeObserver = Callable[
    [np.ndarray, list[tuple[int, int, int, int, float]]],
    PpeVisionResult,
]

SafetyVisionAnalyzer = Callable[[np.ndarray, str | None, float], SafetyVisionResult]
