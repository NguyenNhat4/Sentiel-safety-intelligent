import threading
import time

import numpy as np

from backend.app.services.camera_inference_worker import CameraInferenceWorker


class FakeSource:
    def __init__(self, frames):
        self.frames = iter(frames)
        self.closed = False

    def read_sample(self):
        return next(self.frames)

    def close(self):
        self.closed = True


def test_worker_publishes_camera_correlated_results_and_closes_source():
    frame = np.zeros((4, 6, 3), dtype=np.uint8)
    source = FakeSource([frame])
    published = []
    done = threading.Event()

    def process(camera_id, stream_camera_id, frame_id, captured_at, received_frame):
        assert received_frame is frame
        return {"type": "camera_inference_result", "result": "normal"}

    def publish(payload):
        published.append(payload)
        done.set()

    worker = CameraInferenceWorker(
        "cam_1",
        "line_1",
        source=source,
        process_frame=process,
        publish=publish,
        retry_delay_seconds=0.001,
    )
    worker.start()
    assert done.wait(1)
    worker.stop()

    assert published[0]["camera_id"] == "cam_1"
    assert published[0]["stream_camera_id"] == "line_1"
    assert published[0]["frame_id"] == 1
    assert published[0]["frame_width"] == 6
    assert published[0]["frame_height"] == 4
    assert source.closed is True


def test_worker_survives_read_errors_until_stopped():
    class FailingSource:
        closed = False

        def read_sample(self):
            raise ConnectionError("offline")

        def close(self):
            self.closed = True

    source = FailingSource()
    worker = CameraInferenceWorker(
        "cam_1",
        "line_1",
        source=source,
        process_frame=lambda *_: {},
        publish=lambda _: None,
        retry_delay_seconds=0.001,
    )

    worker.start()
    time.sleep(0.01)
    assert worker.is_alive is True
    worker.stop()
    assert source.closed is True
