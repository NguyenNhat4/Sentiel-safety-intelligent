# Tách Safety Vision worker và triển khai thử

## Mục tiêu và phạm vi hiện tại

Lát cắt này tách phần YOLO11n Safety KD và ByteTrack ra thành một FastAPI process độc lập. Backend chính giữ nguyên REST/WebSocket phía trình duyệt, rule PPE/vùng nguy hiểm, vòng đời occurrence, HITL, database, snapshot và notification.

Luồng production hiện tại:

```text
Backend đọc image/video từ media volume
  -> Railway backend lấy frame ở nhịp giới hạn và gọi FrameInferenceService
    -> RemoteVisionAdapter mã hóa JPEG
    -> POST /v1/infer tới vision worker
      -> YOLO11n Safety KD + ByteTrack
      <- bbox person/hat/vest + track_id
    <- contract safety_vision_v1
  -> Railway áp rule, deduplicate và publish metadata camera
  -> Browser phát asset được xác thực và nhận overlay qua WebSocket hiện hữu
```

Vision worker không đọc media trực tiếp; backend tiếp tục sở hữu asset, camera configuration, sampling, session, rule, review và toàn bộ persistence. Worker v2 không giữ state giữa request và không có `DATABASE_URL`, nên frame tiếp theo có thể đến replica khác mà vẫn tiếp tục đúng `track_id` và PPE anti-flicker. v1 vẫn tồn tại để rollback nhưng giữ tracker trong RAM.

## Contract của worker

- `GET /ping`: health không tải ảnh, trả contract/model version.
- `POST /v1/infer`: multipart gồm JPEG `image`, UUID `request_id`, và `monitoring_session_id` tùy chọn.
- `GET /v2/ping`: health cho contract `safety_vision_v2`.
- `POST /v2/infer`: thêm UUID session, `frame_id`, `state_revision` và JSON state tùy chọn; response trả lại correlation cùng next state đã validation.
- Worker đọc tối đa 8 MiB cho mỗi JPEG và trả `413` nếu vượt giới hạn; bounding box remote phải có tọa độ không âm, kích thước/thứ tự hợp lệ.
- State v2 tối đa 512 KiB, chỉ nhận số hữu hạn và vector/matrix ByteTrack có dimension cố định; không nhận pickle hoặc class import động.
- Response chỉ chứa canonical people, PPE observation và model detections. Worker không truy cập PostgreSQL hoặc S3.
- `VISION_WORKER_API_KEY` là tùy chọn cho deployment trực tiếp. Khi có giá trị, cả `/v1/infer` và `/v2/infer` yêu cầu `Authorization: Bearer <key>`; hai health route vẫn public.
- v2 lưu state kỹ thuật trong PostgreSQL backend bằng revision/frame CAS, TTL mặc định 24 giờ và xóa khi session kết thúc. v1 chỉ an toàn với một worker hoặc worker affinity.

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
   VISION_REMOTE_CONTRACT_VERSION=safety_vision_v2
   VISION_TRACKING_STATE_TTL_SECONDS=86400
   VISION_TRACKING_STATE_MAX_BYTES=524288
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
- Biến worker: `PPE_MODEL_PATH=models/yolo11n_safety_kd_best.pt`, `VISION_MODEL_VERSION=yolo11n_safety_kd-cpu-v1`, và một `VISION_WORKER_API_KEY` bí mật.

Sau khi worker trả health, đặt trên service backend Railway. Khi hai service nằm trong cùng project/environment, ưu tiên private networking:

```dotenv
VISION_PROVIDER=remote
VISION_REMOTE_URL=http://${{vision-worker.RAILWAY_PRIVATE_DOMAIN}}:${{vision-worker.PORT}}
VISION_REMOTE_API_KEY=${{vision-worker.VISION_WORKER_API_KEY}}
VISION_REMOTE_TIMEOUT_SECONDS=5
VISION_REMOTE_CONTRACT_VERSION=safety_vision_v2
VISION_TRACKING_STATE_TTL_SECONDS=86400
VISION_TRACKING_STATE_MAX_BYTES=524288
```

Chạy Alembic migration trước khi chọn v2. Nếu cần rollback tức thời, đổi `VISION_REMOTE_CONTRACT_VERSION=safety_vision_v1` và giữ một worker/affinity, hoặc đổi `VISION_PROVIDER=local`; browser contract không thay đổi.

## Build image GPU cho RunPod

Image GPU là artifact riêng; image CPU phía trên vẫn được giữ để test local và rollback:

```bash
make vision-worker-gpu-image
docker tag p047-vision:gpu-dev DOCKERHUB_USERNAME/p047-vision:gpu-v1
docker login
docker push DOCKERHUB_USERNAME/p047-vision:gpu-v1
```

Trước khi thuê RunPod, có thể đưa nhánh cho một máy Linux có NVIDIA GPU và chạy đúng một lệnh:

```bash
make vision-worker-benchmark
```

