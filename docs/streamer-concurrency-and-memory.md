# Streamer nhiều client: bộ nhớ, kiến trúc và cách vận hành

## 1. Tài liệu này dành cho ai?

Tài liệu này dành cho thành viên mới cần hiểu service `streamer` của P-047 mà chưa
quen FastAPI, FFmpeg hoặc MJPEG. Sau khi đọc xong, bạn cần trả lời được:

- Vì sao bộ nhớ từng tăng nhanh khi nhiều trình duyệt cùng mở camera?
- Hệ thống hiện chia sẻ video giữa các client như thế nào?
- Vì sao client chậm không làm hàng đợi frame tăng vô hạn?
- Mục tiêu 100 client đã được chứng minh đến đâu?
- Cần đo gì trước khi tuyên bố hệ thống chịu được 100 client production?

Phạm vi ở đây là đường truyền camera mô phỏng:

```text
File video → FFmpeg → FastAPI streamer → MJPEG/HTTP → React/browser
```

Đây không phải toàn bộ pipeline AI. Streamer không chạy YOLO, không kiểm tra PPE
và không tạo cảnh báo an toàn.

## 2. Các khái niệm cơ bản

### Client là gì?

Một client thường là một tab trình duyệt đang mở Live Monitor. Giao diện hiện có
thể hiển thị bốn camera, vì vậy 100 người dùng có thể tạo tới 400 kết nối MJPEG:

```text
100 browser × 4 camera = 400 HTTP stream connections
```

“100 client” và “100 kết nối” không giống nhau. Khi load test phải ghi rõ đang
đếm người dùng, tab trình duyệt hay kết nối camera.

### Frame là gì?

Frame là một ảnh JPEG trong chuỗi video. FFmpeg liên tục đọc file video, giải mã
và xuất các ảnh JPEG. FastAPI bọc mỗi ảnh trong định dạng multipart rồi gửi qua
một HTTP response không kết thúc.

### MJPEG là gì?

MJPEG là một chuỗi ảnh JPEG gửi liên tục. Browser hiển thị nó trực tiếp bằng thẻ
`<img>`, nên client đơn giản và không cần video player đặc biệt.

Đổi lại, MJPEG không nén theo thời gian như H.264/WebRTC/HLS. Mỗi client nhận gần
như toàn bộ dữ liệu ảnh của từng camera, nên băng thông tăng tuyến tính theo số
client.

## 3. Vấn đề ban đầu

Thiết kế cũ tạo một FFmpeg process mỗi khi có client gọi:

```text
Client A ─→ FFmpeg A ─┐
Client B ─→ FFmpeg B ─┼→ cùng đọc camera cam_1
Client C ─→ FFmpeg C ─┘
```

Với 100 client cùng xem một camera, hệ thống có thể tạo 100 FFmpeg process. Nếu
mỗi client xem bốn camera, con số xấu nhất có thể lên tới 400 process.

Hậu quả:

- RAM tăng theo số process.
- CPU phải giải mã cùng một video nhiều lần.
- Số thread và file descriptor tăng nhanh.
- Khi client reconnect, process cũ có thể chưa dừng nhưng process mới đã được tạo.
- Container có thể bị OOM kill dù file video trên đĩa không lớn.

Một nhầm lẫn phổ biến là coi kích thước Docker image hoặc file video là lượng RAM
đang sử dụng. Đây là ba số liệu khác nhau:

| Số liệu | Ý nghĩa |
|---|---|
| Docker image size | Dung lượng các layer trên đĩa |
| Video file size | Dung lượng media lưu trên volume |
| Process RSS | Bộ nhớ vật lý process/container đang giữ |

Khi điều tra tăng bộ nhớ, cần đo RSS và số FFmpeg process, không suy luận từ kích
thước image.

## 4. Kiến trúc hiện tại

Thiết kế hiện tại dùng một worker cho mỗi camera đang có người xem:

```text
                         ┌→ Client A
Video cam_1 → FFmpeg 1 → latest frame ─┼→ Client B
                         └→ Client C

Video cam_2 → FFmpeg 2 → latest frame ───→ các client xem cam_2
```

Các thành phần chính trong `streamer/app.py`:

