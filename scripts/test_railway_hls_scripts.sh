#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

docker() { printf 'DOCKER %s\n' "$*" >&2; }
railway() {
  if [[ " $* " == *" --stdin "* ]]; then
    while IFS= read -r -n 1 _; do :; done
  fi
  printf 'RAILWAY %s\n' "$*" >&2
}
export -f docker railway

output="$({
  HLS_TOKEN_SECRET=12345678901234567890123456789012 \
  VITE_STREAMER_URL=https://streamer.example.test \
  VITE_MEDIA_PUBLIC_ORIGIN=https://streamer.example.test \
  VITE_STREAM_TRANSPORT=hls \
    "$ROOT_DIR/scripts/configure_railway_hls.sh" \
      --publish-app --project test-project
} 2>&1)"

grep -F -- '--build-arg VITE_STREAMER_URL=https://streamer.example.test' <<<"$output" >/dev/null
grep -F -- '--build-arg VITE_MEDIA_PUBLIC_ORIGIN=https://streamer.example.test' <<<"$output" >/dev/null
grep -F -- 'redeploy --yes --service p047-app --environment production --project test-project --from-source' <<<"$output" >/dev/null
if grep -F '12345678901234567890123456789012' <<<"$output" >/dev/null; then
  printf 'Error: test secret leaked into script output.\n' >&2
  exit 1
fi

invalid_output="$({
  VITE_STREAMER_URL='https://${{streamer.RAILWAY_PUBLIC_DOMAIN}}' \
  VITE_MEDIA_PUBLIC_ORIGIN=https://streamer.example.test \
  SKIP_RAILWAY_REDEPLOY=true \
    "$ROOT_DIR/scripts/push_app.sh" example/p047 test
} 2>&1 || true)"
grep -F 'must be concrete http(s) URLs' <<<"$invalid_output" >/dev/null

printf 'Railway HLS deployment script checks passed.\n'
