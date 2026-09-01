# Project Progress

### 2026-09-01 Dashboard real event statistics

- [Backend] Removed the fabricated minimum-100 detection denominator and synthetic compliance calculation. Statistics now return real persisted counts for official violations, pending review and false alarms, globally and per authorized camera; legacy compliance values are nullable rather than invented.
- [Frontend] Replaced the misleading compliance percentage and “lượt phát hiện” rows with three auditable KPI counts and per-camera status breakdowns.
- [Verification] Area Dashboard regressions pass 3/3, the full frontend suite passes 117/117, production build, type-check, Ruff, formatting and `git diff --check` pass. Database-backed focused backend execution remains subject to the existing root pytest hang. Railway deployment was not run.

### 2026-09-01 Uploaded media names across camera surfaces

- [Backend/Frontend] The media name entered during upload now resolves as the assigned camera's display name in camera-configuration/event contracts, camera-grouped statistics, Live Monitor, configuration, Dashboard, pending alerts and violation logs. Event summaries prefer that camera name while retaining the distinct configured zone name for zone fields and overlays.
- [Backend] Area Manager accounts without a camera/area assignment now receive an empty events/statistics dashboard instead of HTTP 403; no plant-wide data is exposed by this fallback.
- [Verification] Focused frontend camera/dashboard/event-log tests pass 36/36, the full frontend suite passes 117/117, production build, type-check, Ruff, formatting, deterministic incident-summary regression and `git diff --check` pass. Database-backed focused backend tests reached the existing test-environment hang and timed out without a result. Railway deployment was not run.

### 2026-09-01 Unified sidebar navigation icons

- [Frontend] Replaced the mixed Unicode sidebar symbols with a cohesive, dependency-free SVG outline set for Live Monitor, violation history, system observation, dashboard, administration, and media library. Icons inherit the existing active/inactive colors and remain decorative so accessible button names are unchanged.
- [Verification] Focused App navigation tests pass 10/10 and the full frontend suite passes 117/117; frontend type-check, production build, lint with the existing `StreamViewer.tsx` hooks warning, Ruff, formatting, and `git diff --check` pass. `make check` reached the root pytest suite and timed out after its first passing test. Railway deployment was not run.

### 2026-09-01 Testing and product quality documentation

- [Cross-cutting] Added a standalone testing document covering quality objectives, scope, test levels, critical functional test matrix, local/CI commands, acceptance and release gates, defect management, evidence retention, ownership, and handoff checklist.
- [Verification] The document distinguishes the latest confirmed frontend 116/116 result from the known Python legacy/contract failures instead of claiming a fully green repository. Documentation indexes and the maintained project structure were updated. Application tests/build and Railway deployment were not run for this documentation-only change.

### 2026-09-01 Detailed weekly team log

- [Cross-cutting] Added a standalone five-week team work log derived from repository commit history, covering weekly objectives, implementation work, integration difficulties, resolutions, outcomes, and representative commit references from 2026-07-23 through 2026-08-31.
- [Documentation] Indexed the weekly log in the repository context map and recorded it in the maintained current project structure.
- [Verification] `git diff --check` passes. This is a documentation-only change, so application tests/build and Railway deployment were not run.

Updated: 2026-08-31

### 2026-08-31 HITL snapshot preload before popup

- [Frontend] Live Monitor and Camera Detail now preload each persisted HITL snapshot before making the review popup visible. Live Monitor reserves the active FIFO alert while loading so later zone alerts cannot overtake it; snapshot failure or a five-second timeout opens the popup with an explicit unavailable-image state instead of hiding the alert indefinitely.
- [Verification] Focused Live Monitor and Camera Violation Log regressions pass 18/18; the full frontend suite passes 117/117. Frontend type-check, production build, lint with the existing `StreamViewer.tsx` hooks warning, and `git diff --check` pass. The local Docker image rebuilt successfully and both containers report healthy. `make check` passes all frontend/Ruff stages, then times out in the root pytest stage after its first test. Railway deployment was not run.

### 2026-08-31 HITL snapshot storage consistency

- [Backend] `EventService` now persists and cleans up redacted HITL snapshots through the configured filesystem/S3 provider used by the snapshot-serving route, removing the Docker production-env mismatch where writes went to local disk while reads went to S3.
- [Verification] Snapshot privacy/storage regressions pass 13/13; focused Ruff, Python compile and `git diff --check` pass. The local backend image rebuilt successfully and `/health` reports PostgreSQL and snapshot storage ready. `make check` passes Ruff, formatting, frontend lint/type-check, 116/116 frontend tests and the production build, then times out in the root pytest stage after its first test. The production-bucket write/read/delete smoke was not run because production mutation was not authorized. Railway deployment was not run.

