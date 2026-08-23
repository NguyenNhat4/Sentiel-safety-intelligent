# Chạy P-047 Local Bằng Docker + PostgreSQL

Tài liệu này chạy toàn bộ P-047 trên máy local bằng Docker: FastAPI, frontend
build, model CPU-only và PostgreSQL. Nó dùng database Docker named volume riêng,
không dùng SQLite trong `data/safety_events.db`.

## Điều kiện

- Docker Engine và Docker Compose v2 hoạt động (`docker compose version`).
- Git LFS đã tải hai model trong `models/`; startup sẽ kiểm tra checksum và fail
  rõ ràng nếu model là LFS pointer hoặc sai file.
- Port `8000` local chưa bị service khác chiếm.

## Khởi động lần đầu

Từ repository root, chạy:

```bash
docker compose up -d --build
docker compose ps
docker compose logs --tail=100 backend db
```

Không cần tạo `.env.production` thủ công. `docker-compose.yml` là cấu hình local
độc lập và đặt database thành:

```text
postgresql+psycopg2://p047:p047-local-only@db:5432/p047_local
```

Compose đợi PostgreSQL health check trước khi khởi động backend. Backend chạy
`alembic upgrade head` một lần khi start, vì vậy database local mới sẽ có đúng
schema hiện tại.

## Kiểm tra service

```bash
curl --fail http://localhost:8000/health
docker compose exec db \
  psql -U p047 -d p047_local -c 'SELECT version_num FROM alembic_version;'
```

Kỳ vọng `/health` trả JSON với `ready: true` và PostgreSQL là backend database.
Sau đó mở:

```text
http://localhost:8000/
http://localhost:8000/docs
```

## Dừng và chạy lại

```bash
docker compose down
docker compose up -d
```

Lệnh `down` giữ named volume `p047_local_postgres_data`, nên database và event
local vẫn còn. Dùng `logs -f backend` khi cần xem startup hoặc migration:

```bash
docker compose logs -f backend
```

## Reset sạch database local

Lệnh này chỉ xoá named volume PostgreSQL của compose local này. Nó không xoá
source code, model hay R2/Render data. Toàn bộ event local sẽ mất.

```bash
docker compose down -v
docker compose up -d --build
```

## Chẩn đoán lỗi

| Lỗi | Kiểm tra và xử lý |
|---|---|
| `Can't locate revision` | Reset named volume local theo phần trên; database cũ đang trỏ tới migration không có trong image. |
| Backend không start | Xem `docker compose logs backend`; model checksum, Alembic và database URL xuất hiện trước Uvicorn. |
| PostgreSQL không healthy | Xem `docker compose logs db`; kiểm tra port nội bộ 5432 và named volume còn quyền ghi. |
| Port 8000 đã dùng | Dừng service đang dùng port hoặc đổi mapping `8000:8000` trong Compose base. |
| Build rất lâu | Chờ Python CPU dependencies hoàn tất; frontend build pass chưa chứng minh backend đã sẵn sàng. |

## Giới hạn

Đây là local developer/test topology, không phải production. Credentials
`p047-local-only` chỉ được hard-code vì database chỉ mở trong Docker network và
không được dùng trên Render/production. R2 không được kích hoạt ở đây; snapshot
được lưu trong `data/snapshots` local.

## Nguồn chính thức

- Docker Compose production/configuration model: <https://docs.docker.com/compose/>
- PostgreSQL Docker image: <https://hub.docker.com/_/postgres>
