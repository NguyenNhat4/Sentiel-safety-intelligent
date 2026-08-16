---
title: "Working with uv"
description: "Hướng dẫn cài đặt, quản lý môi trường và dependencies với uv"
weight: 2
---

# Hướng dẫn Làm Việc với `uv` (uv Setup & Development Guide)

Dự án P-047 sử dụng **`uv`** làm công cụ quản lý môi trường ảo (virtual environment) và dependency manager chính cho Python. `uv` là công cụ tốc độ cực cao được viết bằng Rust, giúp tăng tốc độ cài đặt và quản lý môi trường gấp 10-100 lần so với `pip` và `venv` truyền thống.

---

## 🚀 Quick Start cho Cán Bộ / Thành Viên Mới

Để khởi tạo toàn bộ môi trường (Python virtualenv + dependencies + frontend npm dependencies + `.env.development`), bạn chỉ cần đứng ở thư mục gốc của repository và chạy 1 lệnh duy nhất:

```bash
make setup
```

Lệnh này sẽ tự động:
1. Chạy `uv sync` để tạo môi trường `.venv` và cài đặt đúng các phiên bản gói từ `pyproject.toml` và `uv.lock`.
2. Chạy `npm --prefix frontend ci` để cài đặt dependencies cho phân hệ React Frontend.
3. Tạo file cấu hình môi trường `.env.development` từ `.env.development.example` (nếu chưa có). Docker Compose dùng `.env.production` riêng.

---

## 🛠️ Thao Tác Chi Tiết Với `uv`

### 1. Khởi tạo môi trường thủ công (Manual Setup)

Nếu không dùng `make setup`, bạn có thể thực hiện từng bước với `uv`:

```bash
# Tạo virtual environment (runtime được hỗ trợ duy nhất là Python 3.11)
uv venv .venv --python 3.11

# Đồng bộ dependencies từ pyproject.toml / uv.lock
uv sync
```

### 2. Kích hoạt Virtual Environment

Tương tự venv thông thường, bạn có thể kích hoạt môi trường ảo bằng:

```bash
# Trên Linux/macOS:
source .venv/bin/activate

# Trên Windows (PowerShell):
.venv\Scripts\activate
```

Hoặc không cần kích hoạt, bạn có thể thực thi lệnh trực tiếp thông qua `uv run`:

```bash
uv run uvicorn backend.app.main:app --reload
uv run pytest
```

---

## 📦 Quản Lý Dependencies với `uv`

### Thêm một gói thư viện mới (Add Dependency)

Để thêm thư viện vào dự án (tự động cập nhật `pyproject.toml` và `uv.lock`):

```bash
# Cài đặt gói chính (Production dependency)
uv add <package_name>

# Cài đặt gói cho Dev / Testing
uv add --dev <package_name>
```

*Ví dụ:*
```bash
uv add httpx
```

### Xóa gói thư viện (Remove Dependency)

```bash
uv remove <package_name>
```

### Cập nhật Dependencies (Upgrade Packages)

```bash
# Cập nhật tất cả các gói lên phiên bản mới nhất tương thích
uv lock --upgrade
uv sync
```

---

## 🔍 Các Lệnh Makefile Thường Dùng Với `uv`

Tất cả các lệnh Make trong dự án đều được tích hợp sẵn với Virtual Environment của `uv`:

| Lệnh Make | Chức năng |
|---|---|
| `make setup` | Cài đặt toàn bộ môi trường Python (`uv sync`) & Frontend (`npm ci`) |
| `make py-setup` | Chỉ đồng bộ môi trường Python với `uv sync` |
| `make run` | Khởi chạy server FastAPI & ứng dụng Sentinel |
| `make check` | Chạy toàn bộ test suite và linting (Python & React) |
| `make lint` | Kiểm tra cú pháp Python với Ruff (`.venv/bin/ruff check`) |
| `make format` | Kiểm tra định dạng Python với Ruff (`.venv/bin/ruff format`) |
| `make test` | Chạy bộ test Pytest cho cả Agent và Backend |

---

## 💡 Troubleshooting & Best Practices

1. **Dùng Python 3.11**: Đây là runtime duy nhất được pin trong `.python-version`, lockfile, Docker và CI.
2. **Không sửa trực tiếp `requirements.txt`**: Dự án quản lý dependencies chính qua `pyproject.toml` và `uv.lock`. Nếu cần cập nhật `requirements.txt` cho môi trường deploy cũ, chạy:
   ```bash
   uv export --format requirements-txt -o requirements.txt
   ```
3. **Reset lại môi trường sạch (Clean Reinstall)**:
   ```bash
   rm -rf .venv
   make setup
   ```