### 2026-08-31 Decision Audit incident summary localization

- [Backend] Decision Audit summaries now translate both `missing_ppe:*` and `missing_required_ppe:*` reason keys into Vietnamese PPE labels, including `thiếu mũ bảo hộ` and `thiếu áo phản quang`. The optional LLM prompt receives localized reasons instead of technical rule IDs.
- [Verification] Focused event-audit tests, Ruff, and `git diff --check` pass. Railway deployment was not run.

### 2026-08-31 Mutually exclusive Telegram account controls

- [Frontend] The role editor now shows Telegram QR/link-generation controls only for disconnected accounts. Linked accounts replace the entire link panel with the single disconnect action; reloading after link or disconnect immediately switches to the opposite state.
- [Verification] Focused Telegram UI regression passes 1/1 and the full frontend suite passes 116/116. Frontend type-check and production build pass; lint has no errors with the existing `StreamViewer.tsx:155` hooks warning. `make check` completes all frontend and Ruff stages but its pytest launcher is blocked on Windows by Bash receiving `.venv/Scripts/pytest: Permission denied`; direct Python runs confirm 31/32 root tests and 299/316 backend/vision tests pass, with the existing SQLite migration, notification, debounce/PPE, audit/event-batch, remote-adapter, and multi-zone failures outside this UI change. Railway deployment was not run.

### 2026-08-31 Camera Detail HITL review

- [Frontend] The camera-scoped pending log reached from Live Monitor now opens a compact shared HITL review popup instead of the reviewed-event audit dialog. The popup is portalled to the document layer so it stays above the camera zone drawing and sidebar. It renders the persisted protected snapshot, violation copy, timer and VIOLATE/NORMAL actions, then transitions the same occurrence through the existing event review contract and removes the completed row; Event Detail in Audit and Area Manager remains unchanged.
- [Verification] Camera Violation Log regressions pass 6/6; the full frontend suite passes 114/114 serially. Frontend type-check and production build pass, and lint has no errors with the existing `StreamViewer.tsx:155` hooks warning. Railway deployment was not run.

### 2026-08-31 Area dashboard camera labels

- [Frontend] Area Manager compliance rows now keep the fixed `Camera 1`–`Camera 4` slot labels instead of replacing assigned-camera labels with media display names; unassigned slots still show `Chưa gán media`.
- [Backend/Frontend] Area Manager event lists, event detail/status authorization, and statistics now use assigned `managed_camera_ids` when present; legacy accounts without camera assignments retain the previous `managed_area_id` fallback. Camera-only changes also enable the account editor's save action, and dashboard statistics are matched by `camera_id` rather than response position.
- [Verification] The actual local Area Manager route returns all 23 pending events from assigned `cam_1`/`cam_2`, and its summary reports the same 23 pending events. Focused Area Manager backend tests pass 3/3 and frontend tests pass 3/3; Ruff, frontend lint/type-check, and production build pass. Broader backend event/auth/statistics coverage has two pre-existing violation-tracker debounce failures; full `make check` remains blocked by two pre-existing `CameraViolationLog` frontend failures. Railway deployment was not run.

Updated: 2026-08-30

### 2026-08-30 Telegram deep-link retry reliability

- [Backend] Multiple links generated for the same account remain independently usable until their short expiry. A matching `/start` from any active link completes the connection and consumes all outstanding challenges, avoiding false “Start not found” results from an older QR or Telegram tab.
- [Frontend] Successful completion immediately reloads the persisted account and shows the linked state; pending guidance now explicitly asks the user to open the generated link/QR rather than pressing a generic Start in an existing bot chat.
- [Verification] Auth/Telegram-link regressions pass 10/10; Ruff, frontend type-check and production build pass. Frontend lint has no errors (one pre-existing `StreamViewer` hook warning). Full `make check` reaches the frontend suite and remains blocked by two Camera Violation Log tests in the pre-existing event-filter worktree changes, unrelated to Telegram linking. Railway deployment was not run.

### 2026-08-30 Bidirectional event-status synchronization

