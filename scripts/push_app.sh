#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PRODUCTION_ENV_FILE="${PRODUCTION_ENV_FILE:-$ROOT_DIR/.env.production}"

dotenv_value() {
  local key="$1"
  local value
  [[ -f "$PRODUCTION_ENV_FILE" ]] || return 0
  value="$(sed -n "s/^${key}=//p" "$PRODUCTION_ENV_FILE" | tail -n 1 | tr -d '\r')"
  if [[ "$value" == \"*\" && "$value" == *\" ]]; then
    value="${value:1:${#value}-2}"
  elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
    value="${value:1:${#value}-2}"
  fi
  printf '%s' "$value"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  printf 'Usage: %s [IMAGE_NAME] [TAG]\n' "$0"
  printf 'Default image: %s:latest\n' "${DOCKERHUB_IMAGE:-nguyennhat4/p047}"
  printf 'VITE_* values: process environment, then %s\n' "$PRODUCTION_ENV_FILE"
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
VITE_STREAMER_URL="${VITE_STREAMER_URL:-$(dotenv_value VITE_STREAMER_URL)}"
VITE_MEDIA_PUBLIC_ORIGIN="${VITE_MEDIA_PUBLIC_ORIGIN:-$(dotenv_value VITE_MEDIA_PUBLIC_ORIGIN)}"
VITE_STREAM_TRANSPORT="${VITE_STREAM_TRANSPORT:-$(dotenv_value VITE_STREAM_TRANSPORT)}"
VITE_STREAM_TRANSPORT="${VITE_STREAM_TRANSPORT:-hls}"

for public_url in "$VITE_STREAMER_URL" "$VITE_MEDIA_PUBLIC_ORIGIN"; do
  if [[ ! "$public_url" =~ ^https?://[^[:space:]]+$ ]] || [[ "$public_url" == *'${{'* ]]; then
    printf 'Error: VITE streamer/media URLs must be concrete http(s) URLs at frontend build time.\n' >&2
    printf 'Set VITE_STREAMER_URL and VITE_MEDIA_PUBLIC_ORIGIN in %s or the process environment.\n' "$PRODUCTION_ENV_FILE" >&2
    exit 1
  fi
done
if [[ "$VITE_STREAM_TRANSPORT" != "hls" ]]; then
  printf 'Error: production VITE_STREAM_TRANSPORT must be hls.\n' >&2
  exit 1
fi

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
  --build-arg "VITE_STREAMER_URL=$VITE_STREAMER_URL" \
  --build-arg "VITE_MEDIA_PUBLIC_ORIGIN=$VITE_MEDIA_PUBLIC_ORIGIN" \
  --build-arg "VITE_STREAM_TRANSPORT=$VITE_STREAM_TRANSPORT" \
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