Lệnh tự build image rồi đo cùng YOLO11m Safety + ByteTrack trên CPU và `cuda:0`, mặc định warm-up
10 lần và đo 50 lần trên frame tổng hợp 640×640. Kết quả in mean/P50/P95, FPS và hệ số GPU nhanh
hơn CPU. Để đo sát camera hơn, đặt một ảnh đã được phép sử dụng trong repository rồi chạy:

```bash
make vision-worker-benchmark BENCHMARK_INPUT=data/authorized-test.jpg
```

Máy test phải chạy được `nvidia-smi` và Docker phải được cấu hình NVIDIA Container Toolkit.
Benchmark này loại trừ model load, warm-up, decode video và network; nó đo Ultralytics
preprocess, YOLO inference, postprocess và ByteTrack. Không dùng kết quả này để suy ra cold start
hoặc độ trễ Railway–RunPod.

`Dockerfile.ai.gpu` pin Python 3.11, PyTorch `2.9.1`, torchvision `0.24.1` và CUDA wheel `cu128`. Image đặt sẵn `VISION_DEVICE=cuda:0`; worker sẽ từ chối startup nếu container không nhìn thấy CUDA. Vì vậy có thể build image trên máy CPU, nhưng chỉ chạy API đầy đủ khi Docker host được cấp NVIDIA GPU.

Có thể xác nhận image chứa đúng CUDA runtime mà không khởi động API:

```bash
docker run --rm --entrypoint python p047-vision:gpu-dev \
  -c "import torch; print(torch.__version__, torch.version.cuda)"
```

Kết quả mong đợi là Torch `2.9.1` và CUDA `12.8`. `torch.cuda.is_available()` chỉ trả `true` khi container thực sự được RunPod cấp GPU.

## Deploy GPU lên RunPod Serverless Load Balancer

Load Balancer nhận custom FastAPI image và forward trực tiếp HTTP, phù hợp hơn queue endpoint cho frame realtime. Quy trình triển khai:

1. Push một tag immutable mới chứa đồng thời v1/v2 lên Docker Hub hoặc registry mà RunPod đọc được.
2. Tạo Serverless Load Balancer endpoint từ image đó, expose HTTP container port `8000`, health path `/ping`, chọn GPU tương thích CUDA 12.8 và cấp đủ container disk cho image/model.
3. Giữ Railway ở v1, kiểm tra `/ping`, `/v2/ping`, một request `/v1/infer` và một chuỗi `/v2/infer` có state trước khi thay backend.
4. Áp dụng migration `20260825_01`, deploy backend vẫn ở v1, rồi đặt `VISION_REMOTE_URL`, `VISION_REMOTE_API_KEY` và `VISION_REMOTE_CONTRACT_VERSION=safety_vision_v2`. Không đặt `VISION_WORKER_API_KEY` trong container nếu RunPod đã kiểm soát `Authorization` ở gateway.
5. Chạy một session liên tục qua restart/replica, xác nhận revision tăng, `track_id` và PPE anti-flicker không reset. Sau bằng chứng này mới tăng `max workers`; `active workers = 0` vẫn có cold start, còn `active workers = 1` giảm first-frame latency.

Các biến tối thiểu trên RunPod:

```dotenv
PORT=8000
PPE_MODEL_PATH=models/yolo11m_safety.pt
VISION_DEVICE=cuda:0
VISION_MODEL_VERSION=yolo11m_safety-gpu-v1
```

Không đưa `DATABASE_URL`, S3, Telegram hoặc credential Railway vào worker. Nếu dùng private registry, khai báo registry credential trong RunPod thay vì bake vào image.

RunPod tính GPU Serverless theo thời gian worker thực sự chạy. `active workers = 0` phù hợp cho thử nghiệm vì không giữ GPU khi idle; cần đặt spending limit/billing alert trong tài khoản và kiểm tra bảng giá hiện hành trước khi bật worker luôn ấm.

## Điều kiện xác nhận deploy thành công

- `/ping` trả `healthy`, `safety_vision_v1` và đúng model version.
- `/v2/ping` trả `healthy`, `safety_vision_v2`; request v2 đầu tiên tạo revision 1 trong PostgreSQL.
- Log startup không có lỗi CUDA và một lần infer thực tế xác nhận `torch.cuda.is_available()` là `true` trong worker.
- Backend khởi động thành công ở `VISION_PROVIDER=remote`; nếu worker không sẵn sàng thì backend fail-closed thay vì âm thầm dùng local model.
- Một direct-file session giữ nguyên numeric track ID và trạng thái PPE qua ít nhất hai replica hoặc một worker restart; row state bị xóa khi session kết thúc.
- Worker không có credential PostgreSQL, S3, Telegram hoặc OpenAI.
- Log không chứa JPEG, bearer token hoặc response body chi tiết từ provider.
- Rollback về v1 được smoke với `max workers = 1` hoặc affinity, sau đó có thể bật lại v2 mà không đổi browser/rule contract.
