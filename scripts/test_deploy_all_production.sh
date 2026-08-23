#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_BIN="$(mktemp -d)"
trap 'rm -rf "$TEST_BIN"' EXIT

for command_name in docker curl; do
  printf '#!/usr/bin/env bash\nexit 0\n' >"$TEST_BIN/$command_name"
  chmod +x "$TEST_BIN/$command_name"
done

cat >"$TEST_BIN/railway" <<'EOF'
#!/usr/bin/env bash
printf 'RAILWAY %s\n' "$*" >&2
if [[ "$1" == "deployment" ]]; then
  state_file="${RAILWAY_TEST_STATE:?}"
  count="$(cat "$state_file")"
  count=$((count + 1))
  printf '%s' "$count" >"$state_file"
  if (( count <= 2 )); then
    printf '[{"id":"old-deployment","status":"SUCCESS"}]\n'
  else
    printf '[{"id":"new-deployment","status":"SUCCESS"}]\n'
  fi
fi
EOF
chmod +x "$TEST_BIN/railway"

cat >"$TEST_BIN/make" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$TEST_BIN/make"

cat >"$TEST_BIN/npm" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
chmod +x "$TEST_BIN/npm"

mkdir -p "$TEST_BIN/.venv/bin"
printf '#!/usr/bin/env bash\nexit 0\n' >"$TEST_BIN/.venv/bin/pytest"
chmod +x "$TEST_BIN/.venv/bin/pytest"
mkdir -p "$TEST_BIN/scripts" "$TEST_BIN/backend/tests" "$TEST_BIN/frontend"
printf '#!/usr/bin/env bash\nexit 0\n' >"$TEST_BIN/scripts/push_app.sh"
chmod +x "$TEST_BIN/scripts/push_app.sh"
printf '0' >"$TEST_BIN/railway-state"

output="$({
  PATH="$TEST_BIN:$PATH" \
  POLL_INTERVAL_SECONDS=0 \
  DEPLOY_TIMEOUT_SECONDS=2 \
  APP_HEALTH_URL=https://app.example.test/health \
  ROOT_DIR_OVERRIDE="$TEST_BIN" \
  RAILWAY_TEST_STATE="$TEST_BIN/railway-state" \
    bash "$ROOT_DIR/scripts/deploy_all_production.sh"
} 2>&1 || true)"

grep -F 'redeploy --from-source --yes' <<<"$output" >/dev/null
grep -F 'Production deploy completed' <<<"$output" >/dev/null
printf 'Deploy-all production script checks passed.\n'
