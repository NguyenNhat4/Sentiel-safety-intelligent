"""Restore a verified Docker-local data archive after the operator stops Compose."""

from __future__ import annotations

import argparse
import tarfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore a p047 data archive into an empty directory.")
    parser.add_argument("archive", type=Path)
    parser.add_argument("--target-dir", type=Path, default=Path("data"))
    args = parser.parse_args()
    if not args.archive.is_file():
        raise SystemExit(f"Archive does not exist: {args.archive}")
    if args.target_dir.exists() and any(args.target_dir.iterdir()):
        raise SystemExit(f"Target must be empty before restore: {args.target_dir}")
    args.target_dir.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(args.archive, "r:gz") as archive:
        members = archive.getmembers()
        root = args.target_dir.parent.resolve()
        if any(not (root / member.name).resolve().is_relative_to(root) for member in members):
            raise SystemExit("Archive contains an unsafe path")
        archive.extractall(root, members, filter="data")
    print(f"Restored {args.archive} to {args.target_dir}")


if __name__ == "__main__":
    main()
