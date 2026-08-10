# US-13 evaluation dataset workspace

Các template trong thư mục này được commit để đội dự án chuẩn bị dữ liệu trước khi
quay. Raw media, consent record và annotation thật không được commit vào Git; lưu ở
approved storage và chỉ tham chiếu bằng URI/checksum trong manifest.

## Dùng ngay

1. Sao chép `shooting-sheet-template.csv`, điền mỗi video dự định quay và lưu bản làm
   việc ngoài Git.
2. Sau khi quay, sao chép `ground-truth-template.json` cho từng video và điền đáp án
   do con người quan sát.
3. Sao chép `manifest-template.json`, khai báo video, URI lưu trữ, checksum và split.
4. Kiểm tra manifest bằng:

   ```bash
   python scripts/validate_us13_dataset.py path/to/manifest.json
   ```

Script kiểm tra cấu trúc manifest, ID trùng, split không hợp lệ và checksum SHA-256
không đúng định dạng. Nếu `annotation_path` là file local, script cũng kiểm tra file
tồn tại và checksum annotation có khớp không.

Không đưa video thuộc cùng một video/scenario/take gần tương đương vào cả
`calibration` và `final`.
