"""Create a portable timestamped archive of Docker-local runtime data."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from shutil import make_archive


def main() -> None:
    parser = argparse.ArgumentParser(description="Archive the persistent Docker MVP data directory.")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output-dir", type=Path, default=Path("backups"))
    args = parser.parse_args()
    if not args.data_dir.is_dir():
        raise SystemExit(f"Data directory does not exist: {args.data_dir}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    print(make_archive(str(args.output_dir / f"p047-data-{stamp}"), "gztar", args.data_dir.parent, args.data_dir.name))


if __name__ == "__main__":
    main()
