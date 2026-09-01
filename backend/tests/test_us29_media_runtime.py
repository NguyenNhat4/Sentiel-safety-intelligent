import threading
import time
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np

import backend.app.api.v1.camera_sessions as camera_sessions_api
import backend.app.services.camera_session_runtime as camera_session_runtime_module
import backend.app.services.media_asset_service as media_asset_service_module
from backend.app.integrations.media_storage import PresignedUpload, StoredObjectMetadata
from backend.app.models.user import UserRole
from backend.app.schemas.analysis import FrameInferenceRequest, FrameInferenceResponse
from backend.app.schemas.camera_configuration import CameraConfigurationResponse, CameraConfigurationUpdate
from backend.app.schemas.ppe_requirement import PpeRequirementResponse
from backend.app.services.auth_service import AuthService
from backend.app.services.camera_configuration_service import CameraConfigurationService
from backend.app.services.camera_session_runtime import CameraSessionRuntime, SessionContext
from backend.app.services.frame_inference_service import FrameInferenceService
from backend.app.services.media_asset_service import media_asset_settings


def _png_bytes() -> bytes:
    encoded, buffer = cv2.imencode(".png", np.zeros((24, 32, 3), dtype=np.uint8))
    assert encoded
    return buffer.tobytes()


def _set_role(client, db_session, role: UserRole) -> None:
    user = AuthService(db_session).get_current_user(client.headers["Authorization"].split(" ", 1)[1])[0]
    user.role = role.value
    db_session.commit()


def _configuration_payload(asset_id: str, revision: int = 0) -> dict:
    return {
        "expected_revision": revision,
        "asset_id": asset_id,
        "machine_state": "running",
        "ppe_requirements": {
            "profile": "hat_vest_v1",
            "hat_required": True,
            "vest_required": False,
        },
        "zones": [
            {
                "zone_id": "press",
                "display_name": "Press",
                "points": [
                    {"x": 0.1, "y": 0.1},
                    {"x": 0.4, "y": 0.1},
                    {"x": 0.4, "y": 0.4},
                    {"x": 0.1, "y": 0.4},
                ],
                "enabled": True,
                "order": 0,
                "ppe_requirements": {
                    "profile": "hat_vest_v1",
                    "hat_required": True,
                    "vest_required": False,
                    "restricted_area_detection_enabled": False,
                    "zone_intrusion_enabled": True,
                },
            }
        ],
    }


def test_direct_camera_runtime_persists_pending_alert_before_publish(monkeypatch):
    captured = []

    class DummySession:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    class StoredEvent:
        id = 73

    class FakeEventService:
        def __init__(self, _db):
            pass

        def create_event(self, event):
            captured.append(event)
            return StoredEvent()

    monkeypatch.setattr(camera_session_runtime_module, "EventService", FakeEventService)
    runtime = CameraSessionRuntime(session_factory=DummySession, publish=lambda _payload: None)
    occurrence_id = str(uuid4())
    event_ids = runtime._persist_pending_reviews(
        {
            "type": "camera_inference_result",
            "camera_id": "cam_1",
            "session_id": str(uuid4()),
            "monitoring_session_id": str(uuid4()),
            "asset_id": str(uuid4()),
            "media_type": "video",
            "video_time": 3.5,
            "frame_id": 7,
            "frame_width": 100,
            "frame_height": 100,
            "session_status": "RUNNING",
            "inference_fps": 2.0,
            "result": "violate",
            "review_required": True,
            "snapshot_data": "data:image/jpeg;base64,AA==",
            "detections": [],
            "people": [
                {
                    "track_id": 9,
                    "bbox": [1, 2, 3, 4],
                    "confidence": 0.9,
                    "foot_point": [2, 4],
                    "inside_zone": False,
                    "ppe": {
                        "hat": {"status": "missing", "confidence": None},
                        "vest": {"status": "present", "confidence": 0.8},
                    },
                    "missing_required_ppe": ["hat"],
                    "active_violations": [
                        {
                            "occurrence_id": occurrence_id,
                            "rule_key": "missing_ppe:hat",
                            "zone_id": None,
                            "is_new": True,
                        }
                    ],
                }
            ],
            "rule": {
                "person_inside_zone": False,
                "machine_state": "running",
                "ppe_profile": "hat_vest_v1",
                "camera_id": "cam_1",
                "zone_id": "zone_01",
                "ppe_requirements": {"profile": "hat_vest_v1", "hat_required": True, "vest_required": False},
                "ppe_alert": True,
            },
        }
    )

    assert event_ids == [73]
    assert len(captured) == 1
    assert captured[0].status == "unacknowledged"
    assert captured[0].event_type == "missing_ppe"
    assert captured[0].zone_id == "camera_wide"
    assert [str(item) for item in captured[0].occurrence_ids] == [occurrence_id]
    assert "snapshot_data" not in captured[0].details["pending_review"]


