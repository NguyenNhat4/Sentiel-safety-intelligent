# Nhật ký làm việc hằng tuần của nhóm

## 1. Thông tin chung

- **Dự án:** P-047 – AI Agent giám sát an toàn PPE và khu vực nguy hiểm bằng Computer Vision.
- **Thời gian ghi nhận:** Từ ngày 23/07/2026 đến ngày 31/08/2026.
- **Nguồn tổng hợp:** Lịch sử commit của repository, bao gồm commit tính năng, sửa lỗi, tài liệu, kiểm thử, merge và các quyết định kỹ thuật đã được ghi nhận trong dự án.
- **Mục đích:** Ghi lại quá trình hình thành sản phẩm, cách nhóm phân chia và tích hợp công việc, các khó khăn đã gặp, hướng xử lý và kết quả đạt được qua từng tuần.

Nhật ký này tổng hợp công việc theo kết quả chung của nhóm thay vì sử dụng số lượng commit để đánh giá đóng góp cá nhân. Các merge commit, commit tự động và commit sửa lỗi nhỏ được gộp vào hạng mục chức năng tương ứng để phản ánh đúng tiến trình phát triển sản phẩm.

## 2. Tuần 1 – Khởi tạo dự án và xây dựng luồng MVP nền tảng

**Thời gian:** 23/07/2026 – 02/08/2026

### Mục tiêu của tuần

- Xác định bài toán, phạm vi MVP và kiến trúc tổng thể của hệ thống.
- Khởi tạo cấu trúc repository cho backend, frontend và tài liệu.
- Xây dựng luồng tối thiểu từ video đầu vào đến kết quả suy luận và sự kiện cảnh báo.
- Thiết lập quy tắc phối hợp để các thành viên có thể phát triển song song.

### Công việc đã thực hiện

Nhóm bắt đầu bằng việc khởi tạo repository và xây dựng giao diện prototype nhằm thống nhất cách trình bày hệ thống giám sát an toàn. Phần mô tả đề tài, tài liệu kiến trúc và PRD cho MVP được bổ sung để làm rõ người dùng mục tiêu, các loại vi phạm cần phát hiện và giới hạn của sản phẩm.

Backend được thiết lập theo cấu trúc module với FastAPI. Nhóm xây dựng luồng suy luận an toàn thời gian thực qua WebSocket, cho phép frontend gửi khung hình và nhận lại kết quả phát hiện. Frontend ban đầu được tổ chức lại thành các ES module, sau đó tích hợp WebSocket client để hiển thị dữ liệu suy luận.

Nhóm cũng xây dựng bộ điều khiển nhật ký sự kiện, cơ chế lưu sự kiện vào cơ sở dữ liệu và xử lý rollback snapshot nếu quá trình ghi dữ liệu thất bại. Đây là nền tảng cho luồng bằng chứng vi phạm ở các tuần sau.

Song song với phần kỹ thuật, nhóm thống nhất quy tắc quản lý tài liệu, cấu trúc dự án, nhật ký quyết định và tiến độ chung. Điều này giúp hạn chế việc mỗi module lưu một tài liệu trạng thái riêng và giảm xung đột khi tích hợp.

### Khó khăn và cách xử lý

- Sau khi frontend được tách module, nút phát video không hoạt động đúng vì metadata chưa tải xong. Nhóm bổ sung xử lý sự kiện metadata để khôi phục trạng thái nút phát.
- Tài liệu ban đầu nằm ở nhiều vị trí và có nội dung trùng lặp. Nhóm tập trung hóa tài liệu tiến độ và quyết định ở cấp repository.
- Luồng suy luận và lưu sự kiện được phát triển đồng thời nên có nguy cơ snapshot và dữ liệu sự kiện không đồng nhất. Nhóm áp dụng rollback khi lưu thất bại để tránh tạo bằng chứng không có bản ghi tương ứng.

### Kết quả đạt được

Cuối tuần, dự án đã có bộ khung backend và frontend, tài liệu phạm vi MVP, luồng WebSocket inference và khả năng lưu nhật ký sự kiện. Hệ thống chưa hoàn thiện về mô hình và nghiệp vụ, nhưng đã chứng minh được luồng kỹ thuật cơ bản từ dữ liệu đầu vào đến cảnh báo.

### Dấu mốc commit tiêu biểu

