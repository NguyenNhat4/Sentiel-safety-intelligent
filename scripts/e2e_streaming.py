"""Verify real camera video reaches the public MJPEG stream endpoint.

Usage: STREAMER_URL=http://localhost:8001 EXPECTED_CAMERAS=4 make e2e-streaming
"""

from __future__ import annotations

import os
import json
import sys
import mimetypes
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

STREAMER_URL = os.getenv("STREAMER_URL", "http://localhost:8001").rstrip("/")
EXPECTED_CAMERAS = int(os.getenv("EXPECTED_CAMERAS", "1"))
SOURCE_VIDEO = Path(os.getenv("SOURCE_VIDEO", "data/test.mp4"))
READ_LIMIT = 512 * 1024


def upload_test_video(camera_id: str) -> None:
    if not SOURCE_VIDEO.is_file():
        raise AssertionError(f"source video does not exist: {SOURCE_VIDEO}")
    boundary = b"----P047StreamingE2E"
    content_type = mimetypes.guess_type(SOURCE_VIDEO.name)[0] or "video/mp4"
    video = SOURCE_VIDEO.read_bytes()
    body = b"--" + boundary + b"\r\n"
    body += f'Content-Disposition: form-data; name="video"; filename="{SOURCE_VIDEO.name}"\r\n'.encode()
    body += f"Content-Type: {content_type}\r\n\r\n".encode() + video
    body += b"\r\n--" + boundary + b"--\r\n"
    response = urlopen(
        Request(
            f"{STREAMER_URL}/api/cameras/{camera_id}",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary.decode()}"},
            method="POST",
        ),
        timeout=30,
    )
    response.close()


def read_frame(camera_id: str) -> tuple[str, bytes]:
    try:
        response = urlopen(Request(f"{STREAMER_URL}/stream/{camera_id}", headers={"Accept": "multipart/x-mixed-replace"}), timeout=15)
    except (HTTPError, URLError) as exc:
        raise AssertionError(f"{camera_id}: cannot open stream: {exc}") from exc
    with response:
        content_type = response.headers.get("Content-Type", "")
        if "multipart/x-mixed-replace" not in content_type:
            raise AssertionError(f"{camera_id}: expected MJPEG content type, got {content_type!r}")
        data = response.read(READ_LIMIT)
    start = data.find(b"\xff\xd8")
    end = data.find(b"\xff\xd9", start + 2)
    if start < 0 or end < 0:
        raise AssertionError(f"{camera_id}: no complete JPEG frame found in {len(data)} bytes")
    return content_type, data[start : end + 2]


def main() -> int:
    try:
        upload_test_video("cam_1")
        with urlopen(f"{STREAMER_URL}/health", timeout=10) as response:
            if response.status != 200:
                raise AssertionError(f"streamer health returned HTTP {response.status}")
        with urlopen(f"{STREAMER_URL}/api/cameras", timeout=10) as response:
            cameras = response.read().decode()
        camera_ids = json.loads(cameras)
        if len(camera_ids) < EXPECTED_CAMERAS:
            raise AssertionError(f"expected {EXPECTED_CAMERAS} cameras, found {camera_ids}")
        results = []
        for camera_id in camera_ids[:EXPECTED_CAMERAS]:
            content_type, frame = read_frame(camera_id)
            results.append(f"{camera_id}={len(frame)}B")
            if not frame.startswith(b"\xff\xd8") or not frame.endswith(b"\xff\xd9"):
                raise AssertionError(f"{camera_id}: invalid JPEG markers")
        print(f"STREAMING E2E PASS: {', '.join(results)}; source={STREAMER_URL}")
        return 0
    except (AssertionError, HTTPError, URLError, OSError) as exc:
        print(f"STREAMING E2E FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
