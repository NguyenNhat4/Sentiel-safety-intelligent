#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENVIRONMENT="production"
APP_SERVICE="p047-app"
STREAMER_SERVICE="streamer"
STREAMER_PORT="8080"
PROJECT_ID=""
SECRET_FILE="$ROOT_DIR/.env.production"
REDEPLOY=true
PUBLISH_APP=false

usage() {
  cat <<'EOF'
Usage: ./scripts/configure_railway_hls.sh [options]

Configure the shared HLS signing secret and Railway service references for
p047-app and streamer.

Options:
  --project ID          Railway project ID (default: linked project)
  --environment NAME    Railway environment (default: production)
  --app-service NAME    Backend/frontend service (default: p047-app)
  --streamer-service NAME
                        Stream gateway service (default: streamer)
  --streamer-port PORT  Streamer's internal listening port (default: 8080)
  --secret-file PATH    File containing HLS_TOKEN_SECRET=... (default: .env.production)
  --publish-app         Build and push the app image with VITE_* from the secret file,
                        then redeploy p047-app from the latest image source
  --no-redeploy         Set variables without redeploying either service
  -h, --help            Show this help

HLS_TOKEN_SECRET from the current process environment takes precedence over
--secret-file. The same value is written to both services without printing it.
EOF
}

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --project)
      PROJECT_ID="${2:?Error: --project requires an ID}"
      shift 2
      ;;
    --environment)
      ENVIRONMENT="${2:?Error: --environment requires a name}"
      shift 2
      ;;
    --app-service)
      APP_SERVICE="${2:?Error: --app-service requires a name}"
      shift 2
      ;;
    --streamer-service)
      STREAMER_SERVICE="${2:?Error: --streamer-service requires a name}"
      shift 2
      ;;
    --streamer-port)
      STREAMER_PORT="${2:?Error: --streamer-port requires a port}"
      shift 2
      ;;
    --secret-file)
      SECRET_FILE="${2:?Error: --secret-file requires a path}"
      shift 2
      ;;
    --publish-app)
      PUBLISH_APP=true
      shift
      ;;
    --no-redeploy)
      REDEPLOY=false
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Error: unknown option: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

command -v railway >/dev/null 2>&1 || {
  printf 'Error: Railway CLI is not installed or not available in PATH.\n' >&2
  exit 1
}

if [[ ! "$STREAMER_PORT" =~ ^[0-9]+$ ]] || (( STREAMER_PORT < 1 || STREAMER_PORT > 65535 )); then
  printf 'Error: --streamer-port must be an integer from 1 to 65535.\n' >&2
  exit 2
fi

