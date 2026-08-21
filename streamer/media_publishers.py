"""Managed FFmpeg publishers for the RTSP-first simulated CCTV boundary."""

from __future__ import annotations

import asyncio
import logging
import re
import subprocess
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

LOGGER = logging.getLogger(__name__)
CAMERA_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class PublisherProcess(Protocol):
    returncode: int | None

    def poll(self) -> int | None: ...
    def terminate(self) -> None: ...
    def wait(self, timeout: float | None = None) -> int: ...
    def kill(self) -> None: ...


def media_path(camera_id: str) -> str:
    """Return the only allowed MediaMTX path for a validated camera ID."""
    if not CAMERA_ID_PATTERN.fullmatch(camera_id):
        raise ValueError("Invalid camera_id")
    return f"cameras/{camera_id}"


@dataclass
class Publisher:
    camera_id: str
    source: Path
    process: PublisherProcess
    monitor: asyncio.Task[None] | None = None
    stopping: bool = False
    restarts: int = 0


class MediaPublisherManager:
    """Own at most one supervised RTSP publisher process per camera."""

    def __init__(
        self,
        media_dir: Path,
        *,
        rtsp_origin: str = "rtsp://mediamtx:8554",
        public_hls_origin: str = "http://localhost:8888",
        spawn: Callable[[list[str]], PublisherProcess] | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        poll_interval: float = 0.5,
        max_backoff: float = 30.0,
    ) -> None:
        self.media_dir = media_dir
        self.rtsp_origin = rtsp_origin.rstrip("/")
        self.public_hls_origin = public_hls_origin.rstrip("/")
        self._spawn = spawn or self._spawn_process
        self._sleep = sleep
        self.poll_interval = poll_interval
        self.max_backoff = max_backoff
        self._publishers: dict[str, Publisher] = {}
        self._lock = asyncio.Lock()

    def publisher_command(self, camera_id: str, source: Path) -> list[str]:
        path = media_path(camera_id)
        return [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-re",
            "-stream_loop",
            "-1",
            "-i",
            str(source),
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-tune",
            "zerolatency",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "10",
            "-b:v",
            "800k",
            "-maxrate",
            "1000k",
            "-bufsize",
            "1600k",
            "-g",
            "20",
            "-keyint_min",
            "20",
            "-sc_threshold",
            "0",
            "-rtsp_transport",
            "tcp",
            "-f",
            "rtsp",
            f"{self.rtsp_origin}/{path}",
        ]

    async def start(self, camera_id: str, source: Path) -> Publisher:
        media_path(camera_id)
        if not source.is_file():
            raise FileNotFoundError(source)
        async with self._lock:
            current = self._publishers.get(camera_id)
            if current and current.source == source and current.process.poll() is None:
                return current
            if current:
                await self._stop_locked(current)
            publisher = self._new_publisher(camera_id, source)
            self._publishers[camera_id] = publisher
            publisher.monitor = asyncio.create_task(self._monitor(publisher))
            return publisher

    async def replace(self, camera_id: str, source: Path) -> Publisher:
        async with self._lock:
            current = self._publishers.get(camera_id)
            if current:
                await self._stop_locked(current)
            publisher = self._new_publisher(camera_id, source)
            self._publishers[camera_id] = publisher
            publisher.monitor = asyncio.create_task(self._monitor(publisher))
            return publisher

    async def stop(self, camera_id: str) -> None:
        async with self._lock:
            publisher = self._publishers.pop(camera_id, None)
            if publisher:
                await self._stop_locked(publisher)

    async def shutdown(self) -> None:
        async with self._lock:
            publishers = list(self._publishers.values())
            self._publishers.clear()
            for publisher in publishers:
                await self._stop_locked(publisher)

    async def start_existing(self) -> None:
        for source in sorted(self.media_dir.glob("*.mp4")):
            await self.start(source.stem, source)

    def inventory(self) -> list[dict[str, object]]:
        return [
            {
                "stream_camera_id": publisher.camera_id,
                "status": "ready" if publisher.process.poll() is None else "starting",
                "media_path": media_path(publisher.camera_id),
                "transports": {
                    "hls": f"{self.public_hls_origin}/{media_path(publisher.camera_id)}/index.m3u8",
                },
                "restarts": publisher.restarts,
            }
            for publisher in sorted(self._publishers.values(), key=lambda item: item.camera_id)
        ]

    def _new_publisher(self, camera_id: str, source: Path) -> Publisher:
        process = self._spawn(self.publisher_command(camera_id, source))
        return Publisher(camera_id=camera_id, source=source, process=process)

    async def _monitor(self, publisher: Publisher) -> None:
        backoff = 1.0
        try:
            while not publisher.stopping:
                await self._sleep(self.poll_interval)
                if publisher.stopping or publisher.process.poll() is None:
                    continue
                LOGGER.warning("RTSP publisher exited for %s; retrying", publisher.camera_id)
                await self._sleep(backoff)
                if publisher.stopping:
                    break
                publisher.process = self._spawn(self.publisher_command(publisher.camera_id, publisher.source))
                publisher.restarts += 1
                backoff = min(backoff * 2, self.max_backoff)
        except asyncio.CancelledError:
            raise

    async def _stop_locked(self, publisher: Publisher) -> None:
        publisher.stopping = True
        if publisher.process.poll() is None:
            publisher.process.terminate()
            try:
                publisher.process.wait(3)
            except Exception:
                publisher.process.kill()
                publisher.process.wait()
        if publisher.monitor and publisher.monitor is not asyncio.current_task():
            publisher.monitor.cancel()
            try:
                await publisher.monitor
            except asyncio.CancelledError:
                pass

    @staticmethod
    def _spawn_process(command: list[str]) -> PublisherProcess:
        return subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