- `69b515d`: Khởi tạo repository.
- `5a8d12c`: Bổ sung giao diện prototype.
- `009a106`: Bổ sung PRD cho MVP.
- `94c83f0`, `48cdd68`: Thiết lập và hoàn thiện cấu trúc backend.
- `0750753`: Thêm suy luận an toàn thời gian thực qua WebSocket.
- `5bb80c5`: Thêm lưu sự kiện, SQLite persistence và rollback snapshot.

## 3. Tuần 2 – Chuyển đổi frontend và phát triển nhận diện PPE

**Thời gian:** 03/08/2026 – 09/08/2026

### Mục tiêu của tuần

- Chuyển giao diện thử nghiệm sang nền tảng frontend có thể mở rộng.
- Xây dựng backlog và đặc tả user story cho MVP.
- Tích hợp mô hình phát hiện nhiều lớp, đặc biệt là người và PPE.
- Bổ sung bước bảo vệ danh tính cho ảnh bằng chứng.

### Công việc đã thực hiện

Frontend được chuyển sang React, TypeScript và Vite, đồng thời tổ chức theo feature để thuận tiện cho việc chia nhỏ chức năng. Một giao diện sử dụng mock API được xây dựng và kết nối với các màn hình đang có, tạo nền tảng để thay dữ liệu giả bằng API thật trong các giai đoạn tiếp theo.

Nhóm xây dựng danh sách user story, bổ sung đặc tả chi tiết cho các story đầu tiên và mở rộng backlog cho các chức năng như PPE, tracking, quyền riêng tư, dữ liệu đánh giá và khả năng vận hành. Quy trình phối hợp nhóm và quy trình merge cũng được cập nhật để giảm xung đột giữa các nhánh.

Ở phần Computer Vision, model weights được đưa vào thư mục quản lý bằng Git LFS. Hệ thống được mở rộng từ phát hiện cơ bản sang phát hiện nhiều lớp và hiển thị trạng thái PPE. Logic yêu cầu PPE cùng giao diện cấu hình được điều chỉnh để hỗ trợ việc kiểm tra người có đội mũ và mặc áo phản quang.

Nhóm chuyển công cụ quản lý phụ thuộc Python từ pip sang uv để môi trường cài đặt có tính lặp lại tốt hơn. Các lỗi `IndexError` khi kết quả inference thiếu observation cũng được khắc phục bằng cơ chế fallback.

Một bước quan trọng trong tuần là bảo vệ quyền riêng tư: danh tính được làm mờ trước khi snapshot được lưu. Nhóm đồng thời sửa luồng review để ảnh bằng chứng lấy đúng khung hình tại thời điểm dừng và các bounding box khớp với ảnh hiển thị.

### Khó khăn và cách xử lý

- Việc chuyển từ mã frontend cũ sang React/TypeScript làm thay đổi cấu trúc lớn. Nhóm thực hiện theo feature và giữ luồng chức năng hiện có để giảm rủi ro gián đoạn.
- Kết quả mô hình có thể thiếu một số observation, dẫn tới lỗi truy cập mảng. Nhóm thêm giá trị fallback và tối ưu vòng lặp phát hiện PPE.
- Snapshot có nguy cơ lưu hình ảnh nhận dạng cá nhân. Pipeline được thay đổi để bước làm mờ diễn ra trước bước lưu bằng chứng.
- Bounding box từng không khớp với khung hình vi phạm do video tiếp tục thay đổi. Nhóm chụp đúng stopped frame và dùng cùng hệ tọa độ cho ảnh và box.

### Kết quả đạt được

Cuối tuần, dự án có frontend React/TypeScript có cấu trúc rõ ràng, backlog MVP tương đối đầy đủ, mô hình phát hiện đa lớp và luồng bảo vệ danh tính cơ bản. Hệ thống đã tiến gần hơn đến một sản phẩm có thể demo thay vì chỉ là prototype kỹ thuật.

### Dấu mốc commit tiêu biểu

