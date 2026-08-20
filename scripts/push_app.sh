#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  printf 'Usage: %s [IMAGE_NAME] [TAG]\n' "$0"
  printf 'Default image: %s:latest\n' "${DOCKERHUB_IMAGE:-nguyennhat4/p047}"
  exit 0
fi

if [[ "$#" -gt 2 ]]; then
  printf 'Error: expected at most an image name and a tag.\n' >&2
  printf 'Usage: %s [IMAGE_NAME] [TAG]\n' "$0" >&2
  exit 2
fi

IMAGE_NAME="${1:-${DOCKERHUB_IMAGE:-nguyennhat4/p047}}"
IMAGE_TAG="${2:-latest}"
IMAGE_REF="${IMAGE_NAME}:${IMAGE_TAG}"

command -v docker >/dev/null 2>&1 || {
  printf 'Error: docker is not installed or not available in PATH.\n' >&2
  exit 1
}

printf 'Building app image: %s\n' "$IMAGE_REF"
docker build \
  --file "$ROOT_DIR/Dockerfile" \
  --tag "$IMAGE_REF" \
  "$ROOT_DIR"

printf 'Pushing app image: %s\n' "$IMAGE_REF"
docker push "$IMAGE_REF"

printf 'Published app image successfully: %s\n' "$IMAGE_REF"
