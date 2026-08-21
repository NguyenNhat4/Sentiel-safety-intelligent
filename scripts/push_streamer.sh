#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  printf 'Usage: %s [IMAGE_NAME] [TAG]\n' "$0"
  printf 'Default image: %s:dev\n' "${DOCKERHUB_IMAGE:-nguyennhat/streamer}"
  printf 'Example: %s mydockeruser/p047-streamer v1.0.0\n' "$0"
  exit 0
fi

if [[ "$#" -gt 2 ]]; then
  printf 'Error: expected at most an image name and a tag.\n' >&2
  printf 'Usage: %s [IMAGE_NAME] [TAG]\n' "$0" >&2
  exit 2
fi

IMAGE_NAME="${1:-${DOCKERHUB_IMAGE:-nguyennhat4/streamer}}"
IMAGE_TAG="${2:-dev}"
IMAGE_REF="${IMAGE_NAME}:${IMAGE_TAG}"

if ! command -v docker >/dev/null 2>&1; then
  printf 'Error: docker is not installed or not available in PATH.\n' >&2
  exit 1
fi

printf 'Building streamer image: %s\n' "$IMAGE_REF"
docker build \
  --file "$ROOT_DIR/streamer/Dockerfile" \
  --tag "$IMAGE_REF" \
  "$ROOT_DIR"

printf 'Pushing streamer image: %s\n' "$IMAGE_REF"
docker push "$IMAGE_REF"

printf 'Published streamer image successfully: %s\n' "$IMAGE_REF"