- `8371d37`: Chuyển frontend sang Vite, React và TypeScript.
- `095e199`, `60a0e77`: Bổ sung đặc tả và backlog user story.
- `2d4f5ea`: Quản lý model weights bằng Git LFS.
- `3eee171`: Chuyển quản lý phụ thuộc sang uv.
- `6972fac`, `b9b2295`: Hoàn thiện xử lý yêu cầu PPE và giao diện.
- `9a4b67f`: Sửa lỗi inference khi thiếu observation.
- `c1d6d88`: Làm mờ danh tính trước khi lưu snapshot.
- `b21521e`: Đồng bộ stopped frame, snapshot và bounding box.

## 4. Tuần 3 – Tracking, phân quyền, đa vùng và hoàn thiện cảnh báo

**Thời gian:** 10/08/2026 – 16/08/2026

### Mục tiêu của tuần

- Theo dõi một người xuyên suốt phiên video và ngăn cảnh báo trùng.
- Hoàn thiện đăng nhập, phân quyền theo vai trò và phạm vi khu vực.
- Hỗ trợ nhiều vùng giám sát trên cùng một nguồn hình ảnh.
- Cải thiện khả năng đánh giá mô hình, metrics và quy trình triển khai.
- Ổn định quy tắc nghiệp vụ cho PPE, vùng cấm và Human-in-the-Loop.

### Công việc đã thực hiện

Nhóm chuẩn bị tài liệu và công cụ cho bộ dữ liệu đánh giá riêng của dự án, bao gồm template, script validation và khả năng benchmark inference. Việc này giúp chuyển đánh giá mô hình từ cảm nhận khi demo sang một quy trình có thể đo lường và tái lập.

US-08 được triển khai với tracking theo phiên và chống trùng cảnh báo. Mỗi người được gắn Track ID trong phạm vi phiên video, còn occurrence được duy trì khi có chuyển giao Track ID phù hợp. Cách làm này hạn chế việc cùng một người tạo nhiều cảnh báo khi bị che khuất hoặc được tracker gán lại ID.

Frontend và backend được tích hợp đăng nhập có lưu session, phân quyền theo các vai trò vận hành và điều hướng giao diện tương ứng. Bên cạnh đó, hệ thống được mở rộng để cấu hình nhiều vùng giám sát và xóa vùng đã lưu.

Nhóm bổ sung hệ thống operational metrics, ghi nhận độ trễ inference và màn hình theo dõi. Quy trình setup được cập nhật để chạy migration, đồng thời các lỗi migration và PostgreSQL occurrence lookup được sửa để hệ thống hoạt động ổn định hơn trên môi trường cơ sở dữ liệu thật.

Model được chuyển sang YOLO11m Safety nhằm thống nhất việc phát hiện người, tracking và PPE trong một pipeline. Docker, cấu hình development/production, PostgreSQL, S3 snapshot, model preload và readiness check được cải thiện để chuẩn bị cho triển khai.

Luồng cảnh báo được bổ sung debounce nhằm chỉ mở review khi vi phạm xuất hiện đủ số khung hình liên tiếp. Nhóm làm rõ trạng thái cảnh báo trong popup, nội dung mô tả vi phạm và khả năng chạy lại video. Quy tắc máy và vùng cũng được thống nhất: trạng thái máy chỉ điều kiện hóa cảnh báo PPE; hành vi xâm nhập vùng cấm vẫn là vi phạm dù máy đang chạy hay dừng.

Cuối tuần, nhóm phát triển luồng cảnh báo theo khu vực và quy trình review cho Area Manager, bổ sung thông báo theo phạm vi, ổn định vòng đời review của Track ID, tích hợp YuNet để làm mờ khuôn mặt và thiết lập CI/CD ban đầu.

### Khó khăn và cách xử lý

- Tracker có thể đổi ID khi một người bị che khuất. Nhóm bảo toàn occurrence khi chuyển giao Track ID trong điều kiện hợp lệ.
- PostgreSQL xử lý dữ liệu JSON khác SQLite, gây lỗi khi so sánh trường chi tiết sự kiện. Truy vấn được điều chỉnh để không yêu cầu PostgreSQL so sánh trực tiếp cột JSON.
- Việc preload model và phụ thuộc inference có thể làm ứng dụng báo sẵn sàng dù model chưa dùng được. Readiness check được mở rộng sang PostgreSQL, S3 và model.
- Nhóm đã thử ONNX Runtime nhưng hoàn tác trong cùng ngày khi hướng triển khai chưa đạt yêu cầu, giữ pipeline ổn định làm baseline.
- Quy tắc vùng cấm và trạng thái máy từng chưa rõ ràng. Nhóm viết contract, bổ sung regression test và tách logic vùng khỏi machine state.
- Nhánh tính năng cảnh báo khu vực gặp xung đột khi đồng bộ. Nhóm revert phần merge lỗi, reapply thay đổi và khôi phục các patch cần thiết.

