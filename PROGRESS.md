# Project Progress

Updated: 2026-08-27

### 2026-08-28 Stopped-machine PPE warning emphasis

- [Frontend] Khi máy ở trạng thái TẮT, thông báo PPE tạm ngừng kiểm tra dùng chữ đỏ đậm, nền đỏ nhạt và viền cảnh báo để thu hút sự chú ý; trạng thái BẬT giữ màu xanh hiện hành.
- [Verification] Camera configuration focused tests pass 10/10; frontend lint, type-check, production build và `git diff --check` pass. Railway deployment không được chạy.

### 2026-08-28 Live Monitor HITL panel alignment

- [Frontend] Panel HUMAN IN THE LOOP căn các hàng nội dung lên đầu card, không còn để CSS Grid kéo giãn khiến tiêu đề và trạng thái rỗng nằm giữa theo chiều dọc.
- [Verification] Full frontend suite pass 99/99; lint, type-check, production build và `git diff --check` pass. Railway deployment không được chạy.

### 2026-08-28 Camera configuration save feedback

- [Frontend] Sau khi người dùng bấm Lưu cấu hình và API thành công, trang cập nhật draft cùng revision từ response và hiện toast “Đã lưu”; Quay lại Live Monitor sau đó không còn bị chặn sai bởi cảnh báo draft chưa lưu. Luồng vẫn giữ nút lưu thủ công, không tự lưu khi chọn nguồn camera.
- [Verification] Camera configuration focused tests pass 10/10; full frontend suite pass 99/99; frontend lint, type-check, production build và `git diff --check` pass. Railway deployment không được chạy.

### 2026-08-28 Live Monitor viewport-fit camera grid

- [Frontend] Trên desktop từ `1181px`, Live Monitor khóa trong một viewport, chia phần camera thành grid 2x2 có bốn ô cao bằng nhau và giữ media `object-fit: contain`; danh sách cảnh báo dùng chiều cao còn lại và cuộn độc lập. Dưới breakpoint này, layout tiếp tục xếp dọc và cuộn trang như trước để không ép nhỏ camera trên tablet/mobile.
- [Verification] Focused App/Live Monitor tests pass 19/19; full frontend suite pass 99/99; lint, type-check, production build và `git diff --check` pass. Railway deployment không được chạy.

### 2026-08-28 Camera configuration shell alignment

- [Frontend] Giữ nguyên shared sidebar/shell trên màn cấu hình Camera để đồng bộ navigation, profile và trạng thái thu gọn với các trang khác; chỉ áp dụng layout compact cho phần cấu hình bên phải, với preview chữ nhật `3:2` và các control xếp dọc. Card trạng thái máy dùng segmented control BẬT/TẮT có vùng bấm lớn, `aria-pressed`, focus ring và mô tả trạng thái rõ ràng. Badge preview phản ánh kết nối camera độc lập với trạng thái máy; luồng vùng hiển thị tiến độ 0/4–4/4, hướng dẫn tại chỗ và thao tác xóa; footer giải thích save blocker; PPE bỏ nhãn ON/OFF trùng lặp. Quay lại, sidebar và đăng xuất dùng modal Sentinel để xác nhận bỏ draft chưa lưu; reload/đóng tab giữ cảnh báo native bắt buộc của trình duyệt.
- [Verification] Camera configuration focused tests pass 10/10; frontend lint, type-check, production build và `git diff --check` pass. Full frontend suite gần nhất pass 94/95; một assertion Live Monitor cũ vẫn chờ cập nhật theo wording hiện hành và không liên quan thay đổi layout. Docker build đã được hủy trước push/redeploy theo yêu cầu; Railway production không thay đổi.

### 2026-08-28 Restricted-area wording

- [Frontend] Đổi toàn bộ nhãn hiển thị còn sót lại từ “vùng nguy hiểm” thành “vùng cấm” trong Live Monitor và violation copy; giữ nguyên rule key `zone_intrusion` và runtime contract.
- [Verification] Focused wording test pass 3/3; frontend lint, type-check, production build và `git diff --check` pass. Railway release chưa vượt qua gate `backend/tests/test_us29_media_runtime.py` sau khoảng 30 giây nên chưa build/push/redeploy; production chưa thay đổi.

