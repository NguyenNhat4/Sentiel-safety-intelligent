import asyncio
import base64
import hashlib
import hmac
import io
import json
import time
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncByteStream, AsyncClient, MockTransport, Request, Response

import streamer.app as streamer_app
from streamer.app import CameraStreamManager, create_app


def _hls_token(secret: str, *, role: str = "safety_manager", cameras: list[str] | None = None) -> str:
    payload = {
        "sub": "user-1",
        "role": role,
        "cameras": cameras or ["cam_1"],
        "iat": int(time.time()),
        "exp": int(time.time()) + 900,
    }
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).rstrip(b"=")
    signature = base64.urlsafe_b64encode(hmac.new(secret.encode(), encoded, hashlib.sha256).digest()).rstrip(b"=")
    return f"{encoded.decode()}.{signature.decode()}"


class _CompletedProcess:
    def __init__(self, output: bytes = b"") -> None:
        self.stdout = io.BytesIO(output)
        self.returncode: int | None = None

    def terminate(self) -> None:
        self.returncode = 0

    def wait(self, timeout: float | None = None) -> int:
        self.returncode = 0
        return 0

    def kill(self) -> None:
        self.returncode = -9


class _AsyncBytes(AsyncByteStream):
    def __init__(self, content: bytes) -> None:
        self.content = content

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield self.content


@pytest.fixture
def immediate_threadpool(monkeypatch: pytest.MonkeyPatch) -> None:
    async def run_immediately(function: object, *args: object, **kwargs: object) -> object:
        return function(*args, **kwargs)  # type: ignore[operator]

    monkeypatch.setattr(streamer_app, "run_in_threadpool", run_immediately)


@pytest.mark.asyncio
async def test_reuses_one_camera_worker_for_multiple_clients(tmp_path: Path) -> None:
    app = create_app(tmp_path)
    manager = app.state.stream_manager
    video_path = tmp_path / "cam_1.mp4"
    video_path.write_bytes(b"video")
    first = manager._get_stream(video_path)
    second = manager._get_stream(video_path)
    first.task = asyncio.create_task(asyncio.sleep(10))  # type: ignore[assignment]
    first_client = first.subscribe()
    second_client = second.subscribe()

    assert first is second
    first._publish(b"jpeg-frame")
    first_frame = await first_client.receive()
    second_frame = await second_client.receive()
    assert first_frame == b"jpeg-frame"
    assert second_frame is first_frame

    first.task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first.task


@pytest.mark.asyncio
async def test_buffers_one_latest_frame_for_one_hundred_clients(tmp_path: Path) -> None:
    manager = CameraStreamManager(tmp_path)
    stream = manager._get_stream(tmp_path / "cam_1.mp4")
    stream.task = asyncio.create_task(asyncio.sleep(10))  # type: ignore[assignment]

    subscriptions = [stream.subscribe() for _ in range(100)]
    first_frame = b"first-frame"
    latest_frame = b"latest-frame"

    stream._publish(first_frame)
    stream._publish(latest_frame)

    assert stream.buffered_frame_count == 1
    assert all(subscription.latest_payload is latest_frame for subscription in subscriptions)

    stream.task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await stream.task


@pytest.mark.asyncio
async def test_closes_client_stream_when_ffmpeg_exits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manager = CameraStreamManager(tmp_path)
    video_path = tmp_path / "cam_1.mp4"
    video_path.write_bytes(b"invalid-video")
    manager.spawn_ffmpeg_reader = lambda _path: _CompletedProcess()  # type: ignore[method-assign]
    loop = asyncio.get_running_loop()

    async def run_immediately(_executor: object, function: object, *args: object) -> object:
        return function(*args)  # type: ignore[operator]

    monkeypatch.setattr(loop, "run_in_executor", run_immediately)

    generator = manager.frames_generator(video_path)

    with pytest.raises(StopAsyncIteration):
        await asyncio.wait_for(anext(generator), timeout=0.2)