- [Frontend] Camera Detail now queries only `unacknowledged` camera events. New persisted alerts still arrive through the existing camera WebSocket reconciliation; after Monitor or Detail changes an event to any reviewed/terminal status, shared reconciliation removes that row while Audit retains the persisted event.
- [Verification] Focused event transport/Monitor/Camera Detail/Audit regressions pass 26/26; full frontend passes 113/113, lint has no errors (one pre-existing `StreamViewer` hook warning), type-check and production build pass. `make check` reaches 31/32 root tests before the existing SQLite legacy migration failure in `20260829_02_add_manager_camera_assignments.py`. Railway deployment was not run.
- [Frontend] Follow-up diagnosis found that reviewed-event history and Area Manager detail still retained independent module caches. Both now subscribe to the shared event-update signal, reload authoritative backend state, and bypass the HTTP cache for event lists; Area Manager mutations also update its local cache immediately.
- [Verification] Follow-up regression coverage passes 32/32 across event transport, Monitor, Camera Detail, Event Detail, reviewed-event history, and Area Manager detail. Full frontend passes 113/113; lint has no errors (one pre-existing `StreamViewer` hook warning), and the production build passes.
- [Verification] Full `make check` again reaches 31/32 root tests before the same pre-existing SQLite legacy migration failure in `20260829_02_add_manager_camera_assignments.py`; the frontend and all checks before that point pass. Railway deployment was not run.

- [Frontend] Mọi review/status mutation thành công phát tín hiệu reconciliation dùng chung trong cùng tab và qua `BroadcastChannel` giữa các tab; tín hiệu chỉ chứa event/camera IDs, còn Live Monitor, Camera Detail và modal Event Detail luôn tải lại trạng thái authoritative từ backend.
- [Frontend] Camera Detail chỉ refresh khi mutation thuộc đúng camera; Live Monitor đối soát lại pending inbox, loại event đã xử lý và đóng review/toast cũ; modal đang mở tải lại audit khi đúng event thay đổi. Các request reconciliation pending/camera/detail dùng `cache: no-store` và không thêm polling hay kho event thứ hai.
- [Verification] 4 nhóm regression event API/Monitor/Camera Detail/Event Detail pass 26/26; toàn frontend pass 111/111 tests, lint không có error (còn warning `StreamViewer` có sẵn), type-check, production build và `git diff --check` pass. Full `make check` tiếp tục bị chặn bởi một lỗi SQLite legacy migration có sẵn trong `20260829_02_add_manager_camera_assignments.py`; 31/32 root tests pass trước điểm dừng. Railway deployment không được chạy.

### 2026-08-30 Live Monitor as the primary landing page

- [Frontend] Sau đăng nhập hoặc khôi phục session, `system_admin` và `safety_manager` đều mở Live Monitor trước tiên; chỉ `area_manager` mở dashboard khu vực. Thư viện media vẫn có trong navigation của System Admin nhưng không còn là trang mặc định.
- [Frontend] Thẻ tài khoản demo của System Admin hiển thị đúng đích đến Live Monitor.
- [Verification] App authentication/navigation tests, frontend lint/type-check/test/build và `git diff --check` cần được xác minh. Railway deployment không được chạy.

### 2026-08-30 Realtime camera violation-log synchronization

- [Frontend] Camera Detail subscribe camera-detection WebSocket theo đúng `camera_id` và refresh log ngay khi backend công bố `pending_event_ids`; Live Monitor và Detail tiếp tục dùng chung nguồn `safety_events`, không tạo kho log thứ hai.
- [Frontend] Không polling events API; socket tự reconnect sau lỗi và chỉ đối soát một lần khi subscribe/re-subscribe thành công để bù event được persist trong khoảng mất kết nối. Request cũ không được phép ghi đè response mới.
- [Verification] Camera configuration/log tests pass 15/15; full frontend suite pass 106/106; lint (còn một warning `StreamViewer` có sẵn), type-check, production build và `git diff --check` pass. Full `make check` đạt 291 backend/vision tests pass và còn 10 lỗi contract ngoài phạm vi thay đổi ở debounce/PPE, event batch/audit, remote adapter và multi-zone. Railway deployment không được chạy.

### 2026-08-30 Bounding-box zone membership threshold

