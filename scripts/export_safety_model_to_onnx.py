"""Export the approved YOLO11m Safety checkpoint to the runtime ONNX artifact."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

DEFAULT_SOURCE = Path("models/yolo11m_safety.pt")
DEFAULT_OUTPUT = Path("models/yolo11m_safety.onnx")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def export(source: Path, output: Path, image_size: int) -> Path:
    """Create a fixed-size ONNX graph with NMS for the CPU runtime."""
    if source != DEFAULT_SOURCE or output != DEFAULT_OUTPUT:
        raise ValueError("This controlled exporter only supports the approved Safety source and output paths")
    if not source.is_file():
        raise FileNotFoundError(f"Approved Safety source model is missing: {source}")

    from ultralytics import YOLO

    exported = Path(
        YOLO(str(source)).export(
            format="onnx",
            imgsz=image_size,
            dynamic=False,
            # Do not rely on Ultralytics' optional runtime auto-install of onnxslim.
            # The emitted graph is validated by the pinned ONNX Runtime smoke test.
            simplify=False,
            nms=True,
        )
    )
    if exported.resolve() != output.resolve():
        raise RuntimeError(f"Unexpected ONNX export path: {exported}")
    return exported


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--image-size", type=int, default=640)
    args = parser.parse_args()

    artifact = export(args.source, args.output, args.image_size)
    print(f"Exported {artifact} ({artifact.stat().st_size} bytes)")
    print(f"SHA-256: {sha256(artifact)}")


if __name__ == "__main__":
    main()
