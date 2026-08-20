# CI/CD và Railway release

Tài liệu này hướng dẫn một thành viên mới cấu hình pipeline và đưa image mới lên Railway. Local development vẫn chỉ cần `make setup` rồi `make run`; không cần Railway token để chạy local.

## Luồng release

1. Mở pull request vào `main`. CI chạy độc lập các check Ruff/format, root Python tests, backend/vision tests, frontend lint/type-check/Vitest/build và Docker build.
2. Sau approval và mọi required check xanh, GitHub auto-merge PR vào `main`.
3. Workflow `Deploy Railway` chỉ chạy khi workflow CI của `main` thành công. CI đã push Docker Hub image `:latest`, sau đó workflow gọi `railway redeploy` để Railway pull image mới, rồi poll `GET /health` tối đa 10 phút.
4. Deploy chỉ thành công khi response health có `ready: true`; điều này yêu cầu model, PostgreSQL và S3 đều sẵn sàng.

`workflow_run` tách deploy khỏi event push/PR. Không bật Railway GitHub auto-deploy, vì điều đó có thể deploy commit chưa qua health gate.

## Cấu hình GitHub

Thêm các repository Actions secrets sau. Không gửi giá trị secret qua chat, issue hoặc pull request.

| Nơi lưu | Tên | Giá trị |
| --- | --- | --- |
| Repository secret | `DOCKERHUB_USERNAME` | Docker Hub username có quyền push image |
| Repository secret | `DOCKERHUB_TOKEN` | Docker Hub access token có quyền Read & Write |
| Repository secret | `DOCKERHUB_IMAGE` | Docker Hub image name, ví dụ `owner/p047` |
| Repository secret | `RAILWAY_TOKEN` | Railway project token có quyền redeploy service |
| Repository secret | `RAILWAY_SERVICE` | Tên hoặc ID service ứng dụng, không phải PostgreSQL service |
| Repository secret | `RAILWAY_ENVIRONMENT` | Railway environment name, thường là `production` |
| Repository secret | `PROD_BASE_URL` | Public HTTPS base URL không có `/` cuối, ví dụ `https://p047-production.up.railway.app` |
| Repository variable | `STREAMER_PUBLIC_URL` | Public HTTPS URL của streamer service riêng, ví dụ `https://p047-streamer.up.railway.app` |
| Repository variable, tạm thời | `INITIAL_RELEASE_SOURCE_BRANCH` | Đặt `develop2` cho PR release đầu tiên; xóa hoặc để trống sau khi release xong |

Trong GitHub branch protection/ruleset cho `main`, bật các điều kiện sau:

- Require a pull request before merging, với ít nhất 1 approval.
- Require status checks: `Release source`, `Backend and vision lint`, `Root Python tests`, `Backend and vision tests`, `Frontend`, `Docker build and publish`.
- Require branches to be up to date before merging.
- Block direct pushes, force pushes và branch deletion.
- Bật auto-merge sau khi đủ approval và checks.

`Release source` chỉ chặn khi `INITIAL_RELEASE_SOURCE_BRANCH` có giá trị. Đây là cấu hình tùy chọn cần owner/admin GitHub thêm; nếu không có quyền repository variable, để trống thì CI vẫn chạy bình thường.

## Cấu hình Railway

1. Tạo Docker Hub image repository khớp với secret `DOCKERHUB_IMAGE`, hoặc cấp token quyền push vào repository có sẵn.
2. Trong Railway, cấu hình service ứng dụng dùng Docker image `docker.io/<DOCKERHUB_IMAGE>:latest`, thay `<DOCKERHUB_IMAGE>` bằng giá trị secret. `RAILWAY_SERVICE` là tên/ID của service này, không phải tên project hay service PostgreSQL.
3. Tắt Railway auto-deploy từ GitHub branch. Railway chỉ nhận lệnh redeploy của workflow sau CI xanh.
4. Đặt Railway pre-deploy command là `python -m alembic upgrade head`. Đây là migration job duy nhất cho mỗi deploy.
5. Đặt `RUN_DB_MIGRATIONS_ON_START=false`, để nhiều application instance không cùng chạy migration.
6. Thêm các production Variables từ `.env.production.example`: PostgreSQL `DATABASE_URL`, S3-compatible `SNAPSHOT_STORAGE_*`, `PPE_MODEL_PATH=models/yolo11m_safety.pt`, `DATABASE_FALLBACK_ENABLED=false`, cùng `APP_ENV=production` và `CORS_ORIGINS` là public URL thật.
7. Không đặt `DATABASE_URL`, S3 credential, model config hoặc OpenAI key trong GitHub Actions. Chúng chỉ ở Railway Variables.

Streamer là service triển khai riêng, không chạy trong application service production. Build production injects `STREAMER_PUBLIC_URL` vào frontend dưới dạng `VITE_STREAMER_URL`; streamer service phải expose `GET /api/cameras`, `/stream/{camera_id}` và `/health`. Docker Compose chỉ dành cho local và chạy streamer ở `localhost:8001`.

Trước release đầu, chạy một deploy thử và gọi `<PROD_BASE_URL>/health`. Chỉ tiếp tục khi HTTP thành công và JSON có `ready: true`.

## Rollback

Image chỉ được publish với tag di động `:latest`, nên không có image revision xác định để workflow rollback tự động. Dùng Railway Deployment History để owner/team Railway chọn deployment xanh trước đó và rollback thủ công. Sau mỗi deploy, ghi SHA, thời gian và kết quả health vào release note hoặc ticket; thử rollback một lần ngay sau release đầu và xác nhận `/health` vẫn trả `ready: true`.

## Audit và xử lý lỗi

`Dependency Audit` chạy hằng đêm và có thể chạy thủ công. Audit hiện chỉ báo cáo, không chặn merge, nhằm cho team làm sạch baseline trước khi biến nó thành release gate.

Khi deploy fail, xem từng bước theo thứ tự: CI workflow của SHA, `Deploy Railway` log, Railway build/pre-deploy log, rồi JSON `/health`. Không retry mù quáng: lỗi `ready: false` thường là PostgreSQL, S3 hoặc model chưa sẵn sàng và response health đã có reason code an toàn để xác định dependency cần sửa.

## Tham khảo chính thức

- [GitHub Actions workflow events](https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows#workflow_run): hành vi và giới hạn của `workflow_run`.
- [GitHub protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches): required reviews, status checks, auto-merge, force-push và deletion restrictions.
- [Railway deployments](https://docs.railway.com/guides/deployments): pre-deploy command, healthcheck, Docker image source và GitHub autodeploy settings.
- [Railway CLI](https://docs.railway.com/guides/cli): token `RAILWAY_TOKEN`, `railway up`, service/environment options và vận hành deployment.
