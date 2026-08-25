"""Benchmark YOLO inference latency and throughput on a video or image."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from statistics import mean
from typing import Any

import cv2
import numpy as np

DEFAULT_SOURCE = "data/test.mp4"
DEFAULT_MODEL = "models/yolo11n_safety_kd_best.pt"


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def load_frames(source: Path, limit: int | None) -> list[np.ndarray]:
    image = cv2.imread(str(source))
    if image is not None:
        return [image] * (limit or 1)

    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise ValueError(f"Cannot open source: {source}")

    frames: list[np.ndarray] = []
    try:
        while limit is None or len(frames) < limit:
            ok, frame = capture.read()
            if not ok:
                break
            frames.append(frame)
    finally:
        capture.release()

    if not frames:
        raise ValueError(f"Source contains no readable frames: {source}")
    return frames


def synchronize_device(device: str) -> None:
    if device == "cpu":
        return
    import torch

    if torch.cuda.is_available():
        torch.cuda.synchronize()


def summarize(
    *,
    model: str,
    source: Path,
    frames: list[np.ndarray],
    warmup: int,
    iterations: int,
    confidence: float,
    device: str,
    latencies_ms: list[float],
) -> dict[str, Any]:
    total_seconds = sum(latencies_ms) / 1000
    return {
        "model": model,
        "source": str(source),
        "device": device,
        "input_size": {"width": int(frames[0].shape[1]), "height": int(frames[0].shape[0])},
        "warmup_iterations": warmup,
        "measured_iterations": iterations,
        "confidence": confidence,
        "latency_ms": {
            "mean": mean(latencies_ms),
            "min": min(latencies_ms),
            "max": max(latencies_ms),
            "p50": percentile(latencies_ms, 0.50),
            "p95": percentile(latencies_ms, 0.95),
            "p99": percentile(latencies_ms, 0.99),
        },
        "throughput_fps": iterations / total_seconds if total_seconds else 0.0,
    }


def benchmark(
    *,
    model_path: Path,
    source: Path,
    warmup: int,
    iterations: int,
    frame_limit: int | None,
    confidence: float,
    device: str,
) -> dict[str, Any]:
    from ultralytics import YOLO

    frames = load_frames(source, frame_limit)
    model = YOLO(str(model_path))
    predict_options: dict[str, Any] = {"conf": confidence, "verbose": False}
    if device != "auto":
        predict_options["device"] = device

    for index in range(warmup):
        model.predict(frames[index % len(frames)], **predict_options)
    synchronize_device(device)

    latencies_ms: list[float] = []
    total_iterations = max(1, iterations)
    for index in range(total_iterations):
        frame = frames[index % len(frames)]
        started = time.perf_counter_ns()
        model.predict(frame, **predict_options)
        synchronize_device(device)
        latencies_ms.append((time.perf_counter_ns() - started) / 1_000_000)

    return summarize(
        model=str(model_path),
        source=source,
        frames=frames,
        warmup=warmup,
        iterations=total_iterations,
        confidence=confidence,
        device=device,
        latencies_ms=latencies_ms,
    )


def benchmark_pipeline(
    *,
    model_path: Path,
    source: Path,
    warmup: int,
    iterations: int,
    frame_limit: int | None,
    confidence: float,
    device: str,
) -> dict[str, Any]:
    from ultralytics import YOLO

    frames = load_frames(source, frame_limit)
    model = YOLO(str(model_path))
    predict_options: dict[str, Any] = {"conf": confidence, "verbose": False}
    if device != "auto":
        predict_options["device"] = device

    def run(frame: np.ndarray) -> None:
        model.predict(frame, classes=[0, 3, 4], **predict_options)

    for index in range(warmup):
        run(frames[index % len(frames)])
    synchronize_device(device)

    latencies_ms: list[float] = []
    total_iterations = max(1, iterations)
    for index in range(total_iterations):
        started = time.perf_counter_ns()
        run(frames[index % len(frames)])
        synchronize_device(device)
        latencies_ms.append((time.perf_counter_ns() - started) / 1_000_000)

    report = summarize(
        model=str(model_path),
        source=source,
        frames=frames,
        warmup=warmup,
        iterations=total_iterations,
        confidence=confidence,
        device=device,
        latencies_ms=latencies_ms,
    )
    report["pipeline"] = [str(model_path)]
    report["pipeline_classes"] = [[0, 3, 4]]
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=Path(DEFAULT_MODEL))
    parser.add_argument(
        "--pipeline",
        action="store_true",
        help="Match runtime with one Safety model call for person, hat and vest.",
    )
    parser.add_argument("--source", type=Path, default=Path(DEFAULT_SOURCE))
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--iterations", type=int, default=30)
    parser.add_argument("--frames", type=int, default=30, help="Frames loaded from a video source.")
    parser.add_argument("--confidence", type=float, default=0.35)
    parser.add_argument("--device", default="auto", help="auto, cpu, or a CUDA device such as 0.")
    parser.add_argument("--output", type=Path, help="Optional JSON output path.")
    args = parser.parse_args()
    if args.warmup < 0 or args.iterations < 1 or args.frames < 1:
        parser.error("warmup must be >= 0; iterations and frames must be >= 1")
    if not 0 <= args.confidence <= 1:
        parser.error("confidence must be between 0 and 1")
    return args


def main() -> None:
    args = parse_args()
    if not args.source.exists():
        raise SystemExit(f"Source not found: {args.source}")

    if args.pipeline:
        if not args.model.exists():
            raise SystemExit(f"Model not found: {args.model}")
        result = benchmark_pipeline(
            model_path=args.model,
            source=args.source,
            warmup=args.warmup,
            iterations=args.iterations,
            frame_limit=args.frames,
            confidence=args.confidence,
            device=args.device,
        )
    else:
        if not args.model.exists():
            raise SystemExit(f"Model not found: {args.model}")
        result = benchmark(
            model_path=args.model,
            source=args.source,
            warmup=args.warmup,
            iterations=args.iterations,
            frame_limit=args.frames,
            confidence=args.confidence,
            device=args.device,
        )
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
