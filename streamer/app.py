from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import subprocess
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.concurrency import run_in_threadpool

from streamer.media_publishers import MediaPublisherManager

CAMERA_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
VIDEO_EXTENSIONS = {".avi", ".m4v", ".mkv", ".mov", ".mp4", ".webm"}
FRAME_BOUNDARY = b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
FRAME_SUFFIX = b"\r\n"
DEFAULT_MAX_UPLOAD_BYTES = 512 * 1024 * 1024
MAX_MJPEG_BUFFER_BYTES = 16 * 1024 * 1024
LOGGER = logging.getLogger(__name__)
_EMPTY = object()
ADMIN_AUTH = HTTPBasic(auto_error=False)


def _decode_hls_token(token: str, secret: str) -> dict[str, object]:
    try:
        encoded, supplied_signature = token.split(".", 1)
        encoded_bytes = encoded.encode("ascii")
        expected = base64.urlsafe_b64encode(
            hmac.new(secret.encode("utf-8"), encoded_bytes, hashlib.sha256).digest()
        ).rstrip(b"=").decode("ascii")
        if not hmac.compare_digest(supplied_signature, expected):
            raise ValueError
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        if not isinstance(payload, dict) or int(payload["exp"]) <= int(time.time()):
            raise ValueError
        if payload.get("role") not in {"system_admin", "safety_manager"}:
            raise ValueError
        return payload
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=401,
            detail="HLS token is invalid or expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


class _FrameSubscription:
    """Single-slot mailbox: slow clients retain only the newest shared payload."""

    def __init__(self) -> None:
        self.latest_payload: bytes | None | object = _EMPTY
        self.ready = asyncio.Event()

    async def receive(self) -> bytes | None:
        await self.ready.wait()
        payload = self.latest_payload
        self.latest_payload = _EMPTY
        self.ready.clear()
        assert payload is not _EMPTY
        return payload  # type: ignore[return-value]

    def publish(self, payload: bytes | None) -> None:
        self.latest_payload = payload
        self.ready.set()


class _SharedCameraStream:
    def __init__(self, manager: CameraStreamManager, video_path: Path) -> None:
        self.manager = manager
        self.video_path = video_path
        self.clients: set[_FrameSubscription] = set()
        self.process: subprocess.Popen[bytes] | None = None
        self.task: asyncio.Task[None] | None = None

    @property
    def buffered_frame_count(self) -> int:
        return int(any(client.latest_payload is not _EMPTY for client in self.clients))

    def subscribe(self) -> _FrameSubscription:
        subscription = _FrameSubscription()
        self.clients.add(subscription)
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self._run())
        return subscription

    def detach_worker(self) -> tuple[asyncio.Task[None] | None, subprocess.Popen[bytes] | None]:
        task = self.task
        process = self.process
        self.task = None
        self.process = None
        return task, process

    async def _run(self) -> None:
        process: subprocess.Popen[bytes] | None = None
        loop = asyncio.get_running_loop()
        buffer = bytearray()

        try:
            process = self.manager.spawn_ffmpeg_reader(self.video_path)
            self.process = process
            assert process.stdout is not None
            while True:
                chunk = await loop.run_in_executor(None, process.stdout.read, 64 * 1024)
                if not chunk:
                    break
                buffer.extend(chunk)

                while True:
                    start = buffer.find(b"\xff\xd8")
                    if start < 0:
                        if len(buffer) > MAX_MJPEG_BUFFER_BYTES:
                            raise RuntimeError("FFmpeg MJPEG buffer exceeded limit")
                        break
                    end = buffer.find(b"\xff\xd9", start + 2)
                    if end < 0:
                        if start:
                            del buffer[:start]
                        if len(buffer) > MAX_MJPEG_BUFFER_BYTES:
                            raise RuntimeError("FFmpeg MJPEG frame exceeded limit")
                        break
                    frame = bytes(buffer[start : end + 2])
                    del buffer[: end + 2]
                    self._publish(FRAME_BOUNDARY + frame + FRAME_SUFFIX)
        except asyncio.CancelledError:
            raise
        except Exception:
            LOGGER.exception("Camera stream worker failed for %s", self.video_path.name)
        finally:
            if self.process is process:
                self.process = None
            self._publish(None)
            if process is not None:
                process.terminate()
                try:
                    await loop.run_in_executor(None, process.wait, 1)
                except Exception:
                    process.kill()
                    await loop.run_in_executor(None, process.wait)

    def _publish(self, frame: bytes | None) -> None:
        for client in self.clients:
            client.publish(frame)


