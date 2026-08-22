#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
IMAGE_NAME="${VISION_COMPARE_IMAGE:-p047-vision:gpu-dev}"
CPU_PORT="${VISION_COMPARE_CPU_PORT:-8101}"
GPU_PORT="${VISION_COMPARE_GPU_PORT:-8102}"
UI_PORT="${VISION_COMPARE_UI_PORT:-5173}"
WORKER_API_KEY="${VISION_WORKER_API_KEY:-}"
CPU_CONTAINER_ID=""
GPU_CONTAINER_ID=""

cleanup() {
  trap - EXIT INT TERM
  if [[ -n "$CPU_CONTAINER_ID" ]]; then
    docker rm --force "$CPU_CONTAINER_ID" >/dev/null 2>&1 || true
  fi
  if [[ -n "$GPU_CONTAINER_ID" ]]; then
    docker rm --force "$GPU_CONTAINER_ID" >/dev/null 2>&1 || true
  fi
}

fail_with_logs() {
  local container_id="$1"
  local label="$2"
  echo "$label worker không khởi động được. Log cuối:" >&2
  docker logs --tail 40 "$container_id" >&2 || true
  return 1
}

wait_for_worker() {
  local container_id="$1"
  local label="$2"
  local attempt
  for attempt in $(seq 1 90); do
    if docker exec "$container_id" python -c \
      "import json, urllib.request; assert json.load(urllib.request.urlopen('http://127.0.0.1:8000/ping', timeout=2))['status'] == 'healthy'" \
      >/dev/null 2>&1; then
      echo "✓ $label worker sẵn sàng"
      return 0
    fi
    if ! docker inspect --format '{{.State.Running}}' "$container_id" 2>/dev/null | grep -qx true; then
      fail_with_logs "$container_id" "$label"
      return 1
    fi
    sleep 1
  done
  fail_with_logs "$container_id" "$label"
}

trap cleanup EXIT INT TERM

command -v docker >/dev/null 2>&1 || { echo "Thiếu Docker." >&2; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "Thiếu Node.js/npm. Hãy chạy make setup trước." >&2; exit 1; }
docker info >/dev/null 2>&1 || { echo "Docker daemon chưa chạy." >&2; exit 1; }
[[ -d "$REPO_DIR/frontend/node_modules" ]] || { echo "Thiếu frontend/node_modules. Hãy chạy make setup trước." >&2; exit 1; }

CPU_CONTAINER_ID="$(docker create --rm \
  --publish "127.0.0.1:${CPU_PORT}:8000" \
  --env VISION_DEVICE=cpu \
  --env VISION_MODEL_VERSION=yolo11m_safety-cpu-compare \
  --env "VISION_WORKER_API_KEY=${WORKER_API_KEY}" \
  "$IMAGE_NAME")"

GPU_CONTAINER_ID="$(docker create --rm \
  --gpus all \
  --publish "127.0.0.1:${GPU_PORT}:8000" \
  --env VISION_DEVICE=cuda:0 \
  --env VISION_MODEL_VERSION=yolo11m_safety-gpu-compare \
  --env "VISION_WORKER_API_KEY=${WORKER_API_KEY}" \
  "$IMAGE_NAME")"

docker start "$CPU_CONTAINER_ID" "$GPU_CONTAINER_ID" >/dev/null
wait_for_worker "$CPU_CONTAINER_ID" "CPU"
wait_for_worker "$GPU_CONTAINER_ID" "CUDA GPU"

echo
echo "Vision Compare Lab: http://127.0.0.1:${UI_PORT}/vision-worker-compare.html"
echo "Nhấn Ctrl+C để dừng UI và hai worker."
if [[ -n "$WORKER_API_KEY" ]]; then
  echo "VISION_WORKER_API_KEY đang bật; nhập cùng key vào hai ô trên giao diện."
fi
echo

cd "$REPO_DIR"
VISION_WORKER_CPU_DEV_URL="http://127.0.0.1:${CPU_PORT}" \
VISION_WORKER_GPU_DEV_URL="http://127.0.0.1:${GPU_PORT}" \
npm --prefix frontend run dev -- --host 127.0.0.1 --port "$UI_PORT"