if [[ -z "${HLS_TOKEN_SECRET:-}" ]]; then
  if [[ ! -f "$SECRET_FILE" ]]; then
    printf 'Error: HLS_TOKEN_SECRET is unset and secret file does not exist: %s\n' "$SECRET_FILE" >&2
    exit 1
  fi

  HLS_TOKEN_SECRET="$(sed -n 's/^HLS_TOKEN_SECRET=//p' "$SECRET_FILE" | tail -n 1 | tr -d '\r')"
  if [[ "$HLS_TOKEN_SECRET" == \"*\" && "$HLS_TOKEN_SECRET" == *\" ]]; then
    HLS_TOKEN_SECRET="${HLS_TOKEN_SECRET:1:${#HLS_TOKEN_SECRET}-2}"
  elif [[ "$HLS_TOKEN_SECRET" == \'*\' && "$HLS_TOKEN_SECRET" == *\' ]]; then
    HLS_TOKEN_SECRET="${HLS_TOKEN_SECRET:1:${#HLS_TOKEN_SECRET}-2}"
  fi
fi

if [[ "${#HLS_TOKEN_SECRET}" -lt 32 ]]; then
  printf 'Error: HLS_TOKEN_SECRET must contain at least 32 characters.\n' >&2
  exit 1
fi
if [[ "$HLS_TOKEN_SECRET" == *$'\n'* || "$HLS_TOKEN_SECRET" == *$'\r'* ]]; then
  printf 'Error: HLS_TOKEN_SECRET must not contain newline characters.\n' >&2
  exit 1
fi

RAILWAY_AGENT_SESSION="railway-hls-config-$(date +%s)-$$"
export RAILWAY_CALLER="skill:use-railway@1.3.7"
export RAILWAY_AGENT_SESSION

COMMON_ARGS=(--environment "$ENVIRONMENT")
if [[ -n "$PROJECT_ID" ]]; then
  COMMON_ARGS+=(--project "$PROJECT_ID")
fi
STREAMER_PUBLIC_REF='https://${{'"$STREAMER_SERVICE"'.RAILWAY_PUBLIC_DOMAIN}}'
STREAMER_PRIVATE_REF='http://${{'"$STREAMER_SERVICE"'.RAILWAY_PRIVATE_DOMAIN}}:'"$STREAMER_PORT"
APP_PUBLIC_REF='https://${{'"$APP_SERVICE"'.RAILWAY_PUBLIC_DOMAIN}}'

railway whoami --json >/dev/null
if [[ -z "$PROJECT_ID" ]]; then
  railway status --json >/dev/null
fi

printf 'Configuring HLS variables for %s and %s in %s...\n' \
  "$APP_SERVICE" "$STREAMER_SERVICE" "$ENVIRONMENT"

printf '%s' "$HLS_TOKEN_SECRET" | railway variable set HLS_TOKEN_SECRET \
  --stdin --skip-deploys --service "$APP_SERVICE" "${COMMON_ARGS[@]}" >/dev/null
railway variable set \
  "VITE_STREAMER_URL=$STREAMER_PUBLIC_REF" \
  "VITE_MEDIA_PUBLIC_ORIGIN=$STREAMER_PUBLIC_REF" \
  'VITE_STREAM_TRANSPORT=hls' \
  "STREAMER_INTERNAL_ORIGIN=$STREAMER_PRIVATE_REF" \
  'STREAMER_HEALTH_TIMEOUT_SECONDS=3' \
  --skip-deploys --service "$APP_SERVICE" "${COMMON_ARGS[@]}" >/dev/null

printf '%s' "$HLS_TOKEN_SECRET" | railway variable set HLS_TOKEN_SECRET \
  --stdin --skip-deploys --service "$STREAMER_SERVICE" "${COMMON_ARGS[@]}" >/dev/null
railway variable set \
  'HLS_UPSTREAM_ORIGIN=http://${{mediamtx.RAILWAY_PRIVATE_DOMAIN}}:8888' \
  "STREAMER_CORS_ORIGINS=$APP_PUBLIC_REF" \
  --skip-deploys --service "$STREAMER_SERVICE" "${COMMON_ARGS[@]}" >/dev/null

printf 'Variables configured successfully; the secret was not printed.\n'

if [[ "$PUBLISH_APP" == true ]]; then
  printf 'Building and publishing the app with frontend production URLs...\n'
  PRODUCTION_ENV_FILE="$SECRET_FILE" \
    SKIP_RAILWAY_REDEPLOY=true \
    "$ROOT_DIR/scripts/push_app.sh"
fi

if [[ "$REDEPLOY" == true ]]; then
  printf 'Redeploying %s and %s...\n' "$STREAMER_SERVICE" "$APP_SERVICE"
  railway redeploy --yes --service "$STREAMER_SERVICE" "${COMMON_ARGS[@]}" >/dev/null
  APP_REDEPLOY_ARGS=(--yes --service "$APP_SERVICE" "${COMMON_ARGS[@]}")
  if [[ "$PUBLISH_APP" == true ]]; then
    APP_REDEPLOY_ARGS+=(--from-source)
  fi
  railway redeploy "${APP_REDEPLOY_ARGS[@]}" >/dev/null
  printf 'Redeploys queued. Verify both deployments and then check p047-app /health.\n'
else
  printf 'Redeploy skipped. Redeploy both services before testing HLS.\n'
fi

if [[ "$PUBLISH_APP" == false ]]; then
  printf 'Note: Railway runtime variables were updated, but an existing prebuilt frontend image is unchanged.\n'
  printf 'Run again with --publish-app when VITE_* values changed.\n'
fi