- [Backend] Xác định xâm nhập vùng cấm khi diện tích polygon giao với box người lớn hơn 20% diện tích box của chính người đó; đúng 20%, chỉ chạm biên hoặc thấp hơn không tính. `foot_point` vẫn giữ trong payload để tương thích và debug.
- [Contracts] Cập nhật decision record, alert-rule contract và backend inference contract theo ngưỡng bounding-box overlap đã được phê duyệt.
- [Verification] 8/8 focused geometry/API tests pass; Ruff, frontend lint/type-check/test và production build pass. Toàn repo đạt 299 backend/vision tests pass, còn 10 lỗi contract nền có sẵn ở debounce/PPE, event batch/audit và remote adapter; không có lỗi mới thuộc phép tính overlap. Railway deployment không được chạy.

### 2026-08-30 Camera settings control styling

- [Frontend] Đồng bộ hình thức các control trong khối “Kiểm soát camera” theo mẫu tham chiếu: segmented BẬT/TẮT, switch PPE, select/input có khoảng đệm chữ an toàn, ngắt kết nối, vẽ/xóa vùng và nút lưu dùng màu, bo góc, trạng thái focus/disabled nhất quán.
- [Frontend] Mô tả “Vùng cấm” giải thích trực tiếp rằng polygon đã vẽ là vùng cấm và hệ thống ghi cảnh báo khi có người bước vào.
- [Frontend] Tách preview và khối thiết lập thành hai hàng flow độc lập để media không còn tràn/đè xuyên qua control; log vẫn là rail riêng, sticky trong chiều cao viewport và không thay đổi markup/nội dung.
- [Verification] Camera configuration/log tests pass 14/14; full frontend suite pass 105/105; frontend lint (còn một warning `StreamViewer` có sẵn), type-check, production build và `git diff --check` pass. Full `make check` đạt 291 backend/vision tests pass và còn 10 lỗi contract ngoài phạm vi thay đổi ở debounce/PPE, event batch/audit, remote adapter và multi-zone. Railway deployment không được chạy.

### 2026-08-30 Local setup and PR #49 merge repair

- [Cross-cutting] `make setup` completes against the local Docker PostgreSQL service; `make run` builds and serves the application on port 8000.
- [Frontend] Repaired PR #49 merge artifacts so storage-aware playback and video-time detection synchronization coexist; removed two orphaned refs. Focused StreamViewer tests pass 10/10 and the full frontend suite passes 105/105.
- [Vision/Tooling] Restored `VISION_DEVICE` wiring for the KD worker and the deterministic 640px benchmark constant; worker tests pass 11/11 and GPU benchmark tests pass 4/4.
- [Verification] Ruff, format, frontend lint/type-check/test/build, and 32 root tests pass. The full backend/Vision suite is 292 passed with the same nine pre-existing debounce/audit/event-batch/multi-zone contract failures. Local `/` returns 200; `/health` returns 200 but remains `degraded` because the current readiness policy requires S3 while local snapshot storage is filesystem. Railway deployment was not run.
### 2026-08-30 Free-text area assignment

- [Backend/Frontend] Account creation and role assignment now accept a required free-text area name, trim it before persistence, and no longer require it to match a pre-created monitoring zone. Account administration displays the stored name directly and no longer loads a zone catalog for this field.
- [Frontend] The field is labeled “Tên khu vực phụ trách” with a human-readable example instead of asking for a fixed zone ID.
- [Verification] Auth-service regressions pass 9/9; Ruff, frontend type-check and production build pass. Frontend lint has no errors (one pre-existing `StreamViewer` hook warning). Full `make check` remains blocked by two Camera Violation Log tests in the pre-existing event-filter worktree changes, unrelated to free-text area assignment. Railway deployment was not run.

### 2026-08-30 Telegram alert disconnection

- [Backend/Frontend] Added a Telegram disconnect action under the role-and-permissions tab, shown only for confirmed Telegram links. After confirmation it clears the stored Chat ID and username, so subsequent alert recipient queries exclude the account.
- [Frontend] Added an account-row shortcut that opens the Security tab with that exact account selected for administrator password reset.
- [Frontend] Made non-action areas of each account row open the role-and-permissions tab for that account, while preserving independent reset/delete controls and restyling delete as a compact destructive button.
- [Frontend] Replaced the browser-native account deletion confirmation with a white Sentinel dialog using restrained red destructive emphasis, explicit account identity, cancel, loading, and irreversible-action copy.
- [Verification] Focused auth-service tests pass 9/9, frontend auth transport tests pass 4/4, changed frontend files pass ESLint, and the production frontend build passes. The existing alert-notification suite still has its two pre-existing recipient-routing failures.

