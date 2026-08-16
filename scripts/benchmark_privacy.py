"""Benchmark YuNet detection, mixed redaction and JPEG encoding on one snapshot."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

import cv2
import numpy as np

from vision.api import PrivacyRedactionFacade


def _load_frame(input_path: Path | None) -> np.ndarray:
    if input_path is None:
        rows, columns = np.indices((720, 1280))
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        frame[:, :, 0] = (rows * 13 + columns * 7) % 255
        frame[:, :, 1] = (rows * 5 + columns * 17) % 255
        frame[:, :, 2] = (rows * 19 + columns * 3) % 255
        return frame

    frame = cv2.imread(str(input_path), cv2.IMREAD_COLOR)
    if frame is not None:
        return frame

    capture = cv2.VideoCapture(str(input_path))
    try:
        ok, frame = capture.read()
    finally:
        capture.release()
    if not ok or frame is None:
        raise ValueError(f"Could not decode benchmark input: {input_path}")
    return frame


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * percentile)))
    return ordered[index]


def benchmark(
    frame: np.ndarray,
    *,
    model_path: str,
    score_threshold: float,
    face_margin_ratio: float,
    warmup: int,
    iterations: int,
) -> dict[str, object]:
    facade = PrivacyRedactionFacade(
        model_path,
        score_threshold=score_threshold,
        face_margin_ratio=face_margin_ratio,
    )
    facade.preload()
    height, width = frame.shape[:2]
    people = [{"bbox": [0, 0, width, height], "confidence": 1.0, "inside_zone": False}]

    for _ in range(warmup):
        result = facade.redact_snapshot(frame, people)
        ok, _ = cv2.imencode(".jpg", result["image"])
        if not ok:
            raise RuntimeError("Could not encode benchmark frame")

    durations_ms: list[float] = []
    result = None
    for _ in range(iterations):
        started = time.perf_counter()
        result = facade.redact_snapshot(frame, people)
        ok, _ = cv2.imencode(".jpg", result["image"])
        if not ok:
            raise RuntimeError("Could not encode benchmark frame")
        durations_ms.append((time.perf_counter() - started) * 1000)

    assert result is not None
    return {
        "iterations": iterations,
        "frame_width": width,
        "frame_height": height,
        "mean_ms": round(statistics.fmean(durations_ms), 3),
        "p50_ms": round(_percentile(durations_ms, 0.50), 3),
        "p95_ms": round(_percentile(durations_ms, 0.95), 3),
        "min_ms": round(min(durations_ms), 3),
        "max_ms": round(max(durations_ms), 3),
        "detected_face_count": result["detected_face_count"],
        "fallback_person_count": result["fallback_person_count"],
        "face_detector_failed": result["face_detector_failed"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--model", default="models/face_detection_yunet_2023mar.onnx")
    parser.add_argument("--score-threshold", type=float, default=0.6)
    parser.add_argument("--face-margin-ratio", type=float, default=0.2)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--iterations", type=int, default=30)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.warmup < 0 or args.iterations < 1:
        parser.error("--warmup must be non-negative and --iterations must be positive")

    report = benchmark(
        _load_frame(args.input),
        model_path=args.model,
        score_threshold=args.score_threshold,
        face_margin_ratio=args.face_margin_ratio,
        warmup=args.warmup,
        iterations=args.iterations,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
