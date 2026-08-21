from collections.abc import Callable, Iterable
from typing import Protocol

from backend.app.schemas.stream_configuration import StreamMapping


class CameraInferenceWorker(Protocol):
    camera_id: str
    stream_camera_id: str

    def start(self) -> None: ...

    def stop(self) -> None: ...


WorkerFactory = Callable[[str, str], CameraInferenceWorker]


class CameraInferenceSupervisor:
    """Reconcile persisted camera mappings to exactly one inference worker each."""

    def __init__(self, worker_factory: WorkerFactory) -> None:
        self._worker_factory = worker_factory
        self._workers: dict[str, CameraInferenceWorker] = {}

    @property
    def active_camera_ids(self) -> set[str]:
        return set(self._workers)

    def reconcile(self, mappings: Iterable[StreamMapping]) -> None:
        desired = {mapping.camera_id: mapping.stream_camera_id for mapping in mappings}

        for camera_id, worker in list(self._workers.items()):
            if desired.get(camera_id) != worker.stream_camera_id:
                worker.stop()
                del self._workers[camera_id]

        for camera_id, stream_camera_id in desired.items():
            if camera_id in self._workers:
                continue
            worker = self._worker_factory(camera_id, stream_camera_id)
            worker.start()
            self._workers[camera_id] = worker

    def stop_all(self) -> None:
        for worker in self._workers.values():
            worker.stop()
        self._workers.clear()
