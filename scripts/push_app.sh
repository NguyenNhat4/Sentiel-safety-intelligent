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

if [[ "${SKIP_RAILWAY_REDEPLOY:-false}" != "true" ]]; then
  command -v railway >/dev/null 2>&1 || {
    printf 'Error: railway is not installed or not available in PATH.\n' >&2
    printf 'Set SKIP_RAILWAY_REDEPLOY=true to publish without redeploying.\n' >&2
    exit 1
  }
fi

printf 'Building app image: %s\n' "$IMAGE_REF"
docker build \
  --file "$ROOT_DIR/Dockerfile" \
  --tag "$IMAGE_REF" \
  "$ROOT_DIR"

printf 'Pushing app image: %s\n' "$IMAGE_REF"
docker push "$IMAGE_REF"

printf 'Published app image successfully: %s\n' "$IMAGE_REF"

if [[ "${SKIP_RAILWAY_REDEPLOY:-false}" == "true" ]]; then
  printf 'Railway redeploy skipped.\n'
  exit 0
fi

RAILWAY_SERVICE="${RAILWAY_APP_SERVICE:-p047-app}"
RAILWAY_ENVIRONMENT="${RAILWAY_ENVIRONMENT:-production}"
RAILWAY_ARGS=(--service "$RAILWAY_SERVICE" --environment "$RAILWAY_ENVIRONMENT")
if [[ -n "${RAILWAY_PROJECT_ID:-}" ]]; then
  RAILWAY_ARGS+=(--project "$RAILWAY_PROJECT_ID")
fi

export RAILWAY_CALLER="skill:use-railway@1.3.7"
export RAILWAY_AGENT_SESSION="railway-push-app-$(date +%s)-$$"

printf 'Redeploying Railway service %s from its latest image source...\n' "$RAILWAY_SERVICE"
railway redeploy --from-source --yes "${RAILWAY_ARGS[@]}"
printf 'Railway redeploy queued for %s in %s.\n' "$RAILWAY_SERVICE" "$RAILWAY_ENVIRONMENT"
