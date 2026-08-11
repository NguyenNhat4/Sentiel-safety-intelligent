# US-13 Task 2 — Chuẩn bị và khóa custom evaluation dataset

## 1. Mục tiêu

Tạo bộ dữ liệu nghiệm thu do dự án sở hữu để đo person detection, PPE, zone
occurrence, false alarm và latency. Đầu ra phải có thể kiểm tra nguồn gốc, chạy lại
benchmark và chứng minh final evaluation set chưa được dùng để tune.

Chỉ bắt đầu quay sau khi Product Owner chốt metric protocol, scenario matrix, sample
size, định nghĩa occurrence/false alarm và ngưỡng nghiệm thu.

## 2. Kế hoạch scenario

Mỗi dòng trong bảng quay là một scenario độc lập. Bộ dữ liệu tối thiểu phải bao phủ:

| ID | PPE | Zone | Máy | Người | Mục đích |
|---|---|---|---|---:|---|
| S01 | Đủ | Ngoài | OFF hoặc ON | 1 | Normal/negative |
| S02 | Thiếu mũ | Ngoài | ON | 1 | Helmet violation |
| S03 | Thiếu kính | Ngoài | ON | 1 | Glasses violation |
| S04 | Thiếu găng | Ngoài | ON | 1 | Gloves violation |
| S05 | Thiếu tổ hợp | Ngoài | ON | 1 | Nhiều PPE missing |
| S06 | Đủ | Trong | ON | 1 | Zone violation |
| S07 | Đủ | Trong | OFF | 1 | Zone negative khi máy dừng |
| S08 | Đủ | Vào–ra–vào | ON | 1 | Hai occurrence độc lập |
| S09 | Đủ hoặc thiếu | Hỗn hợp | ON | 1 | Che khuất/mất track ngắn |
| S10 | Khác nhau theo người | Hỗn hợp | ON | 2+ | Association nhiều người |

Mỗi scenario nên có nhiều video độc lập, thay đổi người tham gia, góc máy, khoảng
cách, ánh sáng và hướng di chuyển. Không đưa các đoạn cắt từ cùng một video hoặc các
take gần như giống nhau vào hai split khác nhau.

## 3. Consent, privacy và định danh

Trước khi quay:

- Có sự đồng ý của từng người tham gia và mã hồ sơ consent.
- Quy định rõ nơi lưu raw media, người được truy cập và thời hạn lưu.
- Dùng ID giả danh như `actor_001`; không ghi tên thật vào video hoặc annotation.
- Không commit raw video vào Git khi chưa có cơ chế storage và quyền truy cập được duyệt.
- Chỉ version hóa annotation, provenance, manifest và checksum bất biến của media.

Đặt ID trước khi quay:

```text
scenario_id: S08
video_id: VID_S08_003
actor_ids: [actor_002]
recording_take: 3
media_name: VID_S08_003.mp4
```

Không ghi nhãn vi phạm hoặc tên split trong tên media để tránh ảnh hưởng người gán
nhãn. Split được quản lý trong manifest.

## 4. Ground truth bắt buộc

### 4.1 Video và scenario

```json
{
  "video_id": "VID_S08_003",
  "scenario_id": "S08",
  "fps": 30,
  "width": 1920,
  "height": 1080,
  "duration_ms": 18000
}
```

### 4.2 Zone và trạng thái máy

Tọa độ polygon nên chuẩn hóa về `[0, 1]` để không phụ thuộc độ phân giải:

```json
{
  "zone_polygon": [
    [0.25, 0.65],
    [0.72, 0.65],
    [0.82, 0.95],
    [0.15, 0.95]
  ],
  "machine_state_timeline": [
    {"start_ms": 0, "end_ms": 5000, "state": "stopped"},
    {"start_ms": 5000, "end_ms": 18000, "state": "running"}
  ]
}
```

### 4.3 Person track và PPE theo người

```json
{
  "track_id": "GT_P01",
  "actor_id": "actor_002",
  "ppe_segments": [
    {
      "start_ms": 0,
      "end_ms": 18000,
      "helmet": "present",
      "glasses": "missing",
      "gloves": "present"
    }
  ],
  "boxes": [
    {
      "frame": 120,
      "bbox_xyxy": [430, 210, 720, 1010],
      "visibility": 0.92
    }
  ]
}
```

Chỉ gán `missing` khi hình ảnh đủ điều kiện kết luận người đó không có PPE. Nếu vật
thể bị che, ngoài khung hình, quá nhỏ hoặc góc quay không đủ rõ thì gán `unknown`.

### 4.4 Violation occurrence

Occurrence là đơn vị đánh giá nghiệp vụ, không phải từng frame:

```json
{
  "occurrence_id": "OCC_S08_003_01",
  "video_id": "VID_S08_003",
  "track_id": "GT_P01",
  "type": "zone_intrusion",
  "start_ms": 6200,
  "end_ms": 9100,
  "expected_review_outcome": "violate"
}
```

Người vào zone, ra hoàn toàn rồi vào lại phải tạo hai occurrence. Mất track ngắn
trong cùng một vi phạm không tự động tạo occurrence mới; khoảng nối track phải tuân
theo metric protocol đã được duyệt.