def test_media_upload_is_admin_only_and_content_supports_ranges(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(media_asset_settings, "media_asset_dir", str(tmp_path))
    denied = client.post(
        "/api/v1/media-assets",
        data={"display_name": "Camera still"},
        files={"file": ("still.png", _png_bytes(), "image/png")},
    )
    assert denied.status_code == 403

    _set_role(client, db_session, UserRole.SYSTEM_ADMIN)
    uploaded = client.post(
        "/api/v1/media-assets",
        data={"display_name": "Camera still"},
        files={"file": ("../../still.png", _png_bytes(), "image/png")},
    )
    assert uploaded.status_code == 201
    body = uploaded.json()
    assert body["status"] == "READY"
    assert body["media_type"] == "image"
    assert body["storage_backend"] == "filesystem"
    assert "path" not in body
    assert list(tmp_path.iterdir())[0].name.startswith(body["id"])

    ranged = client.get(f"/api/v1/media-assets/{body['id']}/content", headers={"Range": "bytes=0-7"})
    assert ranged.status_code == 206
    assert ranged.headers["content-range"] == f"bytes 0-7/{body['size_bytes']}"
    assert len(ranged.content) == 8


def test_safety_manager_lists_only_ready_assets(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(media_asset_settings, "media_asset_dir", str(tmp_path))
    _set_role(client, db_session, UserRole.SYSTEM_ADMIN)
    ready = client.post(
        "/api/v1/media-assets",
        data={"display_name": "Ready"},
        files={"file": ("ready.png", _png_bytes(), "image/png")},
    ).json()
    corrupt = client.post(
        "/api/v1/media-assets",
        data={"display_name": "Broken"},
        files={"file": ("broken.png", b"not an image", "image/png")},
    )
    assert corrupt.status_code == 422

    _set_role(client, db_session, UserRole.SAFETY_MANAGER)
    assert [item["id"] for item in client.get("/api/v1/media-assets").json()] == [ready["id"]]


def test_direct_bucket_upload_validates_object_and_returns_presigned_playback(
    client, db_session, tmp_path, monkeypatch
):
    content = _png_bytes()

    class Storage:
        def prepare_upload(self, key, content_type, max_bytes):
            assert key.startswith("media-assets/")
            assert content_type == "image/png"
            assert max_bytes >= len(content)
            return PresignedUpload("https://bucket.example/upload", {"key": key})

        def head(self, key):
            return StoredObjectMetadata(len(content), "image/png")

        def download(self, key, path):
            path.write_bytes(content)

        def delete(self, key):
            raise AssertionError("valid upload must not be deleted")

        def playback_url(self, key):
            return f"https://bucket.example/{key}?signed=1"

    monkeypatch.setattr(media_asset_settings, "media_asset_dir", str(tmp_path))
    monkeypatch.setattr(media_asset_settings, "media_storage_backend", "s3")
    monkeypatch.setattr(media_asset_service_module, "create_media_storage", lambda _: Storage())
    _set_role(client, db_session, UserRole.SYSTEM_ADMIN)

    prepared = client.post(
        "/api/v1/media-assets/upload-requests",
        json={
            "display_name": "Bucket still",
            "filename": "still.png",
            "content_type": "image/png",
            "size_bytes": len(content),
        },
    )
    assert prepared.status_code == 201
    assert prepared.json()["asset"]["status"] == "UPLOADING"
    assert prepared.json()["upload_url"] == "https://bucket.example/upload"

    asset_id = prepared.json()["asset"]["id"]
    completed = client.post(f"/api/v1/media-assets/{asset_id}/complete")
    assert completed.status_code == 200
    assert completed.json()["status"] == "READY"
    assert completed.json()["storage_backend"] == "s3"
    playback = client.get(f"/api/v1/media-assets/{asset_id}/playback-url")
    assert playback.status_code == 200
    assert playback.json()["url"].startswith("https://bucket.example/media-assets/")


def test_system_admin_runs_every_configured_camera_and_replays_only_requested_camera(client, db_session, monkeypatch):
    _set_role(client, db_session, UserRole.SYSTEM_ADMIN)
    calls = []

    def start(db, camera_id):
        calls.append(camera_id)
        if camera_id in {"cam_3", "cam_4"}:
            from backend.app.services.camera_session_runtime import CameraSessionStartError

            raise CameraSessionStartError("camera_not_configured")
        return {
            "id": str(uuid4()),
            "camera_id": camera_id,
            "asset_id": str(uuid4()),
            "media_type": "video",
            "status": "STARTING",
            "config_revision": 1,
            "inference_fps": 0,
            "started_at": "2026-08-23T00:00:00Z",
            "running_at": None,
            "completed_at": None,
            "error_code": None,
        }

    monkeypatch.setattr(camera_sessions_api.camera_session_runtime, "start", start)
    run = client.post("/api/v1/simulation-runs")
    assert run.status_code == 200
    assert [item["camera_id"] for item in run.json()["sessions"]] == ["cam_1", "cam_2"]
    assert calls == ["cam_1", "cam_2", "cam_3", "cam_4"]

    calls.clear()
    replay = client.post("/api/v1/camera-sessions/cam_2/replay")
    assert replay.status_code == 200
    assert replay.json()["camera_id"] == "cam_2"
    assert calls == ["cam_2"]


def test_camera_configuration_is_fixed_revisioned_and_atomic(client, db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(media_asset_settings, "media_asset_dir", str(tmp_path))
    _set_role(client, db_session, UserRole.SYSTEM_ADMIN)
    asset = client.post(
        "/api/v1/media-assets",
        data={"display_name": "Still"},
        files={"file": ("still.png", _png_bytes(), "image/png")},
    ).json()
    initial = client.get("/api/v1/camera-configurations").json()
    assert [item["camera_id"] for item in initial] == ["cam_1", "cam_2", "cam_3", "cam_4"]
    saved = client.put("/api/v1/camera-configurations/cam_1", json=_configuration_payload(asset["id"]))
    assert saved.status_code == 200
    assert saved.json()["camera_name"] == "Still"
    assert saved.json()["revision"] == 1
    assert saved.json()["ppe_requirements"]["hat_required"] is True
    assert saved.json()["zones"][0]["ppe_requirements"]["hat_required"] is True

    conflict = client.put("/api/v1/camera-configurations/cam_2", json=_configuration_payload(asset["id"]))
    assert conflict.status_code == 409
    assert client.get("/api/v1/camera-configurations/cam_2").json()["asset_id"] is None
    stale = client.put(
        "/api/v1/camera-configurations/cam_1",
        json=_configuration_payload(asset["id"], revision=0),
    )
    assert stale.status_code == 409
    assert (
        client.put("/api/v1/camera-configurations/cam_9", json=_configuration_payload(asset["id"])).status_code == 404
    )


def test_camera_configuration_saves_camera_wide_ppe_without_zones(client):
    saved = client.put(
        "/api/v1/camera-configurations/cam_1",
        json={
            "expected_revision": 0,
            "asset_id": None,
            "machine_state": "running",
            "ppe_requirements": {
                "profile": "hat_vest_v1",
                "hat_required": True,
                "vest_required": True,
            },
            "zones": [],
        },
    )

    assert saved.status_code == 200
    assert saved.json()["zones"] == []
    assert saved.json()["ppe_requirements"]["hat_required"] is True
    assert saved.json()["ppe_requirements"]["vest_required"] is True


def test_camera_configuration_service_persists_camera_wide_ppe_without_zones(db_session):
    saved = CameraConfigurationService(db_session).save(
        "cam_2",
        CameraConfigurationUpdate.model_validate(
            {
                "expected_revision": 0,
                "asset_id": None,
                "machine_state": "running",
                "ppe_requirements": {
                    "profile": "hat_vest_v1",
                    "hat_required": True,
                    "vest_required": True,
                },
                "zones": [],
            }
        ),
    )

    assert saved.zones == []
    assert saved.ppe_requirements.hat_required is True
    assert saved.ppe_requirements.vest_required is True


def test_image_runtime_infers_once_and_releases_vision_state(tmp_path, monkeypatch):
    image_path = tmp_path / "still.png"
    image_path.write_bytes(_png_bytes())
    published = []
    inferred = []
    released = []
    monkeypatch.setattr(
        camera_session_runtime_module.frame_inference_service,
        "release_vision_session",
        released.append,
    )

    runtime = CameraSessionRuntime(
        session_factory=None,
        process_frame=lambda context, frame, frame_id, video_time, bypass: (
            inferred.append((frame_id, video_time, bypass)) or {"type": "camera_inference_result", "result": "normal"}
        ),
        publish=published.append,
    )
    runtime.start_in_memory(
        camera_id="cam_1",
        session_id="00000000-0000-0000-0000-000000000001",
        asset_id="00000000-0000-0000-0000-000000000002",
        media_type="image",
        path=image_path,
        config_revision=1,
    )

    deadline = time.monotonic() + 2
    while time.monotonic() < deadline and not any(item["session_status"] == "COMPLETED" for item in published):
        time.sleep(0.01)
    runtime.stop_all()

    assert inferred == [(1, 0.0, True)]
    assert released == ["00000000-0000-0000-0000-000000000001"]
    assert [item["session_status"] for item in published] == ["STARTING", "RUNNING", "COMPLETED"]
    assert all(item["session_id"] == "00000000-0000-0000-0000-000000000001" for item in published)


def test_image_inference_bypasses_ppe_and_intrusion_confirmation():
    service = FrameInferenceService(
        ppe_observer=lambda frame, people: [
            {
                "hat": {"status": "missing", "confidence": None},
                "vest": {"status": "present", "confidence": 0.9},
            }
            for _ in people
        ]
    )
    service._track_people = lambda session_id, frame: [(8, 4, 12, 18, 0.95, 1)]
    requirement = PpeRequirementResponse(
        camera_id="cam_1",
        zone_id="press",
        profile="hat_vest_v1",
        hat_required=True,
        vest_required=False,
        zone_intrusion_enabled=True,
        updated_at=None,
    )
    result = service.infer_decoded_frame(
        FrameInferenceRequest(
            image_data="",
            camera_id="cam_1",
            monitoring_session_id=uuid4(),
            frame_id=1,
            machine_state="running",
            zone_revision=1,
            zones=[
                {
                    "zone_id": "press",
                    "display_name": "Press",
                    "points": [
                        {"x": 0.1, "y": 0.1},
                        {"x": 0.9, "y": 0.1},
                        {"x": 0.9, "y": 0.95},
                        {"x": 0.1, "y": 0.95},
                    ],
                    "enabled": True,
                    "order": 0,
                }
            ],
        ),
        np.zeros((24, 32, 3), dtype=np.uint8),
        requirements=requirement,
        requirements_by_zone={"press": requirement},
        bypass_confirmation=True,
    )

    assert result.review_required is True
    assert {item.rule_key for item in result.people[0].active_violations} == {
        "missing_ppe:hat",
        "zone_intrusion:press",
    }


def test_camera_runtime_encodes_snapshot_only_when_review_is_required(monkeypatch):
    response = FrameInferenceResponse(
        result="violate",
        review_required=True,
        has_active_violation=True,
        people=[],
        rule={},
    )
    monkeypatch.setattr(
        camera_session_runtime_module.frame_inference_service,
        "infer_decoded_frame",
        lambda *args, **kwargs: response,
    )
    configuration = CameraConfigurationResponse(
        camera_id="cam_1",
        revision=1,
        asset_id=uuid4(),
        machine_state="running",
        zones=[],
        updated_at=None,
    )
    context = SessionContext(
        camera_id="cam_1",
        session_id=str(uuid4()),
        asset_id=str(configuration.asset_id),
        media_type="image",
        path=Path("."),
        config_revision=1,
        configuration=configuration,
    )

    payload = CameraSessionRuntime(session_factory=None)._infer_frame(
        context,
        np.zeros((24, 32, 3), dtype=np.uint8),
        1,
        0.0,
        True,
    )

    assert payload["snapshot_data"].startswith("data:image/jpeg;base64,")


def test_replacement_suppresses_old_session_inference_output(tmp_path):
    image_path = tmp_path / "still.png"
    image_path.write_bytes(_png_bytes())
    first_entered = threading.Event()
    published = []

    def process(context, frame, frame_id, video_time, bypass):
        if context.session_id.endswith("1"):
            first_entered.set()
            time.sleep(0.1)
        return {"type": "camera_inference_result", "result": "normal"}

    runtime = CameraSessionRuntime(session_factory=None, process_frame=process, publish=published.append)
    runtime.start_in_memory(
        camera_id="cam_1",
        session_id="00000000-0000-0000-0000-000000000001",
        asset_id="00000000-0000-0000-0000-000000000003",
        media_type="image",
        path=image_path,
        config_revision=1,
    )
    assert first_entered.wait(1)
    runtime.start_in_memory(
        camera_id="cam_1",
        session_id="00000000-0000-0000-0000-000000000002",
        asset_id="00000000-0000-0000-0000-000000000003",
        media_type="image",
        path=image_path,
        config_revision=1,
    )
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline and not any(
        item["session_id"].endswith("2") and item["session_status"] == "COMPLETED" for item in published
    ):
        time.sleep(0.01)
    runtime.stop_all()

    inference_sessions = [item["session_id"] for item in published if item["type"] == "camera_inference_result"]
    assert inference_sessions == ["00000000-0000-0000-0000-000000000002"]


def test_different_cameras_process_inference_concurrently(tmp_path):
    image_path = tmp_path / "still.png"
    image_path.write_bytes(_png_bytes())
    both_running = threading.Barrier(2)
    completed = threading.Event()

    def process(context, frame, frame_id, video_time, bypass):
        both_running.wait(timeout=1)
        completed.set()
        return {"type": "camera_inference_result", "result": "normal"}

    runtime = CameraSessionRuntime(session_factory=None, process_frame=process, publish=lambda payload: None)
    for index, camera_id in enumerate(("cam_1", "cam_2"), start=1):
        runtime.start_in_memory(
            camera_id=camera_id,
            session_id=f"00000000-0000-0000-0000-00000000000{index}",
            asset_id="00000000-0000-0000-0000-000000000003",
            media_type="image",
            path=image_path,
            config_revision=1,
        )

    assert completed.wait(2)
    runtime.stop_all()
