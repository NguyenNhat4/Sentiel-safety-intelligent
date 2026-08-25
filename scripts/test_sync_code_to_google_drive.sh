#!/usr/bin/env bash

set -euo pipefail

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TEMP_DIR"' EXIT

mkdir -p "${TEMP_DIR}/bin"

cat >"${TEMP_DIR}/bin/rclone" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' '--- call ---' "$@" >>"$RCLONE_TEST_LOG"
EOF
chmod +x "${TEMP_DIR}/bin/rclone"

export PATH="${TEMP_DIR}/bin:${PATH}"
export RCLONE_TEST_LOG="${TEMP_DIR}/rclone.log"
export GOOGLE_DRIVE_REMOTE="team-drive"
export GOOGLE_DRIVE_DESTINATION="backups/P-047"

"${SCRIPT_DIR}/sync_code_to_google_drive.sh" --dry-run

mapfile -t log_lines <"$RCLONE_TEST_LOG"

contains_line() {
    local expected="$1"
    local line

    for line in "${log_lines[@]}"; do
        [[ "$line" == "$expected" ]] && return 0
    done
    return 1
}

readonly REPOSITORY_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
contains_line "${REPOSITORY_ROOT}/backend/app"
contains_line "team-drive:backups/P-047/backend/app"
contains_line "${REPOSITORY_ROOT}/vision"
contains_line "team-drive:backups/P-047/vision"
contains_line '- **/__pycache__/**'
contains_line '- **/*.py[co]'
contains_line '+ **/*.py'
contains_line '- **'
contains_line '--dry-run'
[[ "$(printf '%s\n' "${log_lines[@]}" | command grep -c '^--- call ---$')" == 2 ]]

printf 'Google Drive code sync script checks passed.\n'