- `CameraStreamManager`: quản lý worker theo đường dẫn video.
- `_SharedCameraStream`: giữ FFmpeg process và danh sách subscription của một camera.
- `_FrameSubscription`: hộp thư một ô cho một client.
- `frames_generator()`: generator mà `StreamingResponse` dùng để gửi dữ liệu.

### Luồng khi client đầu tiên kết nối

1. Browser gọi `GET /stream/cam_1`.
2. Server kiểm tra file `cam_1.mp4` tồn tại.
3. Manager tìm stream dùng chung của `cam_1`.
4. Nếu chưa có worker, server tạo đúng một task và một FFmpeg process.
5. Client đăng ký một `_FrameSubscription`.
6. Mỗi frame mới đánh thức client để FastAPI gửi frame qua HTTP.

### Luồng khi client tiếp theo kết nối

Client mới dùng lại `_SharedCameraStream` đang tồn tại. Nó không tạo FFmpeg mới.
CPU giải mã vì vậy phụ thuộc chủ yếu vào số camera đang active, không phụ thuộc
trực tiếp vào số người xem.

### Luồng khi client chậm

Subscription chỉ giữ frame mới nhất:

```text
frame 101 đến → lưu frame 101
frame 102 đến trước khi client đọc → thay frame 101 bằng frame 102
frame 103 đến → thay bằng frame 103
```

Client không phải xem đủ mọi frame. Việc bỏ frame cũ là chủ ý vì Live Monitor cần
hình ảnh gần thời gian thực hơn là phát lại đầy đủ.

Kết quả quan trọng: bộ nhớ không tăng theo số frame mà client bị chậm.

### Luồng khi client cuối cùng ngắt kết nối

Manager xóa subscription. Khi camera không còn client:

1. Stream bị xóa khỏi registry.
2. Task đọc FFmpeg bị cancel.
3. FFmpeg process được terminate.
4. Nếu process không dừng bình thường, server kill process và chờ nó kết thúc.

Upload thay video, xóa camera và shutdown ứng dụng cũng đi qua cơ chế dừng worker,
tránh tiếp tục phục vụ file cũ hoặc giữ process mồ côi.

## 5. Vì sao dùng latest-frame subscription?

### Giải pháp đã chọn

Mỗi client có một signal nhẹ và một reference tới payload mới nhất. Payload là
`bytes` immutable, vì vậy tất cả client có thể trỏ tới cùng một object mà không
cần copy ảnh JPEG.

### Lợi ích

- Chỉ một FFmpeg process cho mỗi camera active.
- Không có hàng đợi frame tăng vô hạn.
- Không copy payload cho từng client.
- Client chậm tự bỏ frame cũ nên không kéo độ trễ ngày càng xa realtime.
- Không thay đổi URL hoặc định dạng MJPEG mà frontend đang dùng.

### Trade-off

- Client chậm có thể không nhận đủ mọi frame.
- Mỗi kết nối vẫn cần state, task HTTP và socket riêng.
- Gửi frame tới nhiều client vẫn tốn băng thông và một phần CPU.
- Registry nằm trong memory của một process, nên không thể tùy ý tăng số Uvicorn
  worker hoặc replica.

Trade-off bỏ frame là phù hợp với giám sát trực tiếp. Nó sẽ không phù hợp nếu yêu
cầu nghiệp vụ là phát lại chính xác từng frame hoặc ghi hình không mất dữ liệu.

## 6. Chống proxy buffer làm tăng bộ nhớ

MJPEG response không kết thúc. Một reverse proxy có thể cố buffer response trước
khi chuyển cho client. Với stream vô hạn, buffer này có thể tiếp tục tăng.

Streamer trả hai header:

```http
Cache-Control: no-store
X-Accel-Buffering: no
```

- `Cache-Control: no-store` yêu cầu không cache nội dung camera.
- `X-Accel-Buffering: no` yêu cầu proxy tương thích Nginx chuyển dữ liệu ngay thay
  vì tích lũy response.

Đây là lớp bảo vệ quan trọng nhưng không thay thế cấu hình và quan sát thực tế của
proxy/cloud platform đang dùng.

## 7. Kết quả đo hiện có

