FROM python:3.11-slim

# Cài đặt ffmpeg hệ thống
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cài đặt thư viện Python
RUN pip install --no-cache-dir \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.34.0" \
    "httpx>=0.28.0" \
    "python-multipart>=0.0.20"

COPY streamer ./streamer

EXPOSE 8001

CMD ["sh", "-c", "uvicorn streamer.app:app --host 0.0.0.0 --port ${PORT:-8001}"]