This file is the current project snapshot, not a chronological changelog. Use Git history for completed implementation detail. Entries are grouped by owning area so contributors can load only the context relevant to the next task.

## Current State

### 2026-08-27 System-admin Live Monitor access

- [Cross-cutting] `system_admin` has full operational authority: Live Monitor, camera configuration, simulation run/replay, event history/review, media, account administration, and operational metrics. `area_manager` remains scoped to its assigned area.
- [Verification] Merged the latest three `origin/develop2` commits while retaining the system-admin access rules and the new durable alert/toast flow. Frontend passes 95/95 tests, lint, type-check and production build; focused system-admin and alert-persistence backend tests pass. Full `make check` passes Ruff, frontend, 32/32 root tests, and 290 backend/vision tests, with the same nine pre-existing debounce, deterministic-summary, event-batch, and multi-zone contract failures.
### 2026-08-28 Backend-annotated review snapshots

- [Frontend] Review Modal và Event Detail chỉ hiển thị snapshot JPG đã được backend annotate; đã bỏ browser SVG overlay để tránh vẽ box/text hai lần.
- [Frontend] Review Modal và Event Detail vẫn render polygon + tên zone vùng cấm bằng component zone-only; không render person/PPE box hoặc confidence label.
- [Vision] Label và confidence của box snapshot được đặt ở cạnh dưới bounding box, tự co vào trong ảnh khi box sát mép dưới.
- [Verification] Frontend focused tests pass 6/6; toàn bộ frontend pass 94/94 tests, lint, type-check, production build và `git diff --check`. Release script bị stall ở backend media test trước bước build/push/redeploy; Railway production chưa thay đổi.

### 2026-08-27 Storage-aware media playback routing

- [Backend/Frontend] Media inventory now identifies filesystem versus S3 storage so Live Monitor and camera preview avoid the intentional `playback-url` 409 for local assets while retaining presigned S3 playback.
- [Verification] Frontend passes 95/95 tests, lint, type-check and production build; Ruff and `git diff --check` pass. `make check` reached the root suite and was stopped after the same unrelated stall following its first two passing tests. PostgreSQL-backed focused backend tests also stalled before producing a result. Railway deployment remains pending because the dirty worktree contains unrelated unfinished changes that cannot safely be included or discarded as part of this narrow fix.

### 2026-08-27 Durable Live Monitor violation inbox

- [Backend] Direct-camera sessions persist new review occurrences as privacy-protected `unacknowledged` safety events before WebSocket publication; reviewed submissions transition the same idempotent event.
- [Frontend] Live Monitor reloads one newest-first pending list across all four cameras. PPE uses a closeable lower-right toast without auto-opening HITL; zone alerts use one automatic FIFO popup, and closing never removes the pending row.
- [Verification] Release-focused US-29 tests pass 13/13; frontend passes 91/91 tests, lint with zero warnings, type-check and production build; Ruff and the focused runtime persistence test pass. `make check` reached the root suite and was stopped after that unrelated suite stalled. Production image build was canceled on user direction before push or Railway redeploy, so production is unchanged.

### 2026-08-24 PPE and HITL correction

- [Cross-cutting] Đã hợp nhất conflict camera configuration: `asset_id` nullable, disconnect ngoài dropdown, preview empty state và lưu được trạng thái null.
- [Vision] PPE là camera-wide, áp dụng toàn khung hình khi máy running và không phụ thuộc zone; zone intrusion vẫn không phụ thuộc machine state.
- [Cross-cutting] Đã thêm cảnh báo contract bắt buộc đọc trong `docs/architecture/alert-rule-contract.md`.

### Cross-cutting

- The MVP is a React 19 frontend, FastAPI modular monolith, Vision facade, PostgreSQL persistence, and backend-owned media assets in a Railway Bucket with an application-volume inference cache.
- Luồng local từ upload video đến playback, sampled frame inference, metadata WebSocket, SVG overlay, HITL và Replay được mô tả trong `docs/architecture/local-video-frame-flow.md` cùng source-of-truth code map.
- The standard contributor workflow remains `make setup` then `make run`; Alembic upgrades are part of that flow.
- Three authenticated roles are supported: `system_admin`, `safety_manager`, and `area_manager`. New and administrator-reset accounts must replace their temporary password.
- The implemented safety flow covers four fixed camera slots, per-camera zones/rules, direct video/image inference, Human-in-the-Loop review, immutable decision context, privacy-redacted evidence, event history, and area-scoped follow-up.
- Documentation under `docs/` is organized into `docs/architecture/`, `docs/ops/`, and `docs/data/` subdirectories; root `context-map.md` and `docs/PROJECT_STRUCTURE.md` are updated to reflect the new paths.
- Deployment flow diagrams and team runbook for `deploy_all_production.sh` and CI/CD are documented in `docs/ops/DEPLOYMENT_FLOW.md` and indexed in `context-map.md`.
- `scripts/sync_code_to_google_drive.sh` provides an opt-in rclone backup of Python source from `backend/app` and `vision` only; credentials remain in the user's rclone configuration.