### 2026-08-29 Camera detail three-zone layout

- [Frontend] Tái cấu trúc trang chi tiết camera desktop thành một viewport: cột trái xếp preview camera ở trên và dải settings ngang gồm Nguồn/Vận hành & PPE/Vùng ở dưới; log vi phạm theo camera nằm bên phải. Trạng thái máy và yêu cầu bảo hộ được gộp trong cùng một nhóm, phân tách nội bộ để tiết kiệm diện tích. Settings dùng một surface liền khối, phân nhóm bằng divider mảnh, control cùng nhịp và footer save dùng chung khối; chỉ cuộn ngang khi thiếu chỗ, trong khi danh sách log cuộn nội bộ. Mobile giữ thứ tự Preview → Thiết lập → Log và cho phép cuộn trang.
- [Frontend] Nút Quay lại của màn cấu hình camera được chuyển từ footer lên header chung cạnh tiêu đề trang; footer chỉ giữ trạng thái draft và thao tác lưu.
- [Local runtime] Khôi phục PostgreSQL Compose cho backend local và cập nhật `.env.development` dùng cổng PostgreSQL trên host; `/api/v1/auth/me` trở lại `200` thay vì `503`. Frontend khai báo favicon SVG nội tuyến để trình duyệt không tiếp tục gọi `/favicon.ico` bị thiếu.
- [Frontend] Tăng nhẹ chiều cao dải thiết lập desktop và thu gọn nhịp dọc panel Vùng cấm để trường Tên vùng không bị footer lưu che/cắt trong lúc polygon đang ở trạng thái 0/4 điểm.
- [Frontend] Tái bố cục modal Chi tiết sự kiện theo luồng đọc trên xuống: tóm tắt, ảnh bằng chứng, rồi audit 3 bước trên một hàng; màn hình nhỏ xếp cả ba bước dọc và modal cuộn nội bộ.
- [Backend] Chặn tài khoản Quản lý khu vực chưa có `managed_area_id` đọc danh sách log và thống kê toàn hệ thống; API trả `403` rõ ràng thay vì để danh sách lọt qua rồi chi tiết trả `404`.
- [Verification] Focused camera configuration/log tests pass 14/14; frontend lint, type-check và production build pass.

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

### 2026-08-29 Frontend merge-conflict repair

- [Frontend] Hợp nhất hai thay đổi bị dán chồng trong `AuthenticatedMedia` và `StreamViewer`: giữ đồng thời định tuyến `storageBackend` và callback `onPlaybackTime` để tải media đúng backend và đồng bộ overlay theo thời gian phát.
- [Verification] Frontend type-check, production build, toàn bộ 105 test frontend và `git diff --check` pass.

## Current State

### 2026-08-25 YOLO11n Safety KD experiment

- [Vision] Runtime configuration, startup checksum validation and container packaging now target the user-supplied `yolo11n_safety_kd_best.pt`; the public `[0,3,4]` person/hat/vest contract is unchanged.
- [Vision] The former YOLO11m checkpoint remains available only for controlled rollback/benchmark. Training-code revision, dataset provenance and held-out US-13 accuracy/latency evidence for the KD checkpoint remain open gates.
### 2026-08-29 Telegram account linking

- [Backend/Frontend] System Admin can create a one-time Telegram deep link for an account, open the bot, then confirm/retry to capture the sender chat ID. Link challenges store only a digest and expire after ten minutes; bot username is discovered from the configured bot token.
- [Verification] Ruff, frontend type-check, and focused auth-service tests pass. Railway deployment was not run.

### 2026-08-29 Alembic legacy-head compatibility

- [Backend] Local PostgreSQL reported legacy revision `20260825_03` although its schema already includes `vision_tracking_states`. A no-op compatibility revision reconnects that recorded head to the current tracking-state migration history, avoiding database stamping or destructive repair.
- [Verification] `alembic upgrade head` now recognizes `20260825_03 (head)` without DDL, and focused migration tests pass 4/4. `make check` passed Ruff and all frontend checks (99/99) but its output stalled during the Vite production build before backend/root tests started.

### 2026-08-28 Confirmed-event Telegram delivery

