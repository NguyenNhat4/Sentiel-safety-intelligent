# Railway không tự seed dữ liệu khi deploy

## Phạm vi

Tài liệu này giải thích vì sao một deployment mới của `p047-app` trên Railway có
schema PostgreSQL nhưng không đăng nhập được bằng các tài khoản demo hiển thị trên
màn hình. Hướng dẫn áp dụng cho `staging2`; không dùng tài khoản demo hoặc mật khẩu
demo cho production thật.

## Kết luận ngắn

Deploy image, migrate schema và seed dữ liệu là ba thao tác khác nhau:

| Thao tác | Luồng hiện tại thực hiện | Kết quả |
|---|---|---|
| Deploy | Railway kéo Docker image và khởi động container | Có code và model mới |
| Migrate | `scripts/production_start.py` chạy `alembic upgrade head` | Có bảng, cột, index và revision hiện hành |
| Seed | Chỉ chạy trong FastAPI lifespan khi `APP_ENV != production` | Không chạy trên Railway đang đặt `APP_ENV=production` |

Tên Railway environment là `staging2` không tự làm `APP_ENV` thành development.
Nếu service variable vẫn là `APP_ENV=production`, backend cố ý không gọi
`AuthService.seed_demo_users()`.

## Bằng chứng từ runtime hiện tại

Luồng khởi động container nằm trong `scripts/production_start.py`:

1. Đọc và kiểm tra runtime configuration.
2. Kiểm tra model và các file bắt buộc.
3. Chạy `alembic upgrade head` và xác nhận database ở migration head.
4. Khởi động Uvicorn.

Alembic quản lý cấu trúc database; các migration hiện tại không chèn ba tài khoản
demo.

Trong `backend/app/main.py`, seed chỉ được gọi theo điều kiện:

```python
if settings.app_env != "production":
    AuthService(db).seed_demo_users()
```

Hàm `seed_demo_users()` trong `backend/app/services/auth_service.py` tạo ba tài
khoản còn thiếu và dùng mật khẩu demo đã biết. Vì vậy việc chặn seed trong
production là chủ ý an toàn, không phải lỗi Docker, Railway, model hay Alembic.

## Vì sao giao diện vẫn hiện tài khoản demo

`frontend/src/features/auth/LoginPage.tsx` hiện đang đóng gói cứng ba thẻ tài khoản
demo trong frontend production. Nút **Dùng tài khoản** chỉ điền email và mật khẩu
vào form; nó không tạo user trong PostgreSQL và không chứng minh user đó tồn tại.

Do đó có thể đồng thời xảy ra hai việc:

- Trang đăng nhập hiển thị `admin@sentinel.local`.
- PostgreSQL của `staging2` không có bản ghi tương ứng nên API trả
  `Invalid email or password`.

Đây là một khoảng lệch UI/runtime cần xử lý riêng: production nên ẩn các thẻ demo
bằng build flag, còn môi trường demo phải seed có chủ đích.

## Vì sao đổi `DATABASE_URL` làm dữ liệu cũ biến mất

Docker image không chứa các row PostgreSQL. Railway volume gắn vào `p047-app` cũng
không phải volume của managed PostgreSQL. Khi `DATABASE_URL` được đổi sang một
database hoặc PostgreSQL service mới:

- Alembic tạo/nâng cấp schema trong database mới.
- User, camera configuration, media metadata và event ở database cũ không tự được
  sao chép.
- Redeploy app không phục hồi hoặc seed các row đó.

Trước mọi thao tác seed, phải xác nhận `p047-app.DATABASE_URL` đang reference đúng
PostgreSQL service trong đúng environment `staging2`. Không in hoặc gửi toàn bộ URL
vì URL chứa thông tin xác thực.

## Seed có chủ đích cho `staging2`

Chỉ thực hiện phần này khi `staging2` là môi trường demo nội bộ và deployment
`p047-app` đang chạy thành công. Railway CLI phải đăng nhập và có SSH key hợp lệ.

Chạy đúng service và environment:

```bash
railway ssh \
  --service p047-app \
  --environment staging2 \
  -- \
  python -c 'from backend.app.core.database import SessionLocal; from backend.app.services.auth_service import AuthService; db = SessionLocal(); AuthService(db).seed_demo_users(); db.close(); print("Seeded staging2 demo users")'
```

Hàm seed hiện tại có tính lặp lại an toàn đối với ba email demo: user đã tồn tại sẽ
không được tạo lần nữa. Nó không reset mật khẩu của user đã tồn tại.

Sau khi chạy, xác minh danh sách email/role mà không in password hash hoặc
`DATABASE_URL`:

```bash
railway ssh \
  --service p047-app \
  --environment staging2 \
  -- \
  python -c 'from backend.app.core.database import SessionLocal; from backend.app.models.user import User; db = SessionLocal(); print([(u.email, u.role, u.is_active) for u in db.query(User).order_by(User.email).all()]); db.close()'
```

Cuối cùng đăng nhập lại trên `staging2`. Seed là thay đổi dữ liệu PostgreSQL nên nó
vẫn tồn tại sau khi restart hoặc redeploy cùng database.

## Không nên làm

- Không đổi `APP_ENV=development` trên Railway chỉ để ép auto-seed. Cách này thay
  đổi nhiều guard runtime khác ngoài seed và có thể làm staging không còn mô phỏng
  đúng production.
- Không thêm mật khẩu demo vào migration Alembic. Migration schema phải giữ tính
  xác định và không phát tán credential dùng chung.
- Không chạy lệnh seed nếu CLI chưa chỉ rõ `--environment staging2` và
  `--service p047-app`.
- Không giả định thẻ tài khoản trên frontend đồng nghĩa user đã tồn tại.
- Không seed ba tài khoản/mật khẩu demo vào production thật.

## Khoảng trống cần xử lý trước production thật

Codebase hiện chưa có lệnh bootstrap production riêng để tạo system admin đầu tiên
bằng secret một lần. Trước production thật cần triển khai một luồng bootstrap có
guard, nhận credential từ secret manager, từ chối chạy khi admin đã tồn tại và để
lại audit evidence. Đồng thời frontend production cần ẩn hoàn toàn danh sách tài
khoản demo.