### Backend

- US-29 backend runtime owns bucket-backed media assets, atomic fixed-camera configuration aggregates, and explicit direct OpenCV image/video sessions with persisted lifecycle evidence.
- Four fixed camera configurations support unique READY asset assignment and atomic camera-wide PPE saves even with no zones.
- Each configured camera can have revisioned, disjoint four-point zones and persisted rules keyed by `(camera_id, zone_id)`.
- Authenticated `/api/v1/ws/camera-detections` publishes session-correlated detection metadata for fixed cameras.
- Event persistence is idempotent by occurrence. One tracked person/session log accumulates active hat, vest, restricted-area, and zone rules; submitted human outcomes remain authoritative.
- `decision_context_v1` stores immutable observation, rule, actor, outcome, and retention deadlines. False alarms remain auditable but are excluded from official violation statistics.
- Operational metrics use a bounded, privacy-safe rotated JSONL file and support one writer process.
- PostgreSQL-only is the approved database contract. Removal and end-to-end verification of any remaining legacy SQLite defaults/fallbacks is still an open migration task.

### Vision

- Issue #43 is implemented with additive `safety_vision_v2`: workers restore/export strict JSON ByteTrack + PPE smoother state, while backend owns bounded PostgreSQL JSONB persistence, TTL cleanup and revision/frame compare-and-swap. v1 remains unchanged as the rollback contract; Railway production selected v2 after the controlled worker probe passed on 2026-08-26.
- `models/yolo11m_safety.pt` is the only runtime safety detector. One `[0,3,4]` call per sampled frame supplies canonical `person`, `hat`, and `vest` observations plus session-isolated ByteTrack IDs.
- Decoded camera frames retain their source resolution until Ultralytics performs the sole resize/letterbox operation at the configured `960x960` YOLO input boundary.
- The runtime checkpoint is the optimizer-stripped EMA FP16 artifact (`40543303` bytes, SHA-256 `e5b2ad353a33579e821ed9be77ed8406b7bac14bb8abf5d6db77b071ea021218`) under Git LFS.
- Safety Vision can run in-process or through the versioned v1/v2 HTTP worker. The backend keeps rule evaluation and persistence in both modes; local remains the development default and remote is selected explicitly in production.
- The remote worker accepts an explicit Ultralytics compute device. The RunPod image uses `cuda:0` for both inference and tracking and fails startup when CUDA is unavailable instead of silently falling back to CPU.
- RunPod Load Balancer endpoint `p047-vision` now serves the immutable dual-contract image `ntduc0112/p047-vision:gpu-v3-issue43-20260825` at digest `sha256:92e947c8b45662cb826510b4da3665a605a6926ee0dc7b1ee9678694ee8f45d1`, with one GPU per worker, FlashBoot enabled, `active workers = 0`, `max workers = 1`, and HTTP/health port `8000`.
- The 2026-08-26 controlled production probe returned HTTP 200 for both `/ping` (`safety_vision_v1`) and `/v2/ping` (`safety_vision_v2`). Direct v1 inference detected three people; direct v2 frames 1-3 retained track IDs `[1, 2, 3]`, advanced portable tracker frames 1-3, and kept serialized state near 5 KiB.
- Railway production deployment `4545db58-0f8a-40c3-bee7-1a27441cd697` switched `p047-app` to `VISION_REMOTE_CONTRACT_VERSION=safety_vision_v2` and reached `SUCCESS`; public health remained HTTP 200/ready with PostgreSQL and snapshot storage ready. A real production WebSocket session retained `[1, 2, 3]` across three frames through the PostgreSQL coordinator, and its exact `vision_tracking_states` row count was zero after disconnect. A second session retained the same IDs across a 20-second idle gap and also cleaned up, but its second-frame latency did not prove that a worker restart occurred; controlled restart/two-replica evidence remains pending.
- `make vision-worker-benchmark` provides a reproducible same-machine CPU/CUDA comparison for YOLO11m Safety + ByteTrack, with deterministic synthetic input by default and an optional authorized camera image.
- Missing PPE is derived by deterministic backend rules, not emitted by the model.
- Local inference uses anatomical PPE association and ten-frame temporal confirmation without a second backend debounce. Remote v1 inference retains six-frame backend confirmation because its contract has no local absence-confirmation metadata. An unreviewed warning retracts only after two continuous seconds of explicit presence.
- Zone intrusion opens after four consecutive sampled frames in the same active zone. Restricted-area detection remains immediate.
- Snapshot persistence runs YuNet face redaction first, falls back per person, then annotates and persists. Failure remains closed.
- Fixed-camera sessions now use isolated YOLO/ByteTrack instances concurrently, serialize only same-session access, and release model state on completion/error while retaining occurrence context for queued review.

