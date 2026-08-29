# syntax=docker/dockerfile:1

# ---- Stage 1: Build the React frontend ----
FROM node:22-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Build Python dependencies ----
FROM python:3.11-slim AS python-builder

WORKDIR /app

COPY requirements.docker.txt .
RUN --mount=type=cache,id=s/7eb9053b-6d90-41f8-a72c-7535329155f1-/root/.cache/pip,target=/root/.cache/pip \
    python -m venv /opt/venv && \
    /opt/venv/bin/python -m pip install --no-cache-dir --no-compile \
        --index-url https://download.pytorch.org/whl/cpu \
        torch==2.9.1+cpu torchvision==0.24.1+cpu && \
    /opt/venv/bin/python -m pip install --no-cache-dir --no-compile \
        -r requirements.docker.txt && \
    /opt/venv/bin/python -c "import torch, torchvision; from ultralytics import YOLO; print(torch.__version__, torchvision.__version__, YOLO.__name__)"

# ---- Stage 3: Production ----
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gosu && rm -rf /var/lib/apt/lists/*

# Copy the resolved virtual environment as the runtime Python environment.
COPY --from=python-builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

# Security: run as non-root user
RUN useradd -m appuser

# Copy application code
COPY backend ./backend
COPY vision ./vision
COPY scripts ./scripts
COPY --chmod=755 scripts/container_entrypoint.sh /usr/local/bin/p047-entrypoint
COPY alembic.ini ./
COPY models/yolo11n_safety_kd_best.pt ./models/
COPY models/face_detection_yunet_2023mar.onnx ./models/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create data directory with correct ownership
RUN mkdir -p /app/data/media-assets && chown -R appuser:appuser /app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import json, urllib.request; health=json.load(urllib.request.urlopen('http://localhost:8000/health')); assert health['ready']" || exit 1

ENTRYPOINT ["p047-entrypoint"]
CMD ["python", "-m", "scripts.production_start"]
