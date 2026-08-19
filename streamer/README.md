# Mock Camera Streamer

Standalone camera simulator for local testing. It requires FFmpeg on the local
machine, runs on port `8001`, and stores one
uploaded video per camera, and exposes a looped MJPEG stream. This service is
deliberately independent from the safety backend; it does not run YOLO or save
events.

## Run locally

```bash
make streamer-run
```

Open <http://localhost:8001/> and upload a video for a camera such as `cam_1`.
The page creates one tab per uploaded camera; selecting a tab displays that
camera's live stream. The direct stream URL is
`http://localhost:8001/stream/cam_1` and the current camera list is available at
`http://localhost:8001/api/cameras`.

Use the **Xóa** button beside a camera tab to delete that camera's uploaded video,
or call `DELETE /api/cameras/{camera_id}` directly.

## Run with Docker

```bash
docker compose up -d --build streamer
```

Uploaded files are stored in `data/streamer/`. RTSP, HLS, and backend inference
integration are intentionally deferred until MJPEG playback is validated.

## Build and publish the streamer image separately

Run these commands from the repository root. The final `.` is the Docker build
context and is required because the Dockerfile copies the `streamer/` directory.

```bash
docker build -f streamer/Dockerfile -t p047-streamer:dev .
docker images p047-streamer
```

Hoặc dùng script trong folder `scripts/`:

```bash
./scripts/build_streamer.sh
```

Script mặc định build image `nguyennaht4/streamer:dev`. Có thể truyền tag khác:

```bash
./scripts/build_streamer.sh DOCKERHUB_USERNAME/streamer:dev
```

Run the locally built image:

```bash
mkdir -p data/streamer
docker run --rm --name p047-streamer \
  -p 8001:8001 \
  -v "$PWD/data/streamer:/app/data/streamer" \
  p047-streamer:dev
```

Then open <http://localhost:8001>. Check readiness with:

```bash
curl http://localhost:8001/health
```

Ví dụ nếu image đã build với Docker Hub username `nguyennaht4`:

```bash
mkdir -p data/streamer
docker run --rm --name p047-streamer \
  -p 8001:8001 \
  -v "$PWD/data/streamer:/app/data/streamer" \
  nguyennaht4/streamer:dev
```

Giải thích:

- `docker run`: tạo và chạy container từ image.
- `--rm`: tự xóa container sau khi container dừng.
- `--name p047-streamer`: đặt tên container.
- `-p 8001:8001`: map cổng 8001 của máy vào cổng 8001 trong container.
- `-v "$PWD/data/streamer:/app/data/streamer"`: lưu video upload trên máy host
  và cho container đọc cùng thư mục đó; video không mất khi container bị xóa.
- `nguyennaht4/streamer:dev`: tên image và tag đã build.

Sau khi chạy, mở <http://localhost:8001>. Dừng bằng `Ctrl+C`. Nếu cổng đang bị
chiếm, kiểm tra và dừng container cũ:

```bash
docker rm -f p047-streamer
```

To publish to Docker Hub, replace `DOCKERHUB_USERNAME` with your account or
organization name. Authenticate interactively; never commit a password or token.

```bash
docker login
docker tag p047-streamer:dev DOCKERHUB_USERNAME/p047-streamer:dev
docker push DOCKERHUB_USERNAME/p047-streamer:dev
```

A `latest` tag can be published explicitly:

```bash
docker tag p047-streamer:dev DOCKERHUB_USERNAME/p047-streamer:latest
docker push DOCKERHUB_USERNAME/p047-streamer:latest
```

On another machine, pull and run the image with persistent uploaded videos:

```bash
docker pull DOCKERHUB_USERNAME/p047-streamer:dev
mkdir -p data/streamer
docker run --rm --name p047-streamer \
  -p 8001:8001 \
  -v "$PWD/data/streamer:/app/data/streamer" \
  DOCKERHUB_USERNAME/p047-streamer:dev
```