### Frontend

- Sidebar no longer renders the unused disabled `Log JSON` placeholder tab.
- Live Monitor always renders four slots with direct video/image playback, source-coordinate overlays, server lifecycle, rolling inference FPS, and per-video Replay at EOF.
- Live Monitor reloads camera configuration, media inventory, and compatible sessions whenever the page becomes active; disconnected cameras and sessions belonging to a previously assigned asset are removed from the rendered slot.
- Camera configuration is hidden from the sidebar and opens only when `safety_manager` selects a Live Monitor slot; `system_admin` owns the media library.
- Camera configuration binds hat/vest draft state to the camera, reloads persisted switches correctly, and saves them with `zones=[]`.
- A separate developer-only Vision Compare Lab accepts JPEG/video, sends identical frames to isolated CPU and CUDA workers, renders either overlay, and reports rolling RTT, speedup, completed cycles, and skipped frames without changing the production camera path.
- HITL logs retain their own inference frame/context and are opened explicitly by the Safety Officer. Pending counts exclude reviewed logs.
- Area managers have a server-scoped compliance/event workspace and may resolve or mark false alarm only for events in their assigned area.
- Camera configuration exposes camera-wide machine state and PPE controls independently from zone creation.
- Live Monitor deduplicates occurrence IDs across people, serializes reviewed-event writes, blocks double-submit, and advances the HITL queue only after successful persistence.

### Media And Delivery

- Sys Admin uploads image/video assets directly to the Singapore Railway Bucket through presigned POST. Backend verifies metadata and the first decoded frame before `READY`; `MEDIA_ASSET_DIR` is the OpenCV read-through cache.
- Presigned GET playback preserves byte-range streaming without proxying full videos through `p047-app`. Run starts every valid configured camera; Replay creates one fresh camera session and resets playback to the beginning.
- Explicit Run starts every valid camera independently; Replay creates a fresh session for one completed video. Sessions never auto-resume after restart.
- Images infer exactly once without frame debounce. Videos stop at EOF and report inference throughput over a rolling five-second window.
- `scripts/deploy_all_production.sh` gates, publishes, redeploys, waits for Railway success, and checks the application health endpoint.
- `Dockerfile.ai` and `requirements.ai.txt` package a standalone CPU proof worker with `/ping` and `/v1/infer`; deployment remains a separate rollout step.
- `Dockerfile.ai.gpu` packages the same worker contract with pinned PyTorch `2.9.1+cu128` for RunPod; it remains an independently published immutable image.

## Latest Verification

- [Frontend] Camera Configuration đã được căn theo mẫu light-theme mới: sidebar compact, header thấp, source bar full-width, preview dọc bên trái, ba card trạng thái/vùng/PPE bên phải và footer lưu full-width. Mobile chuyển workspace thành một cột. Camera-configuration tests `7/7`, lint, type-check, production build và `git diff --check` pass.

- [Frontend] Camera Configuration now follows the reference composition with the media source bar above, a large preview/zone editor on the left, and a safety-rule panel on the right. Below 720px it stacks into one column, enlarges touch targets, and keeps the existing save, PPE, zone, and disconnect behavior. Frontend lint, type-check, production build, and the camera-configuration focused tests pass; the full frontend suite still has one pre-existing Live Monitor copy assertion failure.

