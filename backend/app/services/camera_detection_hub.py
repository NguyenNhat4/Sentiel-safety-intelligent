import asyncio
import threading
from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class CameraDetectionSubscription:
    queue: asyncio.Queue[dict]
    _close: Callable[[], None]

    def close(self) -> None:
        self._close()


class CameraDetectionHub:
    """Fan out metadata only; slow viewers receive the latest camera result."""

    def __init__(self, *, queue_size: int = 4) -> None:
        self._queue_size = queue_size
        self._subscribers: dict[int, tuple[set[str], asyncio.AbstractEventLoop, asyncio.Queue[dict]]] = {}
        self._next_id = 0
        self._lock = threading.Lock()

    @property
    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscribers)

    def subscribe(self, camera_ids: set[str]) -> CameraDetectionSubscription:
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=self._queue_size)
        with self._lock:
            subscription_id = self._next_id
            self._next_id += 1
            self._subscribers[subscription_id] = (set(camera_ids), loop, queue)

        def close() -> None:
            with self._lock:
                self._subscribers.pop(subscription_id, None)

        return CameraDetectionSubscription(queue=queue, _close=close)

    def publish(self, payload: dict) -> None:
        camera_id = payload.get("camera_id")
        with self._lock:
            subscribers = list(self._subscribers.values())
        for camera_ids, loop, queue in subscribers:
            if camera_id in camera_ids:
                loop.call_soon_threadsafe(self._enqueue_latest, queue, payload)

    @staticmethod
    def _enqueue_latest(queue: asyncio.Queue[dict], payload: dict) -> None:
        if queue.full():
            queue.get_nowait()
        queue.put_nowait(payload)


camera_detection_hub = CameraDetectionHub()
