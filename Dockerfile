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

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --prefix=/install torch torchvision \
        --index-url https://download.pytorch.org/whl/cpu && \
    python -m pip install --prefix=/install -r requirements.txt

# ---- Stage 3: Production ----
FROM python:3.11-slim

WORKDIR /app

# Copy dependencies into the system site-packages so the non-root runtime user
# can import them.
COPY --from=python-builder /install /usr/local

# Security: run as non-root user
RUN useradd -m appuser

# Copy application code
COPY backend ./backend
COPY vision ./vision
COPY scripts ./scripts
COPY alembic.ini ./
COPY models/yolo11n.pt models/ppe_yolov8n.pt ./models/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create data directory with correct ownership
RUN mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import json, urllib.request; health=json.load(urllib.request.urlopen('http://localhost:8000/health')); assert health['ready']" || exit 1

CMD ["python", "-m", "scripts.production_start"]