## 5. Kiểm tra chéo annotation

Không để một người vừa annotate vừa tự duyệt toàn bộ video của mình:

1. Annotator A gán nhãn.
2. Annotator B kiểm tra độc lập và không xem prediction của model.
3. Liệt kê tất cả bất đồng giữa hai annotation.
4. Reviewer C phân xử các bất đồng ảnh hưởng đến metric.
5. Sau adjudication, annotation chuyển sang trạng thái `approved`.

Checklist kiểm tra:

- Bbox và track không nhảy sang người khác.
- PPE được gắn đúng person/track.
- `missing` không được dùng khi bằng chứng chỉ đủ cho `unknown`.
- Zone polygon và hệ tọa độ chính xác.
- Machine-state timeline khớp diễn biến video.
- Occurrence start/end và expected outcome tuân theo rule đã chốt.
- Tình huống vào–ra–vào tạo đúng số occurrence.

Lưu audit metadata trong annotation:

```json
{
  "annotation_status": "approved",
  "annotated_by": "annotator_a",
  "reviewed_by": "annotator_b",
  "adjudicated_by": "reviewer_c",
  "annotation_version": "1.0.0"
}
```

## 6. Chia calibration và final evaluation

Chia theo nhóm video/scenario, tuyệt đối không chia theo frame:

- Tất cả frame và clip dẫn xuất từ một video phải nằm cùng một split.
- Các take gần giống nhau của cùng actor/scenario nên được gom nhóm trước khi chia.
- Hai split đều phải có các scenario quan trọng và đủ positive/negative để tính metric.
- Final không được dùng để chọn model, threshold, confidence guard, association rule
  hoặc dedup window.
- Tỷ lệ tham khảo là 60–70% calibration và 30–40% final; tỷ lệ chính thức phụ thuộc
  sample size và coverage đã được Product Owner duyệt.

Dùng seed cố định để sinh split, sau đó kiểm tra coverage thủ công:

```json
{
  "split_policy": "grouped_by_video_and_scenario",
  "split_seed": 13047,
  "calibration_video_ids": ["VID_S01_001", "VID_S02_002"],
  "final_video_ids": ["VID_S01_004", "VID_S02_005"]
}
```

## 7. Manifest và checksum

Manifest dataset tối thiểu:

```json
{
  "dataset_id": "p047-custom-eval",
  "dataset_version": "1.0.0",
  "created_at": "2026-08-10T00:00:00Z",
  "annotation_schema_version": "1.0.0",
  "split_policy": "grouped_by_video_and_scenario",
  "split_seed": 13047,
  "videos": [
    {
      "video_id": "VID_S08_003",
      "scenario_id": "S08",
      "split": "final",
      "media_uri": "approved-storage://p047/VID_S08_003.mp4",
      "media_sha256": "<sha256>",
      "annotation_path": "annotations/VID_S08_003.json",
      "annotation_sha256": "<sha256>",
      "consent_record_id": "CONSENT_002"
    }
  ]
}
```

Tính SHA-256 cho từng raw video, annotation đã approved, file split và manifest cuối.
Checksum của manifest phải nằm ngoài manifest để tránh vòng lặp:

```text
manifest.json
manifest.json.sha256
```

## 8. Khóa final split

Final split chỉ được xem là khóa khi:

- Annotation đã được cross-check, adjudicate và approved.
- Coverage của từng scenario đã được xác nhận.
- Manifest và toàn bộ checksum đã được xác minh.
- Model/checkpoint, threshold và rule chưa được chạy hoặc tune trên final.
- Dataset có version/tag bất biến, ví dụ `p047-custom-eval-v1.0.0`.
- Quyền ghi final media/annotation bị giới hạn.
- Mọi sửa đổi sau khi khóa tạo dataset version mới; không sửa âm thầm version cũ.

Biên bản khóa cần ghi:

```text
Dataset: p047-custom-eval
Version: 1.0.0
Locked at: <UTC timestamp>
Manifest SHA-256: <sha256>
Final video count: <count>
Final occurrence count by type: <counts>
Approved by: <approver>
Permitted use: final acceptance benchmark only
```

## 9. Definition of Done

Task 2 hoàn thành khi:

- Custom videos bao phủ scenario matrix và sample size đã chốt.
- Consent, nơi lưu raw media và quyền truy cập được ghi nhận rõ ràng.
- Ground truth đủ video/scenario, person bbox/track, PPE, zone, machine timeline,
  occurrence và expected review outcome.
- 100% annotation đã kiểm tra chéo; bất đồng đã được adjudicate.
- Calibration/final không rò rỉ theo video, scenario hoặc take gần tương đương.
- Manifest được version hóa và checksum xác minh thành công.
- Final split đã khóa và chưa được dùng để tune.
- Có bảng tổng hợp số video, thời lượng, person track và occurrence theo scenario/split.

Ba lỗi nghiêm trọng cần tránh là gán `missing` khi chỉ có bằng chứng `unknown`, chia
frame hoặc clip của cùng video sang hai split, và xem prediction của model khi sửa
annotation final. Các lỗi này làm kết quả benchmark không còn đáng tin cậy.
