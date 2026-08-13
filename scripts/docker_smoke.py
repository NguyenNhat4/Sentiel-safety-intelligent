"""Repeatable black-box smoke check for a running local Docker MVP."""

from __future__ import annotations

import json
import os
import sys
from urllib.request import urlopen


def get_json(url: str) -> dict:
    with urlopen(url, timeout=10) as response:  # noqa: S310 - operator supplied URL
        if response.status != 200:
            raise RuntimeError(f"Unexpected HTTP status {response.status} for {url}")
        return json.loads(response.read())


def main() -> None:
    base_url = os.environ.get("SMOKE_BASE_URL", "http://localhost:8000").rstrip("/")
    health = get_json(f"{base_url}/health")
    if not health.get("ready") or not health.get("runtime_files", {}).get("models_verified"):
        raise RuntimeError(f"Service is not ready: {health}")
    with urlopen(f"{base_url}/", timeout=10) as response:  # noqa: S310 - operator supplied URL
        body = response.read().decode("utf-8")
    if "Sentinel" not in body:
        raise RuntimeError("Production frontend was not served")
    print("Docker MVP smoke check passed")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Docker MVP smoke check failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