### Kết quả đạt được

Cuối tuần, hệ thống đã có tracking theo phiên, chống cảnh báo trùng, nhiều vùng giám sát, đăng nhập và phân quyền, metrics vận hành, pipeline YOLO Safety thống nhất, lưu trữ bền vững và quy tắc cảnh báo rõ ràng hơn. Luồng từ AI phát hiện đến con người review đã đủ các bước chính để tiếp tục mở rộng.

### Dấu mốc commit tiêu biểu

- `5cbc6d0`, `d42c36d`: Tracking theo phiên, chống trùng và giữ occurrence khi đổi Track ID.
- `8b2c6e0`: Đăng nhập và phân quyền theo vai trò.
- `cf2315c`, `149675e`, `87fd9c4`: Operational metrics và theo dõi độ trễ inference.
- `7d27ec1`: Giám sát video với nhiều vùng.
- `e6e2f23`: Thống nhất person tracking và PPE bằng YOLO11m Safety.
- `4910c1a`: Lưu snapshot bền vững và observability.
- `b78fce1`, `6edd3d9`: Debounce và hoàn thiện đánh giá quy tắc an toàn.
- `a692156`: Tách xâm nhập vùng cấm khỏi trạng thái máy.
- `da08825`: Cảnh báo theo khu vực và luồng review.
- `8d7be48`: Tích hợp YuNet để làm mờ khuôn mặt.
- `0fe59dc`: Thiết lập CI/CD.

## 5. Tuần 4 – Nhiều camera, audit sự kiện và tách Vision Worker

**Thời gian:** 17/08/2026 – 23/08/2026

### Mục tiêu của tuần

- Mở rộng từ một nguồn video sang mô phỏng và quản lý nhiều camera.
- Tăng khả năng truy vết quyết định của người review.
- Tách tác vụ Computer Vision thành worker có thể chạy độc lập.
- Khảo sát phương án CPU/GPU và tối ưu hiệu năng inference.
- Hoàn thiện cấu hình camera, vùng và PPE cho bản demo.

### Công việc đã thực hiện

Nhóm xây dựng một streaming service riêng, bổ sung chức năng tạo, xóa và chạy camera mô phỏng. Hệ thống quản lý stream được mở rộng với ánh xạ nhiều camera, kiểm soát truy cập, chia sẻ FFmpeg worker và hỗ trợ HLS. Live Monitor được điều chỉnh để hiển thị trạng thái nguồn phát, nhãn camera và các thao tác quản lý cần thiết.

Để bảo vệ luồng HLS, nhóm thêm token, kiểm tra quyền truy cập, health check và xử lý redirect/cookie. Các script build, push image và triển khai được bổ sung cùng regression harness không cần network. Luồng triển khai và hướng dẫn sử dụng cũng được cập nhật để các thành viên có thể tái tạo môi trường.

Ở phần sự kiện, nhóm triển khai audit context bất biến cho quyết định review. Bản ghi sự kiện lưu lại observation, rule, thông tin camera/vùng, kết quả và thời điểm xử lý. Frontend Event Detail được mở rộng để hiển thị nội dung audit, giúp truy vết vì sao một sự kiện được xác nhận là vi phạm hoặc cảnh báo sai.

Phần Vision được tách thành Safety Vision Worker chạy từ xa. Nhóm bổ sung kiểm thử contract, đóng các quality gate và phát triển công cụ so sánh worker CPU với CUDA. Xử lý PPE được cải thiện bằng ràng buộc hình học và temporal smoothing nhằm hạn chế gán nhầm PPE giữa nhiều người.

Trong giai đoạn tối ưu, backend được thay đổi để truyền frame trực tiếp, tránh vòng encode/decode JPEG không cần thiết và cho phép cấu hình kích thước inference. Nhóm cũng điều chỉnh rule engine để không cảnh báo thiếu PPE khi máy dừng, bổ sung cơ chế claim cảnh báo theo phiên và cải thiện giao diện cấu hình camera, vùng cùng review modal.