- [Frontend] Live Monitor now keeps the four-camera 2x2 grid on the left and the durable pending-alert inbox on the right at desktop widths, with responsive stacking below 1180px. The application sidebar can collapse/expand, and PPE toasts close after three seconds without removing the pending event. Focused monitor tests pass `9/9`; App shell regression, browser UAT, and Railway deployment remain pending.
- Issue #43 focused verification passes `75` tests, including uninterrupted versus restore equivalence, alternating replicas, simulated worker restart, v1/v2 HTTP contracts, auth, hostile/oversized state, PostgreSQL JSONB migration, TTL and CAS conflicts. Alembic reports the single head `20260825_01` and `git diff --check` passes.
- Full `make check` has no new regression: Ruff/format/type-check/build pass, root has `32 passed`, frontend has `89 passed`, and backend/Vision has exactly the documented baseline `9 failed, 288 passed`. The same stale debounce, camera-wide PPE and audit-copy expectations remain the only failures.
- GPU image build succeeds as non-root `appuser` on `amd64`, contains Torch `2.9.1+cu128`/CUDA `12.8` and exposes `/v1/infer`, `/v2/ping`, `/v2/infer`. The immutable GPU image above and CPU proof image `ntduc0112/p047-vision:cpu-v2-issue43-20260826` (`sha256:2efadd373965435824eb645c844549d4bdbb0e496e679f64fa06cd523bb9526b`) are published.
- Railway production worktree deployment `7fa46e2a-c38e-4820-95d7-f581ece2dddb` reached `SUCCESS`; PostgreSQL applied `20260824_02 -> 20260825_01` with `PostgresqlImpl`, `/health` returns HTTP 200/ready, and the backend deliberately remains on v1. The migration-on-start switch is reset to false for the next deploy.

- Sync verification after merging `origin/develop2@ff89623` into the GPU worker branch: Ruff/format, TypeScript, frontend build, frontend `89 passed`, root `32 passed`, and focused Vision/GPU `34 passed`. The full backend/Vision suite has `9 failed, 259 passed`; the affected production and test files are identical to `origin/develop2`, where seven-frame debounce, camera-wide PPE, and updated audit wording have not yet been reconciled with older expectations.
- Camera-wide PPE, HITL duplicate-request handling, immutable occurrence ownership across track handoff, and explicit missing-hat/missing-vest wording in the HITL popup and audit views are fixed locally. PostgreSQL migration `20260824_02` adds/backfills camera-level hat/vest requirements; Railway deployment and browser UAT are intentionally pending.

- [Frontend] Camera configuration now always renders the two PPE requirement switches; users can toggle them before creating a zone, and the draft values carry into the new zone. The page actions are grouped into media, zone/safety-rule, and save/navigation sections with responsive mobile layout. Focused camera-configuration tests (6), frontend type-check, and production build pass. Railway release script reached backend 10/10 but stopped at the pre-existing `App.tsx:26` ESLint warning under `--max-warnings=0`; no production deployment was made.

- Added `scripts/clean_local_data.py` and `make clean-local-data` for explicit local-only PostgreSQL cleanup. The script preserves schema/migration history, clears configured media/snapshot/log directories, rejects Railway/production targets, and its three guard tests pass.

