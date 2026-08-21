import re
import time
from collections.abc import Callable

import cv2
import numpy as np


class InvalidMediaSourceError(ValueError):
    pass


_CAMERA_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def build_rtsp_camera_url(origin: str, stream_camera_id: str) -> str:
    """Derive a MediaMTX reader URL without accepting arbitrary client URLs."""
    if not origin.startswith(("rtsp://", "rtsps://")):
        raise InvalidMediaSourceError("RTSP origin must use rtsp:// or rtsps://")
    if not _CAMERA_ID.fullmatch(stream_camera_id):
        raise InvalidMediaSourceError("Invalid stream camera ID")
    return f"{origin.rstrip('/')}/cameras/{stream_camera_id}"


class RtspFrameSource:
    """Reconnectable OpenCV RTSP reader with monotonic sampling backpressure."""

    def __init__(
        self,
        url: str,
        *,
        max_fps: float = 2.0,
        capture_factory: Callable[[str], cv2.VideoCapture] = cv2.VideoCapture,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_fps <= 0:
            raise ValueError("max_fps must be positive")
        self._url = url
        self._minimum_interval = 1.0 / max_fps
        self._capture_factory = capture_factory
        self._monotonic = monotonic
        self._capture: cv2.VideoCapture | None = None
        self._last_sample_at: float | None = None

    def read_sample(self) -> np.ndarray | None:
        now = self._monotonic()
        if self._last_sample_at is not None and now - self._last_sample_at < self._minimum_interval:
            return None
        capture = self._ensure_capture()
        ok, frame = capture.read()
        if not ok or frame is None:
            self.close()
            return None
        self._last_sample_at = now
        return frame

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def _ensure_capture(self) -> cv2.VideoCapture:
        if self._capture is None:
            capture = self._capture_factory(self._url)
            if not capture.isOpened():
                capture.release()
                raise ConnectionError("RTSP source could not be opened")
            self._capture = capture
        return self._capture