### Khó khăn và cách xử lý

- Luồng streaming nhiều camera tạo thêm độ phức tạp về ánh xạ, quyền truy cập và tiến trình FFmpeg. Nhóm bổ sung unique mapping, worker dùng chung và test truy cập.
- HLS cần kiểm soát truy cập nhưng trình phát phải xử lý redirect và cookie đúng cách. Nhóm thêm token, gateway checks và regression test cho các trường hợp này.
- Việc tách Vision Worker làm phát sinh ranh giới API mới. Nhóm định nghĩa contract, coi response từ worker là dữ liệu không tin cậy và bổ sung test cho timeout, payload và lỗi provider.
- PPE của một người có thể bị gán nhầm sang người bên cạnh. Nhóm bổ sung kiểm tra vị trí giải phẫu, số lượng theo lớp và temporal smoothing.
- Một người có thể vi phạm liên tục và tạo nhiều popup. Cơ chế claim theo phiên được sử dụng để giới hạn cảnh báo trùng cho cùng đối tượng.

### Kết quả đạt được

Cuối tuần, hệ thống có khả năng vận hành luồng nhiều camera mô phỏng, phát HLS có kiểm soát, audit quyết định sự kiện và một Vision Worker độc lập có thể thử nghiệm trên CPU hoặc GPU. Đây là giai đoạn nhóm khảo sát và tích hợp nhiều phương án vận hành; một số thành phần streaming sau đó được thay thế bởi luồng xử lý media trực tiếp đơn giản hơn.

### Dấu mốc commit tiêu biểu

- `a14268f`, `730884d`: Xây dựng và chạy streaming service.
- `8d07e3b`, `b423fef`: Lưu và hiển thị audit context của quyết định sự kiện.
- `8c301a8`, `c3240c0`: Quản lý ánh xạ nhiều camera và FFmpeg worker.
- `57685c8`, `f01db65`: Tích hợp HLS và bảo vệ truy cập bằng token.
- `4a59b43`: Tách remote Safety Vision Worker.
- `0d9445d`: Công cụ so sánh Vision Worker CUDA.
- `1cc13e2`: Bổ sung PPE geometry và temporal smoothing.
- `5408fcc`: Tránh JPEG round trip và cho phép cấu hình kích thước inference.
- `4927b2c`: Claim cảnh báo để chống trùng trong cùng phiên.
- `f01b25c`: Hoàn thiện cấu hình camera, vùng và review modal.

## 6. Tuần 5 – Ổn định hệ thống, đồng bộ realtime và hoàn thiện trải nghiệm demo

**Thời gian:** 24/08/2026 – 31/08/2026

### Mục tiêu của tuần

- Ổn định luồng media, inference và replay cho bốn camera demo.
- Tối ưu model và chuẩn bị khả năng mở rộng Vision Worker.
- Bảo đảm cảnh báo không bị mất khi tải lại trang hoặc chuyển màn hình.
- Hoàn thiện Camera Detail, Event Detail, Area Manager và quản trị tài khoản.
- Tích hợp Telegram để hỗ trợ thông báo và liên kết tài khoản.

### Công việc đã thực hiện

Đầu tuần, nhóm ổn định camera replay và media inference, bổ sung công cụ dọn dữ liệu local cho demo và cải thiện bố cục cấu hình camera. PPE được chuyển thành cấu hình ở mức camera để vẫn có thể bật hoặc tắt trước khi tạo vùng. Giao diện snapshot sự kiện được cải thiện với phần tóm tắt và overlay vùng.

Nhóm triển khai debounce bảy khung hình cho luồng Human-in-the-Loop để thống nhất điều kiện mở cảnh báo. Model runtime được thử nghiệm và chuyển sang YOLO11n Safety KD nhằm giảm chi phí inference trong khi vẫn duy trì các lớp person, hat và vest.

Một thay đổi kiến trúc quan trọng là contract `safety_vision_v2`. Trạng thái ByteTrack và PPE temporal được đóng gói dưới dạng JSON và do backend lưu trong PostgreSQL. Vision Worker không cần truy cập cơ sở dữ liệu; mỗi request nhận trạng thái trước đó và trả trạng thái mới. Cơ chế revision, frame number, TTL, giới hạn kích thước và compare-and-swap được bổ sung để hạn chế xung đột khi chạy worker phân tán.

