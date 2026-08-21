# P-047 — Chạy và dùng dự án

P-047 là ứng dụng giám sát an toàn PPE và vùng nguy hiểm bằng Computer Vision. Tài liệu này dành cho việc cài đặt, chạy local và gọi thử API. Xem [context-map.md](context-map.md) khi cần hiểu sản phẩm, kiến trúc, contract hoặc tài liệu theo task.

## Yêu cầu

- Python 3.11 và [uv](https://docs.astral.sh/uv/)
- Node.js/npm tương thích với `frontend/package-lock.json`
- Git LFS nếu clone model checkpoint lần đầu
- FFmpeg (`ffmpeg` trong `PATH`) cho mock camera streamer local
- PostgreSQL 16 đang chạy local, qua Docker Compose, hoặc qua TCP proxy có thể truy cập từ máy phát triển

Python 3.11 là runtime duy nhất được lock, Docker và CI hỗ trợ; `make setup` dùng `.python-version` để chọn đúng runtime.

## Cài đặt và chạy local

```bash
git clone https://github.com/AI20K-Build-Cohort-2/P-047.git
cd P-047
make setup
make run
```

`make setup` đồng bộ Python dependencies, cài frontend dependencies, tạo `.env.development` từ `.env.development.example` nếu chưa có, rồi migrate PostgreSQL. `make run` migrate lại an toàn, build frontend, khởi động mock streamer tại cổng 8001 và FastAPI tại cổng 8000. Đây là workflow chỉ dành cho local; production triển khai streamer như một service riêng.

PostgreSQL là database duy nhất ở local, test và deployment. Trước khi chạy migration, `DATABASE_URL` phải là URL PostgreSQL có thể truy cập từ chính môi trường đang chạy lệnh. Host `*.railway.internal` chỉ dùng được giữa các service trong Railway; máy local phải dùng PostgreSQL local hoặc TCP Proxy URL của Railway. Không cấu hình SQLite và không bật database fallback. Docker Compose dùng PostgreSQL disposable nội bộ. Với deployment, cấu hình giá trị thật từ `.env.production.example` trong secret/Variables của nền tảng.

> Trạng thái chuyển đổi: tài liệu đã chốt contract PostgreSQL-only, nhưng runtime hiện vẫn còn bootstrap/fallback SQLite tương thích cũ. Không xem chuyển đổi là hoàn tất cho đến khi Makefile, template môi trường, cấu hình backend và test đã loại bỏ đường chạy đó.

Mở sau khi server sẵn sàng:

- App: <http://localhost:8000/>
- Mock streamer: <http://localhost:8001/>
- Swagger: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>
- OpenAPI: <http://localhost:8000/openapi.json>
- Health: <http://localhost:8000/health>

Để phát triển frontend riêng, chạy `make frontend-dev` rồi mở <http://localhost:5173>. Vite proxy `/api` và WebSocket về backend cổng 8000.

## Biến môi trường

Chỉ sửa `.env.development` trên máy local; file này bị Git bỏ qua. Với deployment, lấy `.env.production.example` làm mẫu và đặt các giá trị thật trong secret/Variables của nền tảng, không commit credential.

| Biến | Dùng cho | Local / lưu ý |
|---|---|---|
| `APP_ENV` | Chế độ runtime | `development` local; `production` khi deploy |
| `CORS_ORIGINS` | Origin được phép gọi API | Mặc định `http://localhost:8000`; thêm `http://localhost:5173` khi dùng Vite riêng |
| `DATABASE_URL` | PostgreSQL bắt buộc | Dùng URL truy cập được từ môi trường hiện tại; Docker Compose tự ghi đè bằng DB disposable |
| `DATABASE_FALLBACK_ENABLED` | Cờ tương thích cũ đang chờ xóa | Luôn đặt `false`; PostgreSQL lỗi thì startup/migration phải fail |
| `SNAPSHOT_STORAGE_*` | S3-compatible bucket cho snapshot đã redact | Điền bucket, endpoint và credential ở môi trường có S3; không đưa secrets vào tài liệu |
| `PPE_MODEL_PATH` | Checkpoint an toàn | Phải trỏ đến `models/yolo11m_safety.pt` |
| `FACE_DETECTOR_MODEL_PATH` | YuNet privacy detector | Phải trỏ đến `models/face_detection_yunet_2023mar.onnx` |
| `FACE_DETECTOR_SCORE_THRESHOLD` | Ngưỡng face YuNet | Mặc định `0.6`; person không có face sẽ dùng fallback 40% |
| `FACE_REDACTION_MARGIN_RATIO` | Biên mở rộng face trước blur | Mặc định `0.2` |
| `VIOLATION_FRAME` | Số frame vi phạm liên tiếp trước khi cảnh báo | Mặc định `4`; một frame không vi phạm sẽ reset pending count |
| `OPENAI_API_KEY` | Gợi ý AI tùy chọn | Để trống dùng offline safety recommendation |

Frontend dùng `VITE_STREAMER_URL` để trỏ tới streamer. Local mặc định là
`http://<frontend-host>:8001`; production bắt buộc đặt URL public của streamer
service riêng. Ứng dụng dùng URL này để đọc `/api/cameras` và hiển thị
`/stream/{camera_id}`. Backend `/api/v1/stream-config` persists up to four
display-camera mappings; only `system_admin` may connect or disconnect them.
Live Monitor renders the four mappings in a 2×2 grid and shows an empty state
for an unmapped camera.

### Kết nối môi trường local với streamer đã deploy trên Railway

Railway production chạy `streamer` và `mediamtx` thành hai service riêng:

- Browser gọi `streamer` qua public HTTPS.
- `streamer` publish RTSP tới `mediamtx` qua private network của Railway.
- Browser bên ngoài Railway không truy cập được hostname `*.railway.internal`.

Để frontend chạy local đọc camera từ streamer Railway, lấy **Public Domain** của
service `streamer` trong Railway (`Settings` → `Networking`), rồi thêm vào
`.env.development`:

```dotenv
LOG_LEVEL=INFO
MEDIA_RTSP_ENABLED=false
VITE_STREAMER_URL=https://your-streamer.up.railway.app
VITE_MEDIA_PUBLIC_ORIGIN=https://your-streamer.up.railway.app
VITE_STREAM_TRANSPORT=hls
```

Browser gọi authenticated HLS gateway tại public streamer; MediaMTX vẫn private.
Sau khi sửa biến `VITE_*`, dừng và chạy lại frontend vì Vite đọc các biến này
lúc build/start.

Kiểm tra streamer trước khi mở Live Monitor:

```bash
STREAMER_PUBLIC_URL=https://your-streamer.up.railway.app
curl -fsS "$STREAMER_PUBLIC_URL/health"
curl -fsS "$STREAMER_PUBLIC_URL/api/cameras"
```

Thay `your-streamer.up.railway.app` bằng domain Railway cấp cho đúng project,
giữ giao thức `https://` và không thêm dấu `/` cuối.

### Variables của các service Railway

Trong service `streamer`, cấu hình:

```dotenv
MEDIA_RTSP_ENABLED=true
MEDIA_RTSP_ORIGIN=rtsp://${{RTSP_PUBLISH_USER}}:${{RTSP_PUBLISH_PASSWORD}}@${{mediamtx.RAILWAY_PRIVATE_DOMAIN}}:8554
MEDIA_PUBLIC_ORIGIN=http://${{mediamtx.RAILWAY_PRIVATE_DOMAIN}}:8888
HLS_UPSTREAM_ORIGIN=http://${{mediamtx.RAILWAY_PRIVATE_DOMAIN}}:8888
HLS_TOKEN_SECRET=<shared-random-secret-minimum-32-characters>
STREAMER_ADMIN_USERNAME=<operations-username>
STREAMER_ADMIN_PASSWORD=<strong-operations-password>
STREAMER_CORS_ORIGINS=https://${{p047-app.RAILWAY_PUBLIC_DOMAIN}}
APP_ENV=production
```

`RTSP_PUBLISH_USER` và `RTSP_PUBLISH_PASSWORD` phải khớp cấu hình xác thực của
service `mediamtx`. Railway tự resolve private domain từ service có tên chính
xác là `mediamtx`, nên không cần hard-code hostname. Chỉ lưu credential trong
Railway Variables; không copy vào `.env.example`, frontend, Git, log hoặc tài liệu.

Trong service `p047-app`, đặt các Variables sau **trước khi Railway build/deploy**:

```dotenv
VITE_STREAMER_URL=https://${{streamer.RAILWAY_PUBLIC_DOMAIN}}
VITE_MEDIA_PUBLIC_ORIGIN=https://${{streamer.RAILWAY_PUBLIC_DOMAIN}}
VITE_STREAM_TRANSPORT=hls
HLS_TOKEN_SECRET=<same-shared-random-secret>
```

Service phải có tên chính xác là `streamer` và đã được cấp Public Domain.
Railway tự resolve `${{streamer.RAILWAY_PUBLIC_DOMAIN}}`, nên cấu hình không phụ
thuộc domain của một tài khoản hoặc project cụ thể. Biến `VITE_*` được đóng vào
frontend khi build; sau khi thêm hoặc đổi biến, bấm **Redeploy** `p047-app` để
build lại frontend.

Không tạo Public Domain cho MediaMTX. Browser đăng nhập P-047 một lần; backend
cấp token HLS 15 phút cho `system_admin` và `safety_manager`, frontend tự gia hạn,
và streamer gateway xác thực token trước khi đọc HLS private. `area_manager`
nhận `403`; token sai hoặc hết hạn nhận `401`. Trang quản trị streamer trực tiếp
dùng `STREAMER_ADMIN_USERNAME`/`STREAMER_ADMIN_PASSWORD`, không dùng tài khoản
P-047 hoặc RTSP publisher credential.

`/health` chỉ báo `ready: true` khi runtime có PostgreSQL thật và S3 `HeadBucket` thành công. PostgreSQL hoặc storage chưa sẵn sàng sẽ trả `degraded`; xem các reason code an toàn trong response, không đưa URL/credential vào log hay ticket.

## Truy vấn mẫu

Các lệnh bên dưới giả định `make run` đang chạy trong terminal khác.

```bash
# Kiểm tra process và dependency readiness
curl http://localhost:8000/health

# Lấy PPE requirement hiện tại của camera/zone MVP
curl http://localhost:8000/api/v1/ppe-requirements/uploaded_video/zone_01

# Lưu contract canonical hat/vest
curl -X PUT http://localhost:8000/api/v1/ppe-requirements/uploaded_video/zone_01 \
  -H 'Content-Type: application/json' \
  -d '{"profile":"hat_vest_v1","hat_required":true,"vest_required":true}'
```

PostgreSQL development rỗng được seed demo accounts. Ví dụ đăng nhập `system_admin` và gọi endpoint cần bearer token:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@sentinel.local","password":"Sentinel123!"}'

# Dán access_token từ response vào biến shell, không commit token.
TOKEN='paste-access-token-here'
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

Demo password chỉ dành cho local development. Hãy thay đổi hoặc tạo tài khoản phù hợp trước khi dùng môi trường được chia sẻ. Swagger là nguồn HTTP API tương tác; WebSocket inference tại `ws://localhost:8000/api/v1/ws/inference` không xuất hiện trong OpenAPI. Protocol đầy đủ nằm trong [backend README](backend/README.md#frame-inference-contract).

## Docker Compose smoke

```bash
make setup
make docker-up
make docker-smoke
```

Compose nạp `.env.development` nhưng dùng PostgreSQL `db` nội bộ disposable, tách biệt với `DATABASE_URL` của developer. Dùng credential development/staging cho smoke test, không dùng credential production.

Để build và publish riêng mock streamer, xem `streamer/README.md`. Tóm tắt:

```bash
docker build -f streamer/Dockerfile -t p047-streamer:dev .
docker run --rm --name p047-streamer -p 8001:8001 \
  -v "$PWD/data/streamer:/app/data/streamer" p047-streamer:dev
docker login
docker tag p047-streamer:dev DOCKERHUB_USERNAME/p047-streamer:dev
docker push DOCKERHUB_USERNAME/p047-streamer:dev
```

Nếu đã build image bằng username `nguyennaht4`, image cụ thể là
`nguyennaht4/streamer:dev`; xem `streamer/README.md` để biết cách chạy và ý
nghĩa từng tham số Docker.

## CI/CD và release

Pipeline GitHub Actions kiểm tra PR vào `main`, deploy Railway chỉ sau CI xanh và hỗ trợ rollback theo SHA/tag. Thành viên mới cấu hình Environment, Railway Variables, branch protection và vận hành release theo [CI/CD và Railway release](docs/CI_CD.md).

## Kiểm tra

```bash
make check
```

Hoặc chạy riêng `make lint`, `make format`, `make test`, `make frontend-lint`, `make frontend-type-check`, `make frontend-test`, và `make frontend-build`.

## Đóng góp

- Đọc [context-map.md](context-map.md) trước để chọn đúng tài liệu và owner.
- Đọc README của production owner trước khi sửa implementation trong owner đó.
- Không đọc `src/` nếu task không yêu cầu trực tiếp.
- Chỉ commit khi người dùng yêu cầu trực tiếp.

Quy tắc đầy đủ nằm trong [AGENTS.md](AGENTS.md).

## License

MIT