- `.env.development` now includes every active field from `.env.development.example`; runtime loading confirms local Vision, media paths, retention defaults, and a `4.0` per-camera inference FPS cap.
- Removed the backend `640x360` pre-resize and its coordinate-restoration pass so YOLO receives the original decoded frame; tests were updated for the new contract but not run per user request.
- Live Monitor stale-media reconciliation was updated for camera disconnect and media replacement; the production frontend bundle builds successfully, automated tests were not run per user request, and browser verification is pending.
- SQLite revision `20260824_01` repairs the US-29 active-session partial unique index, so a completed camera session no longer blocks Replay while concurrent `STARTING`/`RUNNING` sessions remain prohibited. The migration regression, Ruff, formatting, frontend lint/type-check, 76 frontend tests, and production build pass; full `make check` again stalls in the pre-existing root agent/TestClient suite after its first test.
- Local no-commit merge verification against `origin/develop2@86d34e2`: Ruff, frontend type-check, 76 frontend tests/build, 23 non-agent root tests, and 156 service/backend/vision tests pass. One pre-existing `test_settings_loads_production_env_file` assertion still conflicts with the development env-file runtime setting. Starlette `TestClient` hangs in `__enter__` even for an empty FastAPI app under the locked dependency set, so TestClient-backed suites and the two legacy agent tests could not complete locally.
- Camera-configuration regression coverage passes with both hat and vest enabled through save/reload; all 75 frontend tests and the production build pass. Full `make check` remains blocked only by the pre-existing `.env.production` expectation in `backend/tests/test_config.py`; ESLint has only the pre-existing `App.tsx` exhaustive-deps warning.
- Repository verification passes: 25 root tests, 199 backend/Vision tests, 72 frontend tests, Ruff, ESLint, TypeScript and production build.
- Railway deployment `4b593f2a-18c8-49b0-811a-d2297a2e5ad3` reached `SUCCESS`; PostgreSQL is at `20260823_01`, the app media volume is writable, `/health` is ready in production, and authenticated media/configuration/session smoke passed.
- Production Streamer and MediaMTX services were removed, the old Streamer volume was scheduled for deletion, and obsolete HLS/RTSP/Streamer variables were removed from `p047-app`.
- Server-camera inference bypasses the internal JPEG/Base64 encode-decode round trip and now preserves the original decoded frame through the backend; Ultralytics alone resize/letterboxes at the configured `960x960` model boundary. The earlier focused suite and micro-benchmark predate removal of the backend `640x360` downscale.
- The standalone `p047-vision:dev` CPU image builds successfully and its live `/ping` smoke returns `safety_vision_v1`; frontend dependency audit reports zero known vulnerabilities after the compatible `nanoid` patch update.
- `make check` passes for the CUDA worker and benchmark change: frontend `72 passed`, core/streamer `50 passed`, and backend/Vision `213 passed`. The `p047-vision:gpu-dev` image builds for `linux/amd64`, reports Torch `2.9.1+cu128` with CUDA runtime `12.8`, runs as `appuser`, and fails fast as expected on a host without an NVIDIA GPU. The benchmark has `4 passed` focused tests and completes a real synthetic CPU/ByteTrack smoke; a CUDA measurement remains intentionally pending on NVIDIA hardware.
- `make check` passes with Vision Compare Lab included: frontend `79 passed`, core/streamer `50 passed`, and backend/Vision `213 passed`; Ruff, formatting, ESLint, type-check, and production build pass. Its focused contract/UI coverage is `7 passed`, the real Vite entrypoint serves successfully, and the launcher passes shell syntax/dry-run checks. Real browser/GPU measurement remains pending because this workstation has no NVIDIA runtime and browser DevTools automation is not configured.
- Railway deployment `bfe08eab-c477-4e9f-b211-bba93166ccd0` reached `SUCCESS`; PostgreSQL is at `20260823_02`, `/health` is ready, and production completed a 31,389,527-byte direct bucket upload with `POST .../complete` returning 200 in 1.882 seconds.
- The existing `cbucket` is shared safely by prefixes: `snapshots/` for redacted evidence and `media-assets/` for uploaded media. The one legacy 26,193,014-byte volume asset was copied, size-verified, switched to S3 in PostgreSQL, and removed from canonical volume storage.
- Inference hardening now applies restricted-area rules camera-wide, closes PPE occurrences when their zone/machine requirement becomes inapplicable, runs independent camera models concurrently, drops stale sampled frames, throttles per-frame session DB writes, records direct-camera latency/drop outcomes, validates fixed-camera occurrence ownership, and restores direct-camera HITL persistence.
- Violation review alerts are now limited to one per person (`track_id`) for the full `monitoring_session_id`; later rules or re-violations remain observable without opening another review.
- Railway worktree deployment `c617b5ca-93ca-4ad1-93f2-515024d8e1a0` reached `SUCCESS`; `/health` reports production ready with PostgreSQL and snapshot storage ready. The local Docker publish path was unavailable, so the configured mutable Docker Hub source still needs republishing before a later image-source redeploy.
- RunPod `/ping` returned HTTP `200` with `safety_vision_v1` and `yolo11m_safety-gpu-v1`. A real 1280x720 project JPEG sent to `/v1/infer` returned HTTP `200`, one tracked person, and a vest observation. Railway production redeployed successfully with `VISION_PROVIDER=remote`, and its public `/health` returned `ready: true` and HTTP `200`. After enabling FlashBoot, the first measured idle recovery took 28.52 seconds and the next idle recovery took 6.74 seconds, both within the backend's 30-second timeout.
- A 2026-08-24 direct production diagnostic confirmed the RunPod image is forced to `VISION_DEVICE=cuda:0`, rejects startup when CUDA is unavailable, and returned healthy GPU-worker responses. Scale-from-zero `/ping` took 25.82 seconds; after startup, the first tracked frame for a new monitoring session took 8.00 seconds and the next frame in the same session took 1.27 seconds. An end-to-end smoke through Railway production reproduced the operational impact: the first frame returned HTTP `500` after 31.14 seconds with a logged `httpx.ReadTimeout`, then the same session returned HTTP `200` in 8.42 seconds and 1.71 seconds for the next two frames. The dominant latency is cold startup plus per-session tracking-model initialization, not a CPU fallback.

