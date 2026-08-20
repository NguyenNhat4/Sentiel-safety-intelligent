# syntax=docker/dockerfile:1

# ---- Stage 1: Build the React frontend ----
FROM node:22-slim AS frontend-builder

WORKDIR /app/frontend

ARG VITE_STREAMER_URL=
ENV VITE_STREAMER_URL=${VITE_STREAMER_URL}

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Build Python dependencies ----
FROM python:3.11-slim AS python-builder

WORKDIR /app

COPY requirements.docker.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
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

# Copy the resolved virtual environment as the runtime Python environment.
COPY --from=python-builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

# Security: run as non-root user
RUN useradd -m appuser

# Copy application code
COPY backend ./backend
COPY vision ./vision
COPY scripts ./scripts
COPY alembic.ini ./
COPY models/yolo11m_safety.pt ./models/
COPY models/face_detection_yunet_2023mar.onnx ./models/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create data directory with correct ownership
RUN mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import json, urllib.request; health=json.load(urllib.request.urlopen('http://localhost:8000/health')); assert health['ready']" || exit 1

CMD ["python", "-m", "scripts.production_start"]
