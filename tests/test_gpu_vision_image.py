from pathlib import Path

from scripts.benchmark_model import (
    build_device_comparison,
    create_synthetic_frames,
    render_comparison_summary,
)

ROOT = Path(__file__).resolve().parents[1]


def test_gpu_worker_image_uses_cuda_torch_and_explicit_device():
    dockerfile = (ROOT / "Dockerfile.ai.gpu").read_text(encoding="utf-8")

    assert "https://download.pytorch.org/whl/cu128" in dockerfile
    assert "torch==2.9.1" in dockerfile
    assert "torchvision==0.24.1" in dockerfile
    assert "/whl/cpu" not in dockerfile
    assert "+cpu" not in dockerfile
    assert "VISION_DEVICE=cuda:0" in dockerfile
    assert "VISION_MODEL_VERSION=yolo11m_safety-gpu" in dockerfile
    assert "USER appuser" in dockerfile
    assert "chown -R" not in dockerfile
    assert "--chown=appuser:appuser /opt/venv" in dockerfile


def test_makefile_exposes_an_amd64_gpu_worker_build_target():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "vision-worker-gpu-image:" in makefile
    assert "--platform linux/amd64 -f Dockerfile.ai.gpu" in makefile


def test_benchmark_builds_a_deterministic_cpu_gpu_comparison():
    frames = create_synthetic_frames(2)
    cpu = {"latency_ms": {"mean": 80.0, "p50": 78.0, "p95": 90.0}, "throughput_fps": 12.5}
    gpu = {"latency_ms": {"mean": 20.0, "p50": 19.0, "p95": 24.0}, "throughput_fps": 50.0}

    comparison = build_device_comparison(
        cpu_report=cpu,
        gpu_report=gpu,
        gpu_info={"name": "Test GPU", "memory_gb": 8.0},
    )

    assert len(frames) == 2
    assert frames[0].shape == (640, 640, 3)
    assert (frames[0] == frames[1]).all()
    assert comparison["gpu"] == {"name": "Test GPU", "memory_gb": 8.0}
    assert comparison["speedup"]["mean_latency"] == 4.0
    assert comparison["speedup"]["throughput"] == 4.0
    assert "GPU mean-latency speedup: 4.00x" in render_comparison_summary(comparison)


def test_makefile_exposes_one_command_cpu_gpu_benchmark():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "vision-worker-benchmark: vision-worker-gpu-image" in makefile
    assert "--gpus all" in makefile
    assert "--compare-cpu-gpu" in makefile
    assert "--tracking" in makefile
