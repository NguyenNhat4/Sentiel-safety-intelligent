#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR_OVERRIDE:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
PROJECT_ID="${RAILWAY_PROJECT_ID:-3aeb66d7-0d02-4a6d-a9e8-57cac403b049}"
ENVIRONMENT="${RAILWAY_ENVIRONMENT:-production}"
APP_SERVICE="${RAILWAY_APP_SERVICE:-p047-app}"
STREAMER_SERVICE="${RAILWAY_STREAMER_SERVICE:-streamer}"
APP_IMAGE="${APP_IMAGE:-nguyennhat4/p047}"
APP_TAG="${APP_TAG:-latest}"
STREAMER_IMAGE="${STREAMER_IMAGE:-nguyennhat4/streamer}"
STREAMER_TAG="${STREAMER_TAG:-dev1}"
POLL_INTERVAL_SECONDS="${POLL_INTERVAL_SECONDS:-10}"
DEPLOY_TIMEOUT_SECONDS="${DEPLOY_TIMEOUT_SECONDS:-600}"
APP_HEALTH_URL="${APP_HEALTH_URL:-https://p047-production.up.railway.app/health}"
STREAMER_HEALTH_URL="${STREAMER_HEALTH_URL:-https://streamer-production-3002.up.railway.app/health}"
RAILWAY_AGENT_SESSION="${RAILWAY_AGENT_SESSION:-railway-deploy-all-$(date +%s)-$$}"
export RAILWAY_CALLER="skill:use-railway@1.3.7" RAILWAY_AGENT_SESSION

for command_name in docker railway jq curl; do
  command -v "$command_name" >/dev/null 2>&1 || {
    printf 'Error: required command is unavailable: %s\n' "$command_name" >&2
    exit 1
  }
done

latest_deployment_id() {
  railway deployment list \
    --project "$PROJECT_ID" \
    --environment "$ENVIRONMENT" \
    --service "$1" \
    --limit 1 \
    --json | jq -r '.[0].id // empty'
}

wait_for_deployment() {
  local service="$1"
  local previous_id="$2"
  local started_at deployment_json deployment_id status
  started_at="$(date +%s)"

  while true; do
    deployment_json="$(railway deployment list \
      --project "$PROJECT_ID" \
      --environment "$ENVIRONMENT" \
      --service "$service" \
      --limit 1 \
      --json)"
    deployment_id="$(jq -r '.[0].id // empty' <<<"$deployment_json")"
    status="$(jq -r '.[0].status // "UNKNOWN"' <<<"$deployment_json")"

    if [[ -n "$deployment_id" && "$deployment_id" != "$previous_id" ]]; then
      case "$status" in
        SUCCESS)
          printf '%s deployment %s reached SUCCESS.\n' "$service" "$deployment_id"
          return 0
          ;;
        FAILED|CRASHED|NEEDS_APPROVAL|SLEEPING|SKIPPED|REMOVED|REMOVING)
          printf 'Error: %s deployment %s reached %s.\n' "$service" "$deployment_id" "$status" >&2
          return 1
          ;;
      esac
    fi

    if (( $(date +%s) - started_at >= DEPLOY_TIMEOUT_SECONDS )); then
      printf 'Error: timed out waiting for a new %s deployment.\n' "$service" >&2
      return 1
    fi
    sleep "$POLL_INTERVAL_SECONDS"
  done
}

printf 'Running release checks...\n'
PYTHONPATH=. "$ROOT_DIR/.venv/bin/pytest" -q "$ROOT_DIR/backend/tests/test_hls_access.py"
make -C "$ROOT_DIR" streamer-test
npm --prefix "$ROOT_DIR/frontend" run lint -- --max-warnings=0
npm --prefix "$ROOT_DIR/frontend" test -- --run src/features/monitor/HlsVideo.test.tsx
npm --prefix "$ROOT_DIR/frontend" run build

app_previous_id="$(latest_deployment_id "$APP_SERVICE")"
streamer_previous_id="$(latest_deployment_id "$STREAMER_SERVICE")"

printf 'Building and pushing %s:%s...\n' "$APP_IMAGE" "$APP_TAG"
SKIP_RAILWAY_REDEPLOY=true "$ROOT_DIR/scripts/push_app.sh" "$APP_IMAGE" "$APP_TAG"

printf 'Building and pushing %s:%s...\n' "$STREAMER_IMAGE" "$STREAMER_TAG"
"$ROOT_DIR/scripts/push_streamer.sh" "$STREAMER_IMAGE" "$STREAMER_TAG"

printf 'Redeploying %s and %s in %s...\n' "$APP_SERVICE" "$STREAMER_SERVICE" "$ENVIRONMENT"
railway redeploy --from-source --yes \
  --project "$PROJECT_ID" --environment "$ENVIRONMENT" --service "$APP_SERVICE"
railway redeploy --from-source --yes \
  --project "$PROJECT_ID" --environment "$ENVIRONMENT" --service "$STREAMER_SERVICE"

wait_for_deployment "$APP_SERVICE" "$app_previous_id"
wait_for_deployment "$STREAMER_SERVICE" "$streamer_previous_id"

curl --fail --silent --show-error --max-time 15 "$APP_HEALTH_URL" >/dev/null
curl --fail --silent --show-error --max-time 15 "$STREAMER_HEALTH_URL" >/dev/null

printf 'Production deploy completed: %s and %s succeeded; both health endpoints are reachable.\n' "$APP_SERVICE" "$STREAMER_SERVICE"