@pytest.mark.asyncio
async def test_closes_client_stream_when_ffmpeg_cannot_start(tmp_path: Path) -> None:
    manager = CameraStreamManager(tmp_path)
    video_path = tmp_path / "cam_1.mp4"
    video_path.write_bytes(b"invalid-video")

    def fail_to_start(_path: Path) -> _CompletedProcess:
        raise FileNotFoundError("ffmpeg")

    manager.spawn_ffmpeg_reader = fail_to_start  # type: ignore[method-assign]
    generator = manager.frames_generator(video_path)

    with pytest.raises(StopAsyncIteration):
        await asyncio.wait_for(anext(generator), timeout=0.2)


@pytest.mark.asyncio
async def test_stopping_camera_closes_clients_and_removes_worker(tmp_path: Path) -> None:
    manager = CameraStreamManager(tmp_path)
    video_path = tmp_path / "cam_1.mp4"
    stream = manager._get_stream(video_path)
    stream.task = asyncio.create_task(asyncio.sleep(10))  # type: ignore[assignment]
    client = stream.subscribe()

    await manager.stop_stream(video_path)

    assert await client.receive() is None
    assert stream.task is None
    assert video_path not in manager._streams


@pytest.mark.asyncio
async def test_replacing_camera_atomically_stops_old_worker(tmp_path: Path) -> None:
    manager = CameraStreamManager(tmp_path)
    video_path = tmp_path / "cam_1.mp4"
    temporary = tmp_path / "cam_1.upload"
    video_path.write_bytes(b"old-video")
    temporary.write_bytes(b"new-video")
    stream = manager._get_stream(video_path)
    stream.task = asyncio.create_task(asyncio.sleep(10))  # type: ignore[assignment]
    client = stream.subscribe()

    await manager.replace_media(temporary, video_path)

    assert video_path.read_bytes() == b"new-video"
    assert await client.receive() is None
    assert stream.task is None
    assert video_path not in manager._streams


@pytest.mark.asyncio
async def test_rejects_upload_larger_than_configured_limit(tmp_path: Path) -> None:
    app = create_app(tmp_path, max_upload_bytes=4)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/cameras/cam_1",
            files={"video": ("sample.mp4", b"12345", "video/mp4")},
        )

    assert response.status_code == 413
    assert not (tmp_path / "cam_1.mp4").exists()
    assert not (tmp_path / "cam_1.upload").exists()


