"""Restore a verified Docker-local data archive after the operator stops Compose."""

from __future__ import annotations

import argparse
import tarfile
from pathlib import Path, PurePosixPath


def _validate_members(members: list[tarfile.TarInfo], target_dir: Path) -> None:
    archive_root = target_dir.name
    for member in members:
        member_path = PurePosixPath(member.name)
        if (
            member_path.is_absolute()
            or ".." in member_path.parts
            or not member_path.parts
            or member_path.parts[0] != archive_root
            or not (member.isdir() or member.isfile())
        ):
            raise SystemExit("Archive contains an unsafe or unexpected path")


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
        _validate_members(members, args.target_dir)
        archive.extractall(args.target_dir.parent, members)
    print(f"Restored {args.archive} to {args.target_dir}")


if __name__ == "__main__":
    main()
