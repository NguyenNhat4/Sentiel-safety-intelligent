# Quy Trình Triển Khai Hệ Thống (Deployment Flow & Team Runbook)

Tài liệu này chi tiết hóa luồng triển khai hệ thống **P-047** lên hạ tầng **Railway**, phục vụ việc phối hợp giữa các thành viên trong team khi thực hiện deploy thủ công qua script `scripts/deploy_all_production.sh`.

---

## 1. Luồng Chạy Script Deployment (`scripts/deploy_all_production.sh`)

Sơ đồ bên dưới mô tả thứ tự thực hiện các bước khi chạy script deploy từ máy cá nhân:

```mermaid
flowchart TD
    Start(["🚀 Bắt đầu: ./scripts/deploy_all_production.sh"]) --> CheckTools{"1. Kiểm tra CLI Tools<br/>(docker, railway, jq, curl)"}

    CheckTools -- Thiếu tool --> FailTool["❌ Thông báo lỗi & Dừng execution"]
    CheckTools -- Đủ tool --> ReleaseChecks["2. Chạy Release Checks (Local Gates)"]

    subgraph ReleaseChecksGroup ["Chi tiết Release Checks"]
        direction TB
        PyTest["Backend HLS Test<br/>pytest backend/tests/test_hls_access.py"]
        StreamerTest["Streamer Test<br/>make streamer-test"]
        FrontLint["Frontend Lint & Vitest<br/>npm run lint && npm test HlsVideo"]
        FrontBuild["Frontend Production Build<br/>npm run build"]
        PyTest --> StreamerTest --> FrontLint --> FrontBuild
    end

    ReleaseChecks --> ReleaseChecksGroup
    ReleaseChecksGroup -- Test/Build Lỗi --> FailCheck["❌ Dừng Deploy (Code chưa sẵn sàng)"]
    ReleaseChecksGroup -- Passed All --> FetchPrevID["3. Lấy Deployment ID hiện tại trên Railway<br/>(railway deployment list --json)"]

    FetchPrevID --> BuildPushApp["4. Build & Push App Image<br/>Docker build & push nguyennhat4/p047:latest"]
    BuildPushApp --> BuildPushStreamer["5. Build & Push Streamer Image<br/>Docker build & push nguyennhat4/streamer:dev1"]

    BuildPushStreamer --> RailwayRedeploy["6. Kích hoạt Railway Redeploy<br/>railway redeploy --from-source"]

    subgraph RailwayPoll ["7. Polling trạng thái Railway (Mỗi 10s)"]
        direction TB
        PollStatus{"Trạng thái Deployment?"}
        PollStatus -- SUCCESS --> AppOk["App & Streamer Ready"]
        PollStatus -- FAILED / TIMEOUT --> AppFail["❌ Railway Deploy Failed"]
        PollStatus -- IN_PROGRESS --> Wait["Sleep 10s & Poll lại"]
        Wait --> PollStatus
    end

    RailwayRedeploy --> RailwayPoll
    AppFail --> FailDeploy["❌ Triển khai thất bại"]
    AppOk --> HealthCheck["8. Kiểm tra Health Endpoints (curl)"]

    subgraph HealthCheckGroup ["Kiểm tra Healthcheck HTTPS"]
        curlApp["curl https://p047-production.up.railway.app/health"]
        curlStreamer["curl https://streamer-production-3002.up.railway.app/health"]
    end

    HealthCheck --> HealthCheckGroup
    HealthCheckGroup -- Both 200 OK --> Success(["✅ Deploy thành công hoàn tất!"])
    HealthCheckGroup -- HTTP Error / Timeout --> FailHealth["❌ Endpoint Unreachable"]
```

---

## 2. Phân Định Dịch Vụ Trên Railway (Service Matrix)

| Dịch vụ | Service Name trên Railway | Dockerfile | Nhiệm vụ chính | Healthcheck Endpoint |
|---|---|---|---|---|
| **App Main** | `p047-app` | `/Dockerfile` | FastAPI Backend, React Frontend, YOLO Vision Inferences, PostgreSQL Auth/Events | `https://p047-production.up.railway.app/health` |
| **Streamer** | `streamer` | `/streamer/Dockerfile` | HLS / RTSP Gateway proxy, MediaMTX streaming plane | `https://streamer-production-3002.up.railway.app/health` |

---

## 3. Yêu Cầu Chuẩn Bị Cho Team (Onboarding Checklist)

Để một thành viên mới trong team có thể chạy được script deployment, Admin cần cung cấp và thành viên cần chuẩn bị các thông tin sau:

1. **Công cụ hệ thống (CLI)**: Cài đặt `docker`, `railway`, `jq`, `curl`, `make`, `npm`.
2. **Quyền tài khoản**:
   - Invite vào **Railway Workspace/Project** (`3aeb66d7-0d02-4a6d-a9e8-57cac403b049`).
   - Phân quyền Push vào Docker Hub repositories (`nguyennhat4/p047` và `nguyennhat4/streamer`).
3. **Đăng nhập CLI ở máy cá nhân**:
   ```bash
   docker login
   railway login
   ```
4. **Tạo file `.env.production` ở gốc dự án**:
   ```env
   VITE_STREAMER_URL=https://streamer-production-3002.up.railway.app
   VITE_MEDIA_PUBLIC_ORIGIN=https://p047-production.up.railway.app
   VITE_STREAM_TRANSPORT=hls
   ```
5. **Cấu hình môi trường local**:
   ```bash
   make setup
   ```
