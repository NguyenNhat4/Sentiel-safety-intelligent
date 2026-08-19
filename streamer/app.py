from __future__ import annotations

import asyncio
import re
import subprocess
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse

CAMERA_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
VIDEO_EXTENSIONS = {".avi", ".m4v", ".mkv", ".mov", ".mp4", ".webm"}
FRAME_BOUNDARY = b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"


class CameraStreamManager:
    def __init__(self, media_dir: Path) -> None:
        self.media_dir = media_dir
        self.media_dir.mkdir(parents=True, exist_ok=True)

    def cameras(self) -> list[str]:
        return sorted(
            path.stem for path in self.media_dir.iterdir() if path.is_file() and path.suffix in VIDEO_EXTENSIONS
        )

    def upload_path(self, camera_id: str) -> Path:
        return self.media_dir / f"{camera_id}.mp4"

    def spawn_ffmpeg_reader(self, video_path: Path) -> subprocess.Popen[bytes]:
        """Tạo một tiến trình ffmpeg riêng biệt cho từng client kết nối"""
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
        """Đọc và yield JPEG frame bất đồng bộ, tự dọn dẹp tiến trình khi ngắt kết nối"""
        process = self.spawn_ffmpeg_reader(video_path)
        assert process.stdout is not None
        loop = asyncio.get_running_loop()
        buffer = b""

        try:
            while True:
                # Đọc không đồng bộ tránh block event loop
                chunk = await loop.run_in_executor(None, process.stdout.read, 64 * 1024)
                if not chunk:
                    break
                buffer += chunk

                while b"\xff\xd8" in buffer and b"\xff\xd9" in buffer:
                    start = buffer.index(b"\xff\xd8")
                    end = buffer.index(b"\xff\xd9", start) + 2
                    yield FRAME_BOUNDARY + buffer[start:end] + b"\r\n"
                    buffer = buffer[end:]
        finally:
            # Dọn dẹp tiến trình riêng này khi client disconnect
            process.terminate()
            try:
                await loop.run_in_executor(None, process.wait, 1)
            except Exception:
                process.kill()


def valid_camera_id(camera_id: str) -> str:
    if not CAMERA_ID.fullmatch(camera_id):
        raise HTTPException(status_code=400, detail="Invalid camera_id")
    return camera_id


def create_app(media_dir: Path | None = None) -> FastAPI:
    manager = CameraStreamManager(media_dir or Path("data/streamer"))
    app = FastAPI(title="P-047 Mock Camera Streamer", version="0.1.0")

    # 1. BẮT BUỘC: Thêm CORS để App chính / React gọi API lấy danh sách cam
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", response_class=HTMLResponse)
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
    async def list_cameras() -> list[str]:
        return manager.cameras()

    @app.post("/api/cameras/{camera_id}")
    async def upload_camera(camera_id: str, video: UploadFile = File(...)) -> dict[str, str]:
        camera_id = valid_camera_id(camera_id)
        suffix = Path(video.filename or "").suffix.lower()
        if suffix not in VIDEO_EXTENSIONS:
            raise HTTPException(status_code=415, detail="Unsupported video format")
        target = manager.upload_path(camera_id)
        temporary = target.with_suffix(".upload")
        with temporary.open("wb") as output:
            while chunk := await video.read(1024 * 1024):
                output.write(chunk)
        await video.close()
        temporary.replace(target)
        return {"camera_id": camera_id, "stream_url": f"/stream/{camera_id}"}

    @app.delete("/api/cameras/{camera_id}")
    async def delete_camera(camera_id: str) -> dict[str, str]:
        camera_id = valid_camera_id(camera_id)
        video_path = manager.upload_path(camera_id)
        if not video_path.is_file():
            raise HTTPException(status_code=404, detail="Camera video not found")
        video_path.unlink()
        return {"camera_id": camera_id, "status": "deleted"}

    @app.get("/stream/{camera_id}")
    async def stream(camera_id: str) -> StreamingResponse:
        camera_id = valid_camera_id(camera_id)
        video_path = manager.upload_path(camera_id)
        if not video_path.is_file():
            raise HTTPException(status_code=404, detail="Camera video not found")

        return StreamingResponse(
            manager.frames_generator(video_path), media_type="multipart/x-mixed-replace; boundary=frame"
        )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