Luồng cảnh báo được nâng cấp từ trạng thái tạm trong trình duyệt thành inbox bền vững. Sự kiện mới được lưu với trạng thái chưa xử lý trước khi công bố qua WebSocket. Camera Detail có violation log theo camera; Live Monitor dùng toast và alert stack để thông báo nhưng vẫn sử dụng cùng nguồn dữ liệu sự kiện trong PostgreSQL.

Nhóm mở rộng quyền của System Admin cho các thao tác vận hành và bảo toàn việc gửi Telegram sau khi sự kiện được xác nhận. Phần bảo vệ snapshot được điều chỉnh để frontend chỉ hiển thị annotation do backend tạo; các label và confidence box trùng lặp được loại bỏ, trong khi polygon vùng cấm vẫn được render để người review hiểu bối cảnh.

Cuối tuần, Camera Detail và Event Audit được tinh chỉnh thành hai luồng rõ ràng: cảnh báo đang chờ được review bằng popup HITL, còn sự kiện đã xử lý mở nội dung audit. Giao diện Live Monitor được cố định vừa bốn camera, trang mặc định sau đăng nhập được điều chỉnh theo vai trò và các control cấu hình camera được chuẩn hóa.

Nhóm triển khai liên kết Telegram bằng challenge ngắn hạn, deep link và QR. Luồng này tiếp tục được sửa để nhiều link còn hạn đều có thể sử dụng, trạng thái tài khoản được tải lại ngay sau khi liên kết hoặc ngắt kết nối, và giao diện chỉ hiển thị đúng nhóm thao tác theo trạng thái hiện tại.

Một nhóm thay đổi lớn khác là đồng bộ trạng thái sự kiện giữa Live Monitor, Camera Detail, Event Detail, Audit và Area Manager. Sau khi một sự kiện được review tại bất kỳ màn hình hoặc tab nào, tín hiệu reconciliation được phát trong cùng tab và qua `BroadcastChannel`; các màn hình liên quan tải lại trạng thái authoritative từ backend. Camera Detail đồng thời subscribe WebSocket đúng `camera_id` để nhận sự kiện mới mà không cần polling.

Phạm vi Area Manager được cải thiện từ gán theo khu vực sang ưu tiên danh sách camera được quản lý. Thống kê, danh sách sự kiện và quyền xem chi tiết dùng cùng camera assignment, đồng thời vẫn giữ fallback theo khu vực cho tài khoản cũ.

### Khó khăn và cách xử lý

- State tracking đặt trong worker làm giới hạn khả năng scale ngang. Nhóm chuyển quyền sở hữu persistence về backend và dùng contract trạng thái JSON v2.
- Cảnh báo lưu trong bộ nhớ trình duyệt bị mất khi reload. Nhóm persist sự kiện trước WebSocket và xây dựng lại inbox từ PostgreSQL.
- Nhiều màn hình giữ cache sự kiện riêng khiến trạng thái sau review không đồng bộ. Nhóm dùng tín hiệu reconciliation chung, tải dữ liệu với `cache: no-store` và cập nhật cache cục bộ khi cần.
- WebSocket có thể mất kết nối tạm thời. Camera Detail tự reconnect và đối soát một lần sau khi subscribe lại để lấy các sự kiện đã được persist trong thời gian mất kết nối.
- Nhiều QR hoặc tab Telegram có thể làm link cũ báo không hợp lệ. Backend cho phép mọi challenge còn hạn của cùng tài khoản hoàn tất liên kết và thu hồi các challenge còn lại sau khi thành công.
- Giao diện snapshot từng vẽ lặp box và confidence so với annotation backend. Nhóm quy định snapshot review sử dụng annotation backend, còn frontend chỉ bổ sung overlay vùng cần thiết.
- Quá trình merge model mới tạo ra artifact và mã trùng. Nhóm có commit sửa riêng, chạy lại regression và khôi phục các quality gate liên quan.

### Kết quả đạt được

Đến ngày 31/08/2026, hệ thống đã có luồng demo tương đối hoàn chỉnh với bốn camera logic, media trực tiếp, phát hiện người và PPE, tracking, vùng cấm, chống cảnh báo trùng, HITL review, snapshot bảo vệ danh tính, nhật ký sự kiện, audit, phân quyền, dashboard Area Manager và liên kết Telegram.

