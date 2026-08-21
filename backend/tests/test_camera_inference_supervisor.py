from backend.app.schemas.stream_configuration import StreamMapping
from backend.app.services.camera_inference_supervisor import CameraInferenceSupervisor


class FakeWorker:
    def __init__(self, camera_id, stream_camera_id):
        self.camera_id = camera_id
        self.stream_camera_id = stream_camera_id
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


def mapping(camera_id, stream_camera_id):
    return StreamMapping(camera_id=camera_id, stream_camera_id=stream_camera_id)


def test_reconcile_starts_one_worker_per_mapping_and_reuses_unchanged_workers():
    created = []

    def factory(camera_id, stream_camera_id):
        worker = FakeWorker(camera_id, stream_camera_id)
        created.append(worker)
        return worker

    supervisor = CameraInferenceSupervisor(factory)
    supervisor.reconcile([mapping("cam_1", "line_1"), mapping("cam_2", "line_2")])
    supervisor.reconcile([mapping("cam_1", "line_1"), mapping("cam_2", "line_2")])

    assert len(created) == 2
    assert all(worker.started for worker in created)
    assert supervisor.active_camera_ids == {"cam_1", "cam_2"}


def test_reconcile_replaces_changed_stream_and_stops_disconnected_camera():
    created = []

    def factory(camera_id, stream_camera_id):
        worker = FakeWorker(camera_id, stream_camera_id)
        created.append(worker)
        return worker

    supervisor = CameraInferenceSupervisor(factory)
    supervisor.reconcile([mapping("cam_1", "line_1"), mapping("cam_2", "line_2")])
    first_cam_1, first_cam_2 = created

    supervisor.reconcile([mapping("cam_1", "line_3")])

    assert first_cam_1.stopped is True
    assert first_cam_2.stopped is True
    assert created[-1].stream_camera_id == "line_3"
    assert created[-1].started is True
    assert supervisor.active_camera_ids == {"cam_1"}


def test_stop_all_is_idempotent():
    worker = FakeWorker("cam_1", "line_1")
    supervisor = CameraInferenceSupervisor(lambda *_: worker)
    supervisor.reconcile([mapping("cam_1", "line_1")])

    supervisor.stop_all()
    supervisor.stop_all()

    assert worker.stopped is True
    assert supervisor.active_camera_ids == set()
