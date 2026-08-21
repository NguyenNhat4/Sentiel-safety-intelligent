import logging
import threading
import time
from collections.abc import Callable
from typing import Protocol

import numpy as np

logger = logging.getLogger(__name__)


class FrameSource(Protocol):
    def read_sample(self) -> np.ndarray | None: ...

    def close(self) -> None: ...


ProcessFrame = Callable[[str, str, int, float, np.ndarray], dict]
PublishResult = Callable[[dict], None]


class CameraInferenceWorker:
    """Own one camera source and publish its latest server-side inference."""

    def __init__(
        self,
        camera_id: str,
        stream_camera_id: str,
        *,
        source: FrameSource,
        process_frame: ProcessFrame,
        publish: PublishResult,
        retry_delay_seconds: float = 0.25,
    ) -> None:
        self.camera_id = camera_id
        self.stream_camera_id = stream_camera_id
        self._source = source
        self._process_frame = process_frame
        self._publish = publish
        self._retry_delay_seconds = retry_delay_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def is_alive(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> None:
        if self.is_alive:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name=f"camera-inference-{self.camera_id}",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._source.close()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=2.0)
        self._thread = None

    def _run(self) -> None:
        frame_id = 0
        while not self._stop.is_set():
            try:
                frame = self._source.read_sample()
                if frame is None:
                    self._stop.wait(self._retry_delay_seconds)
                    continue
                frame_id += 1
                captured_at = time.time()
                result = self._process_frame(
                    self.camera_id,
                    self.stream_camera_id,
                    frame_id,
                    captured_at,
                    frame,
                )
                self._publish(
                    {
                        **result,
                        "camera_id": self.camera_id,
                        "stream_camera_id": self.stream_camera_id,
                        "frame_id": frame_id,
                        "source_timestamp_ms": round(captured_at * 1000),
                        "frame_width": int(frame.shape[1]),
                        "frame_height": int(frame.shape[0]),
                    }
                )
            except Exception:
                logger.exception("Camera inference worker failed for camera %s", self.camera_id)
                self._stop.wait(self._retry_delay_seconds)
