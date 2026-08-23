#!/usr/bin/env sh
set -eu

media_dir="${MEDIA_ASSET_DIR:-/app/data/media-assets}"
mkdir -p "$media_dir"
chown -R appuser:appuser "$media_dir"

exec gosu appuser "$@"
