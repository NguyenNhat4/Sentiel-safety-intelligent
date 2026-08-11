import time

import numpy as np

from vision.api import PersonTrackingFacade, TrackedPerson


class PersonTrackingAdapter:
    """Backend adapter for session-isolated person tracking."""

    def __init__(self, model_path: str) -> None:
        self._facade = PersonTrackingFacade(model_path)

    def track(self, session_id: str, frame: np.ndarray) -> list[TrackedPerson]:
        return self._facade.track(session_id, frame, now=time.monotonic())
