import asyncio
from pathlib import Path

import pytest

from streamer.media_publishers import MediaPublisherManager, media_path


class FakeProcess:
    def __init__(self) -> None:
        self.returncode: int | None = None
        self.terminated = False
        self.killed = False

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True
        self.returncode = 0

    def wait(self, timeout: float | None = None) -> int:
        return self.returncode or 0

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9


def test_media_path_is_deterministic_and_rejects_invalid_ids() -> None:
    assert media_path("cam_1") == "cameras/cam_1"
    with pytest.raises(ValueError):
        media_path("../camera")
    with pytest.raises(ValueError):
        media_path("camera/name")


def test_publish_command_uses_rtsp_tcp_and_locked_h264_profile(tmp_path: Path) -> None:
    manager = MediaPublisherManager(tmp_path, rtsp_origin="rtsp://mediamtx:8554")

    command = manager.publisher_command("cam_1", tmp_path / "cam_1.mp4")

    assert command[-1] == "rtsp://mediamtx:8554/cameras/cam_1"
    assert command[command.index("-rtsp_transport") + 1] == "tcp"
    assert command[command.index("-c:v") + 1] == "libx264"
    assert command[command.index("-pix_fmt") + 1] == "yuv420p"
    assert command[command.index("-r") + 1] == "10"


@pytest.mark.asyncio
async def test_start_reuses_one_publisher_and_replace_stops_old_process(tmp_path: Path) -> None:
    processes: list[FakeProcess] = []

    def spawn(_command: list[str]) -> FakeProcess:
        process = FakeProcess()
        processes.append(process)
        return process

    manager = MediaPublisherManager(tmp_path, spawn=spawn)
    source = tmp_path / "cam_1.mp4"
    source.write_bytes(b"video")

    first = await manager.start("cam_1", source)
    reused = await manager.start("cam_1", source)
    replacement = await manager.replace("cam_1", source)

    assert reused is first
    assert replacement is not first
    assert len(processes) == 2
    assert processes[0].terminated
    await manager.shutdown()


@pytest.mark.asyncio
async def test_delete_and_shutdown_stop_publishers(tmp_path: Path) -> None:
    processes: list[FakeProcess] = []

    def spawn(_command: list[str]) -> FakeProcess:
        process = FakeProcess()
        processes.append(process)
        return process

    manager = MediaPublisherManager(tmp_path, spawn=spawn)
    for camera_id in ("cam_1", "cam_2"):
        source = tmp_path / f"{camera_id}.mp4"
        source.write_bytes(b"video")
        await manager.start(camera_id, source)

    await manager.stop("cam_1")
    await manager.shutdown()

    assert all(process.terminated for process in processes)
    assert manager.inventory() == []


@pytest.mark.asyncio
async def test_unexpected_exit_restarts_with_bounded_backoff(tmp_path: Path) -> None:
    processes: list[FakeProcess] = []
    delays: list[float] = []

    def spawn(_command: list[str]) -> FakeProcess:
        process = FakeProcess()
        processes.append(process)
        return process

    async def sleep(delay: float) -> None:
        delays.append(delay)
        if len(processes) == 1:
            processes[0].returncode = 1
        await asyncio.sleep(0)

    manager = MediaPublisherManager(tmp_path, spawn=spawn, sleep=sleep, poll_interval=0.01)
    source = tmp_path / "cam_1.mp4"
    source.write_bytes(b"video")
    await manager.start("cam_1", source)

    for _ in range(20):
        if len(processes) >= 2:
            break
        await asyncio.sleep(0)

    assert len(processes) >= 2
    assert delays
    assert max(delays) <= manager.max_backoff
    await manager.shutdown()