Regression test mô phỏng 100 subscription trên một camera và xác nhận:

- Chỉ một latest-frame buffer về mặt payload.
- Tất cả subscription trỏ tới cùng object frame mới nhất.
- Frame cũ bị thay thế thay vì xếp hàng.

Phép đo synthetic với 100 client và bốn camera, tổng 400 subscription, dùng một
payload 1 MiB:

| Phiên bản | Python traced allocation |
|---|---:|
| Queue một phần tử/client | 2,393,809 bytes |
| Single-slot subscription | 1,466,009 bytes |
| Chênh lệch | giảm khoảng 39% |

Con số này chỉ đo allocation của Python trong kịch bản cô lập. Nó không bao gồm:

- RSS của FFmpeg.
- Socket buffer của hệ điều hành.
- Buffer của reverse proxy.
- Bộ nhớ browser.
- Băng thông và độ trễ mạng.
- Bốn nguồn video thật chạy đồng thời.

Vì vậy đây là bằng chứng cho việc giảm overhead subscriber, chưa phải chứng nhận
production chịu được 100 người dùng.

## 8. Giới hạn thật sự khi lên 100 client

Sau khi loại bỏ FFmpeg-per-client và backlog frame, giới hạn lớn nhất thường là
băng thông:

```text
bandwidth ≈ client × camera/client × FPS × JPEG bytes/frame
```

Ví dụ minh họa, không phải benchmark của hệ thống:

```text
100 client × 4 camera × 5 FPS × 100 KiB/frame
≈ 195 MiB/s
≈ 1.64 Gbit/s
```

Do đó “RAM đã bounded” không đồng nghĩa “100 client chắc chắn chạy tốt”. Cần khóa
độ phân giải, FPS và chất lượng JPEG phù hợp với hạ tầng mạng.

Một giới hạn khác là mô hình single-process. Nếu chạy hai Uvicorn worker hoặc hai
replica, mỗi process có registry riêng và có thể tạo FFmpeg riêng cho cùng camera:

```text
Load balancer
├── replica A → FFmpeg cam_1
└── replica B → FFmpeg cam_1
```

Hiện tại nên chạy một worker/replica cho streamer. Muốn scale ngang cần kiến trúc
media server hoặc broker dùng chung; không chỉ tăng `--workers`.

## 9. Các phương án khác và trade-off

### Một queue có giới hạn cho mỗi client

Ưu điểm: đơn giản, semantics rõ ràng. Nhược điểm: mỗi client cần queue/deque riêng
và publish phải thao tác queue cho từng frame. Đây là thiết kế trước bước tối ưu
single-slot.

### WebSocket gửi JPEG

Ưu điểm: client kiểm soát protocol và backpressure rõ hơn. Nhược điểm: browser
không thể chỉ dùng `<img>`, phải decode/render frame bằng JavaScript; vẫn tốn nhiều
băng thông vì dữ liệu vẫn là các JPEG độc lập.

### HLS

Ưu điểm: cache/CDN tốt, phù hợp nhiều viewer. Nhược điểm: latency thường cao hơn,
cần segment/playlist và player phía client. Hợp với xem broadcast hơn phản hồi gần
realtime.

### WebRTC

Ưu điểm: latency thấp, codec hiệu quả và có cơ chế thích nghi mạng. Nhược điểm:
signaling, NAT traversal, TURN và vận hành phức tạp hơn đáng kể.

### Media server chuyên dụng

Ưu điểm: fan-out, transcoding và scale ngang tốt hơn. Nhược điểm: thêm service,
chi phí vận hành và observability. Đây là hướng phù hợp nếu load test cho thấy
MJPEG single-process không đáp ứng mục tiêu production.

### Shared frame broker bên ngoài process

Redis Pub/Sub hoặc broker tương tự giúp nhiều replica nhận frame. Tuy nhiên đẩy
ảnh tốc độ cao qua broker tạo tải mới, và Pub/Sub không tự giải quyết transcoding
hay băng thông tới client. Không nên thêm chỉ để “có scale ngang” khi chưa đo.

## 10. Kế hoạch load test 100 client

### Trước khi chạy

Ghi rõ kịch bản:

- 100 client hay 100 kết nối?
- Mỗi client xem một hay bốn camera?
- Độ phân giải, FPS và JPEG quality là bao nhiêu?
- Test trong bao lâu: tối thiểu nên có giai đoạn ổn định 15–30 phút.
- Chạy trực tiếp hay qua đúng proxy/domain production?

### Chỉ số cần thu thập

| Nhóm | Chỉ số |
|---|---|
| Bộ nhớ | RSS streamer, RSS từng FFmpeg, memory theo thời gian |
| Process | Số FFmpeg, thread và file descriptor |
| CPU | Streamer CPU và tổng FFmpeg CPU |
| Client | Thời gian tới frame đầu, FPS nhận được, reconnect/error |
| Mạng | Outbound throughput, connection count, dropped connection |
| Vòng đời | Worker còn lại sau disconnect, replace, delete và shutdown |

### Điều kiện đạt đề xuất

- Số FFmpeg bằng số camera đang được xem, không bằng số client.
- RSS đạt plateau thay vì tiếp tục tăng theo thời gian.
- Sau khi toàn bộ client disconnect, worker và RSS quay về gần baseline.
- Không có client tích lũy độ trễ ngày càng lớn.
- Tỷ lệ lỗi/reconnect và thời gian tới frame đầu nằm trong ngưỡng sản phẩm chấp nhận.
- Băng thông không vượt giới hạn service hoặc network egress.

### Các bước tăng tải

Không nhảy thẳng lên 100. Chạy cùng một kịch bản ở 1, 10, 25, 50 và 100 client.
Giữ nguyên camera, video, FPS, thời lượng và môi trường để kết quả so sánh được.

Sau mỗi mức tải:

1. Chờ hệ thống ổn định.
2. Ghi CPU/RSS/băng thông và số process.
3. Ngắt toàn bộ client.
4. Xác nhận worker được dọn.
5. Chỉ tăng tải nếu mức trước không có memory growth hoặc lỗi vòng đời.

## 11. Cách kiểm tra khi bộ nhớ lại tăng

Đi theo thứ tự sau:

1. Đếm FFmpeg process. Nhiều hơn số camera active thường là lỗi lifecycle hoặc
   chạy nhiều worker/replica.
2. Tách RSS streamer khỏi RSS FFmpeg và backend AI.
3. Kiểm tra số connection có giảm sau khi browser đóng hay không.
4. Kiểm tra proxy có tôn trọng streaming/no-buffer hay không.
5. So sánh RSS ngay sau khởi động, khi có tải, và sau khi ngắt toàn bộ tải.
6. Kiểm tra camera replace/delete có đóng client và dừng worker cũ.
7. Chỉ chụp heap Python khi đã xác nhận phần tăng nằm ở process streamer Python.

Nếu RSS tăng nhưng Python heap ổn định, nghi ngờ FFmpeg, socket/native buffer hoặc
proxy trước khi tiếp tục tối ưu object Python.

## 12. Quy tắc vận hành hiện tại

- Chạy streamer với một Uvicorn worker và một replica.
- Không bật cache cho `/stream/*`.
- Không thay latest-frame slot bằng queue không giới hạn.
- Khi sửa lifecycle, phải test disconnect, FFmpeg exit, replace, delete và shutdown.
- Khi thay FPS, resolution hoặc JPEG quality, phải đo lại băng thông và CPU.
- Không tuyên bố “đạt 100 client” chỉ từ unit test; cần load test qua môi trường
  deployment thật.

## 13. Tóm tắt quyết định

Vấn đề chính không phải file video lớn mà là công việc và buffer bị nhân theo số
client. Giải pháp hiện tại chia sẻ một FFmpeg worker cho mỗi camera, chỉ giữ frame
mới nhất cho từng subscriber, chia sẻ cùng payload và yêu cầu proxy không buffer.

Thiết kế này giảm RAM/CPU mà không đổi contract MJPEG của frontend. Trade-off là
client chậm sẽ bỏ frame và hệ thống vẫn bị giới hạn bởi băng thông MJPEG cùng mô
hình single-process. Vì vậy bước tiếp theo để chốt capacity là load test 100 client
trong đúng cấu hình deployment, không phải tiếp tục thêm abstraction khi chưa đo.
