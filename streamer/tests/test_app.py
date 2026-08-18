from pathlib import Path

from fastapi.testclient import TestClient

from streamer.app import create_app


def test_health_and_camera_list(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))

    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/api/cameras").json() == []


def test_uploads_video_and_lists_camera(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))

    response = client.post(
        "/api/cameras/cam_1",
        files={"video": ("sample.mp4", b"not-a-real-video", "video/mp4")},
    )

    assert response.status_code == 200
    assert response.json() == {"camera_id": "cam_1", "stream_url": "/stream/cam_1"}
    assert client.get("/api/cameras").json() == ["cam_1"]
    assert (tmp_path / "cam_1.mp4").read_bytes() == b"not-a-real-video"


def test_rejects_invalid_camera_and_extension(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))

    assert (
        client.post(
            "/api/cameras/cam.1",
            files={"video": ("sample.mp4", b"video", "video/mp4")},
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/cameras/cam_1",
            files={"video": ("sample.txt", b"text", "text/plain")},
        ).status_code
        == 415
    )
