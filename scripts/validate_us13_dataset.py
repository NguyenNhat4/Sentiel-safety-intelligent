#!/usr/bin/env python3
"""Validate the versioned manifest used for the US-13 evaluation dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

REQUIRED_VIDEO_FIELDS = {
    "video_id",
    "scenario_id",
    "split",
    "media_uri",
    "media_sha256",
    "annotation_path",
    "annotation_sha256",
    "consent_record_id",
}
VALID_SPLITS = {"calibration", "final"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_manifest(manifest_path: Path) -> list[str]:
    """Return all detected validation errors without modifying dataset files."""
    errors: list[str] = []
    try:
        manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"Cannot read manifest: {error}"]

    for field in ("dataset_id", "dataset_version", "annotation_schema_version", "split_policy", "videos"):
        if not manifest.get(field):
            errors.append(f"Missing top-level field: {field}")

    videos = manifest.get("videos")
    if not isinstance(videos, list) or not videos:
        return errors + ["videos must be a non-empty list"]

    video_splits: dict[str, str] = {}
    scenario_splits: dict[str, set[str]] = {}
    for index, video in enumerate(videos):
        label = f"videos[{index}]"
        if not isinstance(video, dict):
            errors.append(f"{label} must be an object")
            continue
        missing = REQUIRED_VIDEO_FIELDS - video.keys()
        if missing:
            errors.append(f"{label} missing fields: {', '.join(sorted(missing))}")
            continue

        video_id = video["video_id"]
        split = video["split"]
        if not isinstance(video_id, str) or not video_id:
            errors.append(f"{label}.video_id must be a non-empty string")
        elif video_id in video_splits:
            errors.append(f"Duplicate video_id: {video_id}")
        else:
            video_splits[video_id] = split

        if split not in VALID_SPLITS:
            errors.append(f"{label}.split must be calibration or final")
        scenario_id = video["scenario_id"]
        if isinstance(scenario_id, str) and scenario_id:
            scenario_splits.setdefault(scenario_id, set()).add(split)

        for checksum_field in ("media_sha256", "annotation_sha256"):
            checksum = video[checksum_field]
            if (
                not isinstance(checksum, str)
                or len(checksum) != 64
                or any(c not in "0123456789abcdef" for c in checksum.lower())
            ):
                errors.append(f"{label}.{checksum_field} must be a 64-character SHA-256 hex digest")

        annotation_path = manifest_path.parent / video["annotation_path"]
        if annotation_path.is_file() and sha256_file(annotation_path) != video["annotation_sha256"].lower():
            errors.append(f"{label}.annotation_sha256 does not match {annotation_path}")

    for scenario_id, splits in scenario_splits.items():
        if len(splits) > 1:
            errors.append(f"Scenario leaks across splits: {scenario_id}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a US-13 dataset manifest")
    parser.add_argument("manifest", type=Path, help="Path to manifest JSON")
    args = parser.parse_args()

    errors = validate_manifest(args.manifest)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"OK: {args.manifest} is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