Các màn hình vận hành sử dụng cùng nguồn sự kiện bền vững và có khả năng đồng bộ trạng thái gần thời gian thực. Frontend đã đạt trên 100 regression test trong các lần kiểm tra cuối kỳ; lint, type-check và production build đều hoàn tất, dù bộ kiểm tra toàn repository vẫn ghi nhận một số lỗi migration/contract cũ ngoài phạm vi các thay đổi giao diện cuối tuần. Nhóm chỉ triển khai môi trường staging theo lịch sử commit; không xem thay đổi mã nguồn thông thường là quyền tự động triển khai production.

### Dấu mốc commit tiêu biểu

- `3f6e8a9`: Ổn định camera replay và media inference.
- `8df026a`: Áp dụng debounce bảy khung hình cho HITL.
- `d060df8`: Thử nghiệm YOLO11n Safety KD.
- `882b4e3`, `990f5c0`: Portable tracking state v2 và lưu state trong backend.
- `ac6287f`, `28599dc`: Alert stack, toast và violation log theo camera.
- `bcf0e8a`: Mở rộng quyền vận hành cho System Admin.
- `275417d`: Bảo toàn Telegram delivery cho sự kiện đã xác nhận.
- `43abda2`: Tinh chỉnh Camera Detail và Event Audit.
- `e276596`, `a177f35`: Liên kết Telegram và hoàn thiện quản lý tài khoản.
- `fac5161`, `ceeddf1`: Đồng bộ trạng thái sự kiện giữa các màn hình.
- `ee5a3d3`: Hoàn thiện review sự kiện và quản lý tài khoản.

## 7. Tổng kết quá trình làm việc của nhóm

Trong năm tuần phát triển chính, nhóm đã chuyển dự án từ một prototype giao diện thành hệ thống MVP tích hợp đầy đủ frontend, backend, Computer Vision, cơ sở dữ liệu và các thành phần vận hành. Quá trình này không diễn ra theo một đường thẳng: một số phương án như ONNX Runtime hoặc streaming/HLS được thử nghiệm, đánh giá rồi hoàn tác hoặc thay thế khi không còn phù hợp với hướng MVP.

Nhóm làm việc theo hướng phát triển tăng dần. Mỗi chức năng lớn thường đi qua các bước: viết hoặc cập nhật đặc tả, triển khai backend/vision, tích hợp frontend, bổ sung kiểm thử, sửa lỗi tích hợp và cập nhật tài liệu. Lịch sử commit cũng cho thấy các thành viên thường xuyên đồng bộ nhánh và hỗ trợ sửa lỗi ở ranh giới giữa các phần thay vì chỉ làm việc độc lập trong một module.

Các kết quả nổi bật của toàn giai đoạn gồm:

1. Xây dựng luồng phát hiện người, mũ và áo phản quang bằng YOLO Safety.
2. Theo dõi đối tượng theo phiên, quản lý occurrence và chống cảnh báo trùng.
3. Phát hiện xâm nhập nhiều vùng cấm với quy tắc độc lập trạng thái máy.
4. Thiết lập Human-in-the-Loop với debounce, inbox bền vững và audit quyết định.
5. Làm mờ danh tính và lưu snapshot theo pipeline fail-closed trước khi persist.
6. Hỗ trợ bốn camera logic, media library, Run/Replay và đồng bộ WebSocket.
7. Xây dựng đăng nhập, phân quyền System Admin, Safety Manager và Area Manager.
8. Tích hợp Telegram cho thông báo và liên kết tài khoản bằng QR/deep link.
9. Tách Vision Worker, hỗ trợ CPU/GPU và trạng thái tracking phân tán qua PostgreSQL.
10. Thiết lập kiểm thử, Docker, CI/CD, metrics và tài liệu vận hành.

Qua quá trình này, nhóm rút ra rằng chất lượng của hệ thống AI không chỉ phụ thuộc vào độ chính xác của mô hình. Tracking, quy tắc nghiệp vụ, chống trùng, quyền riêng tư, tính bền vững của sự kiện, phân quyền và khả năng truy vết quyết định đều cần được thiết kế đồng bộ để tạo thành một sản phẩm giám sát an toàn có thể sử dụng trong thực tế.