## Open Gates

- Update the RunPod `p047-vision` template to `ntduc0112/p047-vision:gpu-v3-issue43-20260825` with a management-capable credential, verify `/v2/ping` and restart/replica continuity, then set Railway `VISION_REMOTE_CONTRACT_VERSION=safety_vision_v2`. The current endpoint-restricted inference key returns 401 from the RunPod management API, so production remains safely on v1.
- Measure end-to-end direct-file inference freshness and model latency on Railway; focused evidence does not yet prove four-camera throughput.
- Complete browser UAT from upload through real-model HITL review and persisted event.
- Run browser UAT for camera configuration, two-zone save/reload, mixed rule states, overlays, grouped review, Event Detail, and Area Manager follow-up.
- Run a real 200-viewer x four-camera 30-minute soak with CPU, RSS, egress, errors, and first-frame latency before making a capacity claim.
- Complete the PostgreSQL-only runtime migration and validate the full Alembic chain against PostgreSQL.
- Add the retention cleanup scheduler for persisted US-16 metadata/snapshot deadlines.
- Complete US-13 protocol, representative ground truth, calibration/final split, accuracy thresholds, association/tracking evidence, and target-device latency.
- Configure and exercise the GitHub production environment, first protected release PR, and immutable rollback procedure.
- Benchmark cold/warm Railway-to-RunPod latency and decide between FlashBoot, a warm worker, or an explicitly accepted cold-start delay before relying on realtime alerts continuously.

## Known Limitations

- Six missing frames, two-second PPE revoke, four intrusion frames, confidence, and NMS values are MVP defaults pending held-out calibration.
- YuNet plus person fallback is fail-closed but still needs representative privacy recall and license/provenance sign-off before pilot use.
- JSONL operational metrics do not support multi-worker deployment; use a centralized sink before scaling backend workers.
- Telegram delivery is disabled until `TELEGRAM_BOT_TOKEN` and recipient chat IDs are configured; provider failure never blocks inference.
- Only three of four required local demo media assets were previously available, and browser DevTools automation is not configured.
- RunPod `active workers = 0` avoids idle GPU spend. A pre-FlashBoot cold start exceeded the backend's allowed 30-second remote timeout; FlashBoot subsequently recovered within 28.52 seconds and then 6.74 seconds, but this small first-recovery margin still needs monitoring. An always-active 16 GB tier worker removes that risk but would consume the current small credit balance quickly.

## Next Steps

0. [Frontend] Resolve the pre-existing `frontend/src/App.tsx:26` ESLint warning, redeploy the PPE-switch fix to Railway, and run browser UAT for camera configuration.
1. Prove an uploaded asset reaches model, rule, HITL log, and persisted event end to end on Railway.
2. Run the two-zone browser UAT and record results.
3. Finish PostgreSQL-only cleanup and verify `make setup`, `make run`, and migrations on a fresh environment.
4. Finalize and execute the US-13 evaluation protocol.
5. Run the four-camera capacity soak and close production readiness dependencies.
6. Implement retention cleanup and automate the proven US-08 browser sequence.
7. Run the remaining controlled RunPod restart/two-replica and v1 rollback smoke, then benchmark cold/warm latency before raising worker count.
