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
RUN pip install --no-cache-dir --user -r requirements.txt

# ---- Stage 3: Production ----
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from the Python dependency stage
COPY --from=python-builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

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

CMD ["python", "scripts/production_start.py"]
