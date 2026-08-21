from collections import deque

import numpy as np
import pytest

from backend.app.integrations.rtsp_frame_source import (
    InvalidMediaSourceError,
    RtspFrameSource,
    build_rtsp_camera_url,
)


class FakeCapture:
    def __init__(self, reads):
        self._reads = deque(reads)
        self.released = False

    def isOpened(self):  # noqa: N802 - mirrors OpenCV's public API
        return True

    def read(self):
        return self._reads.popleft()

    def release(self):
        self.released = True


def test_build_rtsp_camera_url_derives_validated_media_path():
    assert build_rtsp_camera_url("rtsp://reader:secret@mediamtx:8554", "line_1") == (
        "rtsp://reader:secret@mediamtx:8554/cameras/line_1"
    )


@pytest.mark.parametrize("camera_id", ["../admin", "line/1", "", "camera id"])
def test_build_rtsp_camera_url_rejects_untrusted_camera_id(camera_id):
    with pytest.raises(InvalidMediaSourceError):
        build_rtsp_camera_url("rtsp://mediamtx:8554", camera_id)


def test_frame_source_samples_no_faster_than_configured_rate():
    frame = np.zeros((8, 8, 3), dtype=np.uint8)
    capture = FakeCapture([(True, frame), (True, frame)])
    times = iter([0.0, 0.1, 0.5])
    source = RtspFrameSource(
        "rtsp://mediamtx:8554/cameras/cam_1",
        max_fps=2.0,
        capture_factory=lambda _: capture,
        monotonic=lambda: next(times),
    )

    assert source.read_sample() is frame
    assert source.read_sample() is None
    assert source.read_sample() is frame

    source.close()
    assert capture.released is True


def test_frame_source_reconnects_after_a_failed_read():
    frame = np.zeros((8, 8, 3), dtype=np.uint8)
    failed = FakeCapture([(False, None)])
    recovered = FakeCapture([(True, frame)])
    captures = iter([failed, recovered])
    source = RtspFrameSource(
        "rtsp://mediamtx:8554/cameras/cam_1",
        capture_factory=lambda _: next(captures),
        monotonic=lambda: 1.0,
    )

    assert source.read_sample() is None
    assert failed.released is True
    assert source.read_sample() is frame