class CameraStreamManager:
    def __init__(self, media_dir: Path) -> None:
        self.media_dir = media_dir
        self.media_dir.mkdir(parents=True, exist_ok=True)
        self._streams: dict[Path, _SharedCameraStream] = {}
        self._lock = asyncio.Lock()

    def cameras(self) -> list[str]:
        return sorted(
            path.stem for path in self.media_dir.iterdir() if path.is_file() and path.suffix in VIDEO_EXTENSIONS
        )

    def upload_path(self, camera_id: str) -> Path:
        return self.media_dir / f"{camera_id}.mp4"

    def spawn_ffmpeg_reader(self, video_path: Path) -> subprocess.Popen[bytes]:
        """Create the one FFmpeg reader shared by this camera's clients."""
        return subprocess.Popen(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-stream_loop",
                "-1",
                "-re",
                "-i",
                str(video_path),
                "-an",
                "-fflags",
                "nobuffer",
                "-f",
                "mjpeg",
                "-q:v",
                "5",
                "-flush_packets",
                "1",
                "pipe:1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

    async def frames_generator(self, video_path: Path) -> AsyncIterator[bytes]:
        """Yield one shared camera's JPEG frames to each connected client."""
        async with self._lock:
            stream = self._get_stream(video_path)
            subscription = stream.subscribe()

        try:
            while (payload := await subscription.receive()) is not None:
                yield payload
        finally:
            await self._unsubscribe(video_path, stream, subscription)

    def _get_stream(self, video_path: Path) -> _SharedCameraStream:
        stream = self._streams.get(video_path)
        if stream is None:
            stream = _SharedCameraStream(self, video_path)
            self._streams[video_path] = stream
        return stream

    def remove_stream(self, video_path: Path, stream: _SharedCameraStream) -> None:
        if self._streams.get(video_path) is stream:
            self._streams.pop(video_path, None)

    async def _unsubscribe(
        self,
        video_path: Path,
        stream: _SharedCameraStream,
        subscription: _FrameSubscription,
    ) -> None:
        task: asyncio.Task[None] | None = None
        process: subprocess.Popen[bytes] | None = None
        async with self._lock:
            stream.clients.discard(subscription)
            if not stream.clients:
                self.remove_stream(video_path, stream)
                task, process = stream.detach_worker()
        await self._stop_worker(task, process)

    async def stop_stream(self, video_path: Path) -> None:
        """Stop and unregister a camera worker, closing all connected clients."""
        async with self._lock:
            task, process = self._detach_stream(video_path)
        await self._stop_worker(task, process)

    async def replace_media(self, temporary: Path, video_path: Path) -> None:
        """Atomically publish new media and detach any worker reading the old file."""
        async with self._lock:
            temporary.replace(video_path)
            task, process = self._detach_stream(video_path)
        await self._stop_worker(task, process)

    async def delete_media(self, video_path: Path) -> bool:
        """Atomically remove camera media and detach its active worker."""
        async with self._lock:
            if not video_path.is_file():
                return False
            video_path.unlink()
            task, process = self._detach_stream(video_path)
        await self._stop_worker(task, process)
        return True

    async def stop_all(self) -> None:
        for video_path in tuple(self._streams):
            await self.stop_stream(video_path)

    def _detach_stream(
        self,
        video_path: Path,
    ) -> tuple[asyncio.Task[None] | None, subprocess.Popen[bytes] | None]:
        stream = self._streams.pop(video_path, None)
        if stream is None:
            return None, None
        stream._publish(None)
        return stream.detach_worker()

    @staticmethod
    async def _stop_worker(
        task: asyncio.Task[None] | None,
        process: subprocess.Popen[bytes] | None,
    ) -> None:
        if process is not None:
            process.terminate()
        if task is not None and task is not asyncio.current_task():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task


def valid_camera_id(camera_id: str) -> str:
    if not CAMERA_ID.fullmatch(camera_id):
        raise HTTPException(status_code=400, detail="Invalid camera_id")
    return camera_id


def create_app(
    media_dir: Path | None = None,
    *,
    max_upload_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
    rtsp_enabled: bool | None = None,
    rtsp_origin: str | None = None,
    public_hls_origin: str | None = None,
    admin_username: str | None = None,
    admin_password: str | None = None,
    hls_token_secret: str | None = None,
    hls_upstream_origin: str | None = None,
) -> FastAPI:
    manager = CameraStreamManager(media_dir or Path("data/streamer"))
    media_publishers = MediaPublisherManager(
        manager.media_dir,
        rtsp_origin=rtsp_origin or os.getenv("MEDIA_RTSP_ORIGIN", "rtsp://mediamtx:8554"),
        public_hls_origin=public_hls_origin or os.getenv("MEDIA_PUBLIC_ORIGIN", "http://localhost:8888"),
    )
    use_rtsp = rtsp_enabled if rtsp_enabled is not None else os.getenv("MEDIA_RTSP_ENABLED", "false").lower() == "true"
    configured_admin_username = admin_username if admin_username is not None else os.getenv("STREAMER_ADMIN_USERNAME", "")
    configured_admin_password = admin_password if admin_password is not None else os.getenv("STREAMER_ADMIN_PASSWORD", "")
    configured_hls_secret = hls_token_secret if hls_token_secret is not None else os.getenv("HLS_TOKEN_SECRET", "")
    configured_hls_upstream = (
        hls_upstream_origin if hls_upstream_origin is not None else os.getenv("HLS_UPSTREAM_ORIGIN", "http://mediamtx:8888")
    ).rstrip("/")
    cors_origins = [
        origin.strip()
        for origin in os.getenv("STREAMER_CORS_ORIGINS", "http://localhost:8000,http://localhost:5173").split(",")
        if origin.strip()
    ]
    if os.getenv("APP_ENV") == "production":
        if not configured_admin_username or not configured_admin_password:
            raise RuntimeError("Production streamer requires administrator credentials")
        if len(configured_hls_secret) < 32:
            raise RuntimeError("Production streamer requires a strong HLS token secret")

    async def require_admin(credentials: HTTPBasicCredentials | None = Depends(ADMIN_AUTH)) -> None:
        if not configured_admin_username or not configured_admin_password:
            return
        if not credentials or not (
            secrets.compare_digest(credentials.username, configured_admin_username)
            and secrets.compare_digest(credentials.password, configured_admin_password)
        ):
            raise HTTPException(
                status_code=401,
                detail="Streamer administrator authentication is required",
                headers={"WWW-Authenticate": 'Basic realm="P-047 Streamer"'},
            )

    def require_hls_camera(request: Request, camera_id: str) -> dict[str, object]:
        if len(configured_hls_secret) < 32:
            raise HTTPException(status_code=503, detail="HLS gateway is not configured")
        authorization = request.headers.get("authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(
                status_code=401,
                detail="HLS bearer token is required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        payload = _decode_hls_token(token, configured_hls_secret)
        cameras = payload.get("cameras")
        if not isinstance(cameras, list) or ("*" not in cameras and camera_id not in cameras):
            raise HTTPException(status_code=403, detail="HLS token does not permit this camera")
        return payload

    def require_camera_inventory(request: Request) -> None:
        if len(configured_hls_secret) < 32:
            return
        authorization = request.headers.get("authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "basic" and token:
            try:
                username, password = base64.b64decode(token, validate=True).decode("utf-8").split(":", 1)
            except (binascii.Error, ValueError, UnicodeDecodeError):
                pass
            else:
                if secrets.compare_digest(username, configured_admin_username) and secrets.compare_digest(
                    password, configured_admin_password
                ):
                    return
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(status_code=401, detail="HLS bearer token is required")
        payload = _decode_hls_token(token, configured_hls_secret)
        if payload.get("role") != "system_admin":
            raise HTTPException(status_code=403, detail="System administrator access is required")

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        if use_rtsp:
            await media_publishers.start_existing()
        yield
        await media_publishers.shutdown()
        await manager.stop_all()

    app = FastAPI(title="P-047 Mock Camera Streamer", version="0.1.0", lifespan=lifespan)
    app.state.stream_manager = manager
    app.state.media_publishers = media_publishers

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.get("/", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
    async def index() -> str:
        return """<!doctype html>
<html>
<head><title>Mock Camera Streamer Studio</title></head>
<body style="font-family:sans-serif; padding:20px;">
  <h1>🎥 Mock Camera Streamer Studio</h1>
  <form id="upload" style="margin-bottom:20px; padding:15px; background:#f4f4f4; border-radius:8px;">
    <label>Camera ID: <input name="camera_id" value="cam_1" pattern="[A-Za-z0-9_-]+" required></label>
    <input name="video" type="file" accept="video/*" required>
    <button type="submit">Upload & Stream</button>
  </form>
  <p id="status" style="font-weight:bold; color:blue;"></p>
  <div id="camera-tabs" role="tablist" style="display:flex; gap:8px; flex-wrap:wrap; margin:15px 0;"></div>
  <section id="viewer" style="max-width:960px; border:1px solid #ccc; padding:12px; border-radius:8px; background:#fff;">
    <h2 id="viewer-title" style="margin-top:0;">Chưa có camera</h2>
    <p id="empty-viewer">Upload video để tạo camera stream.</p>
    <img id="viewer-image" alt="Camera stream" style="display:none; width:100%; border-radius:4px; background:#000;" />
  </section>

<script>
const form=document.querySelector('#upload'), status=document.querySelector('#status'), tabs=document.querySelector('#camera-tabs');
const title=document.querySelector('#viewer-title'), empty=document.querySelector('#empty-viewer'), image=document.querySelector('#viewer-image');
let activeCamera=null;
function selectCamera(camera){
    activeCamera=camera;
    title.textContent='Đang xem: '+camera;
    empty.style.display='none';
    image.style.display='block';
    image.src='/stream/'+encodeURIComponent(camera)+'?t='+Date.now();
    document.querySelectorAll('[data-camera-tab]').forEach(tab=>{
        const selected=tab.dataset.cameraTab===camera;
        tab.setAttribute('aria-selected', selected ? 'true' : 'false');
        tab.style.background=selected ? '#2563eb' : '#e5e7eb';
        tab.style.color=selected ? '#fff' : '#111';
    });
}
async function refresh(preferredCamera=null){
    const cameras = await fetch('/api/cameras').then(r=>r.json());
    tabs.innerHTML = cameras.map(c => `
      <span style="display:inline-flex; gap:3px; align-items:center;">
        <button type="button" role="tab" data-camera-tab="${c}" aria-selected="false"
          style="border:0; padding:9px 14px; border-radius:6px; cursor:pointer;">${c}</button>
        <button type="button" data-delete-camera="${c}" title="Xóa ${c}"
          style="border:0; padding:9px 10px; border-radius:6px; cursor:pointer; background:#fee2e2; color:#991b1b;">Xóa</button>
      </span>`).join('');
    tabs.querySelectorAll('[data-camera-tab]').forEach(tab=>{
        tab.onclick=()=>selectCamera(tab.dataset.cameraTab);
    });
    tabs.querySelectorAll('[data-delete-camera]').forEach(button=>{
        button.onclick=async()=>{
            const camera=button.dataset.deleteCamera;
            if(!confirm('Xóa camera '+camera+'?')) return;
            const response=await fetch('/api/cameras/'+encodeURIComponent(camera), {method:'DELETE'});
            if(!response.ok){ status.textContent='❌ Xóa camera thất bại'; return; }
            status.textContent='✅ Đã xóa '+camera;
            refresh(activeCamera===camera ? null : activeCamera);
        };
    });
    const camera=preferredCamera && cameras.includes(preferredCamera) ? preferredCamera : (activeCamera && cameras.includes(activeCamera) ? activeCamera : cameras[0]);
    if(camera) selectCamera(camera);
    else {
        activeCamera=null;
        title.textContent='Chưa có camera';
        empty.style.display='block';
        image.style.display='none';
        image.removeAttribute('src');
    }
}
form.onsubmit = async e => {
    e.preventDefault();
    status.textContent = 'Uploading video...';
    const r = await fetch('/api/cameras/' + encodeURIComponent(form.camera_id.value), { method: 'POST', body: new FormData(form) });
    status.textContent = r.ok ? '✅ Uploaded successfully!' : '❌ Upload failed';
    if(r.ok) refresh(form.camera_id.value);
};
refresh();
</script>
</body>
</html>"""

    @app.get("/api/cameras")
    async def list_cameras(request: Request) -> list[str]:
        require_camera_inventory(request)
        return manager.cameras()

    @app.post("/api/cameras/{camera_id}", dependencies=[Depends(require_admin)])
    async def upload_camera(camera_id: str, video: UploadFile = File(...)) -> dict[str, str]:
        camera_id = valid_camera_id(camera_id)
        suffix = Path(video.filename or "").suffix.lower()
        if suffix not in VIDEO_EXTENSIONS:
            raise HTTPException(status_code=415, detail="Unsupported video format")
        target = manager.upload_path(camera_id)
        temporary = target.with_suffix(".upload")
        uploaded_bytes = 0
        try:
            with temporary.open("wb") as output:
                while chunk := await video.read(1024 * 1024):
                    uploaded_bytes += len(chunk)
                    if uploaded_bytes > max_upload_bytes:
                        raise HTTPException(status_code=413, detail="Video exceeds upload size limit")
                    await run_in_threadpool(output.write, chunk)
            await manager.replace_media(temporary, target)
            if use_rtsp:
                await media_publishers.replace(camera_id, target)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
        finally:
            await video.close()
        return {"camera_id": camera_id, "stream_url": f"/stream/{camera_id}"}

    @app.delete("/api/cameras/{camera_id}", dependencies=[Depends(require_admin)])
    async def delete_camera(camera_id: str) -> dict[str, str]:
        camera_id = valid_camera_id(camera_id)
        video_path = manager.upload_path(camera_id)
        if not await manager.delete_media(video_path):
            raise HTTPException(status_code=404, detail="Camera video not found")
        await media_publishers.stop(camera_id)
        return {"camera_id": camera_id, "status": "deleted"}

    @app.get("/api/media/inventory", dependencies=[Depends(require_admin)])
    async def media_inventory() -> dict[str, object]:
        return {"version": "camera_inventory_v1", "cameras": media_publishers.inventory()}

    @app.get("/stream/{camera_id}", dependencies=[Depends(require_admin)])
    async def stream(camera_id: str) -> StreamingResponse:
        camera_id = valid_camera_id(camera_id)
        video_path = manager.upload_path(camera_id)
        if not video_path.is_file():
            raise HTTPException(status_code=404, detail="Camera video not found")

        return StreamingResponse(
            manager.frames_generator(video_path),
            media_type="multipart/x-mixed-replace; boundary=frame",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    @app.get("/hls/cameras/{camera_id}/{asset_path:path}")
    async def hls_gateway(camera_id: str, asset_path: str, request: Request) -> StreamingResponse:
        camera_id = valid_camera_id(camera_id)
        require_hls_camera(request, camera_id)
        if not asset_path or ".." in asset_path or not re.fullmatch(r"[A-Za-z0-9_.-]+", asset_path):
            raise HTTPException(status_code=400, detail="Invalid HLS asset path")
        upstream_url = f"{configured_hls_upstream}/cameras/{camera_id}/{asset_path}"
        client = httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0), follow_redirects=True)
        try:
            upstream_request = client.build_request("GET", upstream_url, params=request.query_params)
            upstream = await client.send(upstream_request, stream=True)
        except httpx.HTTPError as exc:
            await client.aclose()
            raise HTTPException(status_code=502, detail="HLS upstream is unavailable") from exc
        if upstream.status_code == 404:
            await upstream.aclose()
            await client.aclose()
            raise HTTPException(status_code=404, detail="HLS asset was not found")
        if upstream.status_code >= 400:
            await upstream.aclose()
            await client.aclose()
            raise HTTPException(status_code=502, detail="HLS upstream rejected the request")

        async def body() -> AsyncIterator[bytes]:
            received = 0
            try:
                async for chunk in upstream.aiter_raw():
                    received += len(chunk)
                    if received > 32 * 1024 * 1024:
                        LOGGER.warning("HLS upstream asset exceeded gateway limit")
                        return
                    yield chunk
            finally:
                await upstream.aclose()
                await client.aclose()

        return StreamingResponse(
            body(),
            media_type=upstream.headers.get("content-type", "application/octet-stream"),
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
