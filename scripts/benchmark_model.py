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


def create_synthetic_frames(limit: int | None) -> list[np.ndarray]:
    """Create a deterministic input when no authorized camera frame is available."""
    frame = np.zeros((SYNTHETIC_SIZE, SYNTHETIC_SIZE, 3), dtype=np.uint8)
    frame[:, :, 0] = np.arange(SYNTHETIC_SIZE, dtype=np.uint8)[None, :]
    frame[:, :, 1] = np.arange(SYNTHETIC_SIZE, dtype=np.uint8)[:, None]
    cv2.rectangle(frame, (160, 80), (480, 600), (40, 180, 220), thickness=-1)
    return [frame.copy() for _ in range(limit or 1)]


def load_benchmark_frames(
    source: Path,
    limit: int | None,
    *,
    synthetic: bool,
) -> list[np.ndarray]:
    return create_synthetic_frames(limit) if synthetic else load_frames(source, limit)


def synchronize_device(device: str) -> None:
    if device == "cpu":
        return
    import torch

    if torch.cuda.is_available():
        torch.cuda.synchronize()


def summarize(
    *,
    model: str,
    source: Path | str,
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
    synthetic: bool = False,
) -> dict[str, Any]:
    from ultralytics import YOLO

    frames = load_benchmark_frames(source, frame_limit, synthetic=synthetic)
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
        source="synthetic://640x640" if synthetic else source,
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
    synthetic: bool = False,
    tracking: bool = False,
) -> dict[str, Any]:
    from ultralytics import YOLO

    frames = load_benchmark_frames(source, frame_limit, synthetic=synthetic)
    model = YOLO(str(model_path))
    predict_options: dict[str, Any] = {"conf": confidence, "verbose": False}
    if device != "auto":
        predict_options["device"] = device

    def run(frame: np.ndarray) -> None:
        if tracking:
            model.track(
                frame,
                persist=True,
                tracker="bytetrack.yaml",
                classes=[0, 3, 4],
                **predict_options,
            )
        else:
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
        source="synthetic://640x640" if synthetic else source,
        frames=frames,
        warmup=warmup,
        iterations=total_iterations,
        confidence=confidence,
        device=device,
        latencies_ms=latencies_ms,
    )
    report["pipeline"] = [str(model_path)]
    report["pipeline_classes"] = [[0, 3, 4]]
    report["tracking"] = tracking
    return report


def build_device_comparison(
    *,
    cpu_report: dict[str, Any],
    gpu_report: dict[str, Any],
    gpu_info: dict[str, Any],
) -> dict[str, Any]:
    cpu_mean = float(cpu_report["latency_ms"]["mean"])
    gpu_mean = float(gpu_report["latency_ms"]["mean"])
    cpu_fps = float(cpu_report["throughput_fps"])
    gpu_fps = float(gpu_report["throughput_fps"])
    return {
        "comparison": "cpu_vs_cuda",
        "gpu": gpu_info,
        "cpu_report": cpu_report,
        "gpu_report": gpu_report,
        "speedup": {
            "mean_latency": cpu_mean / gpu_mean if gpu_mean else 0.0,
            "throughput": gpu_fps / cpu_fps if cpu_fps else 0.0,
        },
    }


def cuda_device_info() -> dict[str, Any]:
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable. Check nvidia-smi, NVIDIA Container Toolkit, and docker --gpus all.")
    properties = torch.cuda.get_device_properties(0)
    return {
        "name": torch.cuda.get_device_name(0),
        "memory_gb": round(properties.total_memory / 1024**3, 2),
        "torch": torch.__version__,
        "cuda_runtime": torch.version.cuda,
    }


def render_comparison_summary(report: dict[str, Any]) -> str:
    cpu = report["cpu_report"]
    gpu = report["gpu_report"]
    speedup = report["speedup"]
    return "\n".join(
        [
            "=== P-047 CPU vs NVIDIA GPU benchmark ===",
            f"GPU: {report['gpu']['name']} ({report['gpu']['memory_gb']:.2f} GB)",
            "Device    Mean ms    P50 ms    P95 ms    FPS",
            _summary_row("CPU", cpu),
            _summary_row("CUDA", gpu),
            f"GPU mean-latency speedup: {speedup['mean_latency']:.2f}x",
            f"GPU throughput speedup:   {speedup['throughput']:.2f}x",
        ]
    )


def _summary_row(label: str, report: dict[str, Any]) -> str:
    latency = report["latency_ms"]
    return (
        f"{label:<8} {latency['mean']:>8.2f} {latency['p50']:>9.2f} "
        f"{latency['p95']:>9.2f} {report['throughput_fps']:>7.2f}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=Path(DEFAULT_MODEL))
    parser.add_argument(
        "--pipeline",
        action="store_true",
        help="Match runtime with one Safety model call for person, hat and vest.",
    )
    parser.add_argument(
        "--tracking",
        action="store_true",
        help="Include session-style ByteTrack work in pipeline mode.",
    )
    parser.add_argument(
        "--compare-cpu-gpu",
        action="store_true",
        help="Run the same benchmark on CPU and cuda:0, then report the speedup.",
    )
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Use a deterministic 640x640 frame instead of reading --source.",
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
    if not args.synthetic and not args.source.exists():
        raise SystemExit(f"Source not found: {args.source}")

    if not args.model.exists():
        raise SystemExit(f"Model not found: {args.model}")

    common_options = {
        "model_path": args.model,
        "source": args.source,
        "warmup": args.warmup,
        "iterations": args.iterations,
        "frame_limit": args.frames,
        "confidence": args.confidence,
        "synthetic": args.synthetic,
    }
    runner = benchmark_pipeline if args.pipeline else benchmark
    if args.pipeline:
        common_options["tracking"] = args.tracking

    if args.compare_cpu_gpu:
        try:
            gpu_info = cuda_device_info()
        except RuntimeError as exc:
            raise SystemExit(str(exc)) from exc
        cpu_report = runner(device="cpu", **common_options)
        gpu_report = runner(device="cuda:0", **common_options)
        result = build_device_comparison(
            cpu_report=cpu_report,
            gpu_report=gpu_report,
            gpu_info=gpu_info,
        )
        print(render_comparison_summary(result))
    else:
        result = runner(device=args.device, **common_options)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
