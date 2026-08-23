#!/usr/bin/env bash

set -euo pipefail

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly REPOSITORY_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

remote="${GOOGLE_DRIVE_REMOTE:-gdrive}"
destination="${GOOGLE_DRIVE_DESTINATION:-P-047-code}"
dry_run=false

usage() {
    cat <<'EOF'
Usage: ./scripts/sync_code_to_google_drive.sh [--dry-run]

Synchronize Python source code from backend/app and vision to Google Drive.

Environment variables:
  GOOGLE_DRIVE_REMOTE       rclone remote name without ':' (default: gdrive)
  GOOGLE_DRIVE_DESTINATION  destination folder in Drive (default: P-047-code)
EOF
}

while (($# > 0)); do
    case "$1" in
        --dry-run)
            dry_run=true
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            printf 'Unknown argument: %s\n' "$1" >&2
            usage >&2
            exit 2
            ;;
    esac
    shift
done

if ! command -v rclone >/dev/null 2>&1; then
    printf 'rclone is required. Install it from https://rclone.org/install/\n' >&2
    exit 1
fi

if [[ -z "$remote" || "$remote" == *:* ]]; then
    printf 'GOOGLE_DRIVE_REMOTE must be a non-empty rclone remote name without a colon.\n' >&2
    exit 2
fi

destination="${destination#/}"
destination="${destination%/}"
if [[ -z "$destination" ]]; then
    printf 'GOOGLE_DRIVE_DESTINATION must be a non-empty Drive folder.\n' >&2
    exit 2
fi

rclone_options=(
    --filter '- **/__pycache__/**'
    --filter '- **/*.py[co]'
    --filter '+ **/*.py'
    --filter '- **'
    --log-level INFO
)

if [[ "$dry_run" == true ]]; then
    rclone_options+=(--dry-run)
fi

sync_source() {
    local source_path="$1"
    local destination_path="$2"

    rclone sync \
        "$source_path" \
        "${remote}:${destination}/${destination_path}" \
        "${rclone_options[@]}"
}

sync_source "${REPOSITORY_ROOT}/backend/app" "backend/app"
sync_source "${REPOSITORY_ROOT}/vision" "vision"