- [Backend] Telegram delivery follows the durable event lifecycle: no message for AI-created `unacknowledged` candidates, one message on the first human-confirmed `acknowledged` transition, and no duplicate on an idempotent retry.
- [Backend] Confirmed rules are aggregated per assigned area manager, preserving zone intrusion and specific missing hat/vest labels instead of dropping same-area events or producing an empty description.
- [Known limitation] PPE-only events intentionally remain `camera_wide`; the current zone-based `managed_area_id` assignment cannot infer their Telegram recipient until a camera-wide recipient policy is chosen.
- [Verification] Six focused Telegram, reviewed-event transition, and camera-runtime tests pass. Full `make check` passes Ruff, frontend lint/type-check/build and 95/95 frontend plus 32/32 root tests; backend/vision has 293 passes and the same nine pre-existing safety debounce, summary, event-batch, and multi-zone contract failures.

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

- Railway seed behavior is documented: production startup migrates schema but intentionally does not create demo users; the staging2-only one-off seed procedure and the misleading always-visible frontend demo cards are recorded in the operations runbook.
- Camera detail now uses a responsive two-column layout: configuration/preview on the left and a camera-scoped violation log on the right, loaded through the optional `camera_id` event filter with per-event detail access and empty/error states.
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

- `models/yolo11n_safety_kd_best.pt` is the only runtime safety detector. One `[0,3,4]` call per sampled frame supplies canonical `person`, `hat`, and `vest` observations plus session-isolated ByteTrack IDs.
- Issue #43 is implemented with additive `safety_vision_v2`: workers restore/export strict JSON ByteTrack + PPE smoother state, while backend owns bounded PostgreSQL JSONB persistence, TTL cleanup and revision/frame compare-and-swap. v1 remains unchanged as the rollback contract; Railway production selected v2 after the controlled worker probe passed on 2026-08-26.
- `models/yolo11m_safety.pt` is the only runtime safety detector. One `[0,3,4]` call per sampled frame supplies canonical `person`, `hat`, and `vest` observations plus session-isolated ByteTrack IDs.
- Decoded camera frames retain their source resolution until Ultralytics performs the sole resize/letterbox operation at the configured `960x960` YOLO input boundary.
- The runtime checkpoint is the user-supplied knowledge-distilled artifact (`5480154` bytes, SHA-256 `940467d80536e1a26313bd700e33d3e7a17816659ca7346708e0dc8e03aa06c6`) under Git LFS.
- Safety Vision can run in-process or through the versioned `safety_vision_v1` HTTP worker. The backend keeps rule evaluation and persistence in both modes; local remains the default and remote is opt-in.
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

- Live Monitor buffers direct-camera video detections per camera/session and renders an overlay only when the browser's presented media time is within 200 ms of the inference result timestamp; image results remain immediate.
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

- [Cross-cutting] The playback-synchronized overlay worktree was promoted to Railway production, then production inference was aligned with `staging2`: `VISION_PROVIDER=local`, `PPE_MODEL_PATH=models/yolo11n_safety_kd_best.pt`, `YOLO_INFERENCE_IMAGE_SIZE=640`, and `MEDIA_INFERENCE_MAX_FPS=20`. Final production deployment `86f4f3b4-9028-447c-ab31-b8e42743213d` reached `SUCCESS` with image digest `sha256:8a9c56d36463ae6f96ce802583d8b7cf0b693641642870274fbe7dd26b09e24b`; local model preload completed without the prior remote-health warning, and public `/health` reports ready.

- [Frontend] Added playback-time-gated video overlays using `requestVideoFrameCallback` with metadata/time-update fallback and regression coverage for early detection delivery. Per repository policy, no local runtime was executed. Railway `staging2` deployment `dea9fc8a-4da1-4de0-8ae0-b1d6ef51f6a1` built successfully as image digest `sha256:a875a49d3d524ea66bf3af12800e115d8a088e90169e3025d05bf0a999837766`; application startup completed and public `/health` reports ready with PostgreSQL and snapshot storage ready.

- YOLO11n Safety KD cutover: the actual checkpoint hash matches the pinned SHA-256; 10 settings/startup tests and 39 Vision API/tracking tests pass. The backend PPE file has 16 passing tests and 3 pre-existing debounce expectation failures (4/immediate versus the active 7-frame contract). Ruff, format, frontend type-check, 82 frontend tests and production build pass; ESLint retains the known `App.tsx:26` warning. Full root pytest and the Railway release gate both stall in the known Starlette `TestClient` path, so the release stopped before Docker build/push and no production deployment was made.

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

- Record the YOLO11n Safety KD training-code revision and dataset provenance/license, then run held-out US-13 accuracy and target-device latency evaluation before pilot use.

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