@pytest.mark.asyncio
async def test_health_and_camera_list(tmp_path: Path) -> None:
    app = create_app(tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        health_response = await client.get("/health")
        cameras_response = await client.get("/api/cameras")
        inventory_response = await client.get("/api/media/inventory")

    assert health_response.json() == {"status": "ok"}
    assert cameras_response.json() == []
    assert inventory_response.json() == {"version": "camera_inventory_v1", "cameras": []}


@pytest.mark.asyncio
async def test_streamer_admin_routes_require_basic_auth(tmp_path: Path) -> None:
    app = create_app(tmp_path, admin_username="operator", admin_password="strong-password")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        anonymous = await client.get("/")
        authenticated = await client.get("/", auth=("operator", "strong-password"))
        mjpeg = await client.get("/stream/cam_1")
        health = await client.get("/health")

    assert anonymous.status_code == 401
    assert anonymous.headers["www-authenticate"] == 'Basic realm="P-047 Streamer"'
    assert authenticated.status_code == 200
    assert mjpeg.status_code == 401
    assert health.status_code == 200


@pytest.mark.asyncio
async def test_hls_gateway_rejects_missing_expired_and_wrong_camera_tokens(tmp_path: Path) -> None:
    secret = "test-secret-that-is-at-least-thirty-two-bytes"
    app = create_app(tmp_path, hls_token_secret=secret, hls_upstream_origin="http://mediamtx:8888")
    expired = _hls_token(secret)
    payload, _ = expired.split(".")
    decoded = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    decoded["exp"] = int(time.time()) - 1
    encoded = base64.urlsafe_b64encode(json.dumps(decoded, separators=(",", ":")).encode()).rstrip(b"=")
    signature = base64.urlsafe_b64encode(hmac.new(secret.encode(), encoded, hashlib.sha256).digest()).rstrip(b"=")
    expired = f"{encoded.decode()}.{signature.decode()}"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        missing = await client.get("/hls/cameras/cam_1/index.m3u8")
        stale = await client.get(
            "/hls/cameras/cam_1/index.m3u8", headers={"Authorization": f"Bearer {expired}"}
        )
        wrong_camera = await client.get(
            "/hls/cameras/cam_2/index.m3u8",
            headers={"Authorization": f"Bearer {_hls_token(secret)}"},
        )

    assert missing.status_code == 401
    assert stale.status_code == 401
    assert wrong_camera.status_code == 403


@pytest.mark.asyncio
async def test_hls_gateway_follows_mediamtx_cookie_check_redirect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "test-secret-that-is-at-least-thirty-two-bytes"
    playlist = b"#EXTM3U\n#EXT-X-VERSION:9\n"
    upstream_requests: list[Request] = []
    expected_authorization = "Basic " + base64.b64encode(b"reader:reader-password").decode()

    def upstream(request: Request) -> Response:
        upstream_requests.append(request)
        if request.headers.get("Authorization") != expected_authorization:
            return Response(401, json={"error": "authentication error"})
        if request.url.params.get("cookieCheck") != "1":
            return Response(302, headers={"Location": f"{request.url}?cookieCheck=1"})
        return Response(
            200,
            stream=_AsyncBytes(playlist),
            headers={"Content-Type": "application/vnd.apple.mpegurl"},
        )

    def upstream_client(**kwargs: object) -> AsyncClient:
        return AsyncClient(transport=MockTransport(upstream), **kwargs)

    monkeypatch.setattr(streamer_app.httpx, "AsyncClient", upstream_client)
    app = create_app(
        tmp_path,
        hls_token_secret=secret,
        hls_upstream_origin="http://reader:reader-password@mediamtx:8888",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/hls/cameras/cam_1/index.m3u8",
            headers={"Authorization": f"Bearer {_hls_token(secret)}"},
        )

    assert response.status_code == 200
    assert response.content == playlist
    assert response.headers["content-type"].startswith("application/vnd.apple.mpegurl")
    assert [request.url.params.get("cookieCheck") for request in upstream_requests] == [None, "1"]


@pytest.mark.asyncio
async def test_stream_response_disables_proxy_buffering_and_caching(tmp_path: Path) -> None:
    app = create_app(tmp_path)
    (tmp_path / "cam_1.mp4").write_bytes(b"video")
    stream_route = next(route for route in app.routes if getattr(route, "path", None) == "/stream/{camera_id}")

    response = await stream_route.endpoint("cam_1")

    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-accel-buffering"] == "no"


@pytest.mark.asyncio
async def test_uploads_video_and_lists_camera(tmp_path: Path, immediate_threadpool: None) -> None:
    app = create_app(tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/cameras/cam_1",
            files={"video": ("sample.mp4", b"not-a-real-video", "video/mp4")},
        )
        cameras_response = await client.get("/api/cameras")

    assert response.status_code == 200
    assert response.json() == {"camera_id": "cam_1", "stream_url": "/stream/cam_1"}
    assert cameras_response.json() == ["cam_1"]
    assert (tmp_path / "cam_1.mp4").read_bytes() == b"not-a-real-video"


@pytest.mark.asyncio
async def test_rejects_invalid_camera_and_extension(tmp_path: Path) -> None:
    app = create_app(tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        invalid_camera_response = await client.post(
            "/api/cameras/cam.1",
            files={"video": ("sample.mp4", b"video", "video/mp4")},
        )
        invalid_extension_response = await client.post(
            "/api/cameras/cam_1",
            files={"video": ("sample.txt", b"text", "text/plain")},
        )

    assert invalid_camera_response.status_code == 400
    assert invalid_extension_response.status_code == 415


@pytest.mark.asyncio
async def test_deletes_camera_video(tmp_path: Path, immediate_threadpool: None) -> None:
    app = create_app(tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            "/api/cameras/cam_1",
            files={"video": ("sample.mp4", b"video", "video/mp4")},
        )
        response = await client.delete("/api/cameras/cam_1")
        cameras_response = await client.get("/api/cameras")
        missing_response = await client.delete("/api/cameras/cam_1")

    assert response.status_code == 200
    assert response.json() == {"camera_id": "cam_1", "status": "deleted"}
    assert cameras_response.json() == []
    assert missing_response.status_code == 404
