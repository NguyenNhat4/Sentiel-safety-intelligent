#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  printf 'Usage: %s [IMAGE_TAG]\n' "$0"
  printf 'Default image tag: nguyennaht4/streamer:dev\n'
  exit 0
fi

IMAGE_TAG="${1:-nguyennaht4/streamer:dev}"

if ! command -v docker >/dev/null 2>&1; then
  printf 'Error: docker is not installed or not available in PATH.\n' >&2
  exit 1
fi

mkdir -p "$ROOT_DIR/data/streamer"
printf 'Running streamer image: %s\n' "$IMAGE_TAG"
printf 'Open http://localhost:8001/\n'

exec docker run --rm \
  --name p047-streamer \
  --publish 8001:8001 \
  --volume "$ROOT_DIR/data/streamer:/app/data/streamer" \
  "$IMAGE_TAG"
