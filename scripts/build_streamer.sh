#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  printf 'Usage: %s [IMAGE_TAG]\n' "$0"
  printf 'Default image tag: nguyennhat4/streamer:dev\n'
  exit 0
fi

IMAGE_TAG="${1:-nguyennhat4/streamer:dev}"

if ! command -v docker >/dev/null 2>&1; then
  printf 'Error: docker is not installed or not available in PATH.\n' >&2
  exit 1
fi

printf 'Building streamer image: %s\n' "$IMAGE_TAG"
docker build \
  --file "$ROOT_DIR/streamer/Dockerfile" \
  --tag "$IMAGE_TAG" \
  "$ROOT_DIR"

printf 'Built image successfully: %s\n' "$IMAGE_TAG"
