# Tách Safety Vision worker và triển khai thử

## Mục tiêu và phạm vi hiện tại

Lát cắt này tách phần YOLO11m Safety và ByteTrack ra thành một FastAPI process độc lập. Backend chính giữ nguyên REST/WebSocket phía trình duyệt, rule PPE/vùng nguy hiểm, vòng đời occurrence, HITL, database, snapshot và notification.

Luồng production hiện tại:

```text
Streamer xuất RTSP qua MediaMTX
  -> Railway backend lấy frame ở nhịp giới hạn và gọi FrameInferenceService
    -> RemoteVisionAdapter mã hóa JPEG
    -> POST /v1/infer tới vision worker
      -> YOLO11m Safety + ByteTrack
      <- bbox person/hat/vest + track_id
    <- contract safety_vision_v1
  -> Railway áp rule, deduplicate và publish metadata camera
  -> Browser phát HLS và nhận overlay qua WebSocket hiện hữu
```

REST/WebSocket gửi JPEG từ browser vẫn được giữ để tương thích và dùng cùng `FrameInferenceService`. Vision worker không đọc RTSP/HLS trực tiếp; backend tiếp tục sở hữu camera mapping, sampling, rule, review và persistence. Lần tách này chỉ thay nơi thực thi model nên contract browser và metadata camera không đổi.

## Contract của worker

- `GET /ping`: health không tải ảnh, trả contract/model version.
- `POST /v1/infer`: multipart gồm JPEG `image`, UUID `request_id`, và `monitoring_session_id` tùy chọn.
- Worker đọc tối đa 8 MiB cho mỗi JPEG và trả `413` nếu vượt giới hạn; bounding box remote phải có tọa độ không âm, kích thước/thứ tự hợp lệ.
- Response chỉ chứa canonical people, PPE observation và model detections. Worker không truy cập PostgreSQL hoặc S3.
- `VISION_WORKER_API_KEY` là tùy chọn cho deployment trực tiếp. Khi có giá trị, `/v1/infer` yêu cầu `Authorization: Bearer <key>`; `/ping` vẫn public để nền tảng health-check.
- Mỗi monitoring session giữ ByteTrack trong memory của một worker. Bản thử nghiệm nên dùng một worker; scale nhiều worker chỉ an toàn sau khi cấu hình worker affinity hoặc chuyển tracking state ra khỏi process.

## Chạy tách riêng trên máy local

Cài và chạy dự án như cũ bằng `make setup` và `make run` vẫn dùng model local. Để kiểm tra đường remote:

1. Terminal thứ nhất chạy vision worker:

   ```bash
   make vision-worker-run
   ```

2. Kiểm tra health:

   ```bash
   curl http://localhost:8100/ping
   ```

3. Trong `.env.development`, đặt:

   ```dotenv
   VISION_PROVIDER=remote
   VISION_REMOTE_URL=http://127.0.0.1:8100
   VISION_REMOTE_API_KEY=
   VISION_REMOTE_TIMEOUT_SECONDS=5
   ```

4. Terminal thứ hai chạy ứng dụng chính:

   ```bash
   make run
   ```

Muốn thử auth local, khởi động worker với `VISION_WORKER_API_KEY=dev-secret make vision-worker-run` và đặt cùng giá trị ở `VISION_REMOTE_API_KEY`.

## Build image CPU độc lập

Image hiện tại cố ý dùng PyTorch CPU để chứng minh boundary trước khi tối ưu CUDA:

```bash
make vision-worker-image
docker run --rm -p 8100:8000 --name p047-vision p047-vision:dev
curl http://localhost:8100/ping
```

Để publish:

```bash
docker tag p047-vision:dev DOCKERHUB_USERNAME/p047-vision:cpu-v1
docker login
docker push DOCKERHUB_USERNAME/p047-vision:cpu-v1
```

Không dùng tag mutable `latest` cho production. Model checkpoint đã được copy vào image nên image khá lớn; lần build đầu sẽ mất thời gian do tải PyTorch CPU.

## Deploy proof-of-separation không cần GPU

Cách ít biến số nhất ở giai đoạn này là tạo service thứ hai trên Railway hoặc nền tảng container CPU bất kỳ:

- Image: `DOCKERHUB_USERNAME/p047-vision:cpu-v1`.
- Port: dùng biến `PORT` của nền tảng; image đã đọc biến này.
- Health path: `/ping`.
- Replica: `1`.
- Biến worker: `PPE_MODEL_PATH=models/yolo11m_safety.pt`, `VISION_MODEL_VERSION=yolo11m_safety-cpu-v1`, và một `VISION_WORKER_API_KEY` bí mật.

Sau khi worker trả health, đặt trên service backend Railway. Khi hai service nằm trong cùng project/environment, ưu tiên private networking:

```dotenv
VISION_PROVIDER=remote
VISION_REMOTE_URL=http://${{vision-worker.RAILWAY_PRIVATE_DOMAIN}}:${{vision-worker.PORT}}
VISION_REMOTE_API_KEY=${{vision-worker.VISION_WORKER_API_KEY}}
VISION_REMOTE_TIMEOUT_SECONDS=5
```

Redeploy backend rồi gọi lại flow inference hiện hữu. Nếu cần rollback tức thời, chỉ đổi `VISION_PROVIDER=local` và redeploy; browser contract không thay đổi.

## Đưa cùng image lên RunPod Serverless sau đó

RunPod Load Balancer nhận custom FastAPI image và forward trực tiếp HTTP, phù hợp hơn queue endpoint cho frame realtime. Quy trình proof:

1. Push `p047-vision:cpu-v1` lên Docker Hub hoặc registry mà RunPod đọc được.
2. Tạo Serverless Load Balancer endpoint từ image đó, expose container port `8000`, health path `/ping`, và cấp đủ container disk cho image/model.
3. Giữ một worker để bảo toàn ByteTrack của một camera. `active workers = 0` tiết kiệm chi phí nhưng request đầu chịu cold start; `active workers = 1` giảm latency nhưng tính phí liên tục.
4. Đặt `VISION_REMOTE_URL` trên Railway thành URL Load Balancer endpoint và `VISION_REMOTE_API_KEY` thành RunPod API key. Không đặt `VISION_WORKER_API_KEY` trong container nếu RunPod đã kiểm soát `Authorization` ở gateway.
5. Kiểm tra `/ping`, sau đó gửi một JPEG nhỏ qua `/v1/infer` trước khi bật `VISION_PROVIDER=remote` trên backend.

RunPod Serverless hiện vẫn yêu cầu chọn GPU cho endpoint worker. Image CPU này chạy được để kiểm tra contract nhưng không tận dụng GPU và không phải cấu hình kinh tế/latency cuối cùng. Bước sau mới thay base image/PyTorch bằng CUDA, benchmark vùng gần Railway/streamer, cấu hình worker affinity và đặt active worker theo SLA.

## Điều kiện xác nhận deploy thành công

- `/ping` trả `healthy`, `safety_vision_v1` và đúng model version.
- Backend khởi động thành công ở `VISION_PROVIDER=remote`; nếu worker không sẵn sàng thì backend fail-closed thay vì âm thầm dùng local model.
- Một frame từ REST/WebSocket hoặc vòng RTSP server-side giữ nguyên response/metadata hiện tại và có bbox/track ID hợp lệ.
- Worker không có credential PostgreSQL, S3, Telegram hoặc OpenAI.
- Log không chứa JPEG, bearer token hoặc response body chi tiết từ provider.
