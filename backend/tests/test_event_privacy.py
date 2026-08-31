import base64

import cv2
import numpy as np
import pytest

from backend.app.models.event import SafetyEvent
from backend.app.schemas.event import EventCreate, EventUpdate
from backend.app.services.event_service import EventPersistenceError, EventPrivacyError, EventService
from vision.pipeline import PrivacyRedactionError, redact_person_head_regions


def _patterned_frame() -> np.ndarray:
    rows, columns = np.indices((100, 120))
    frame = np.zeros((100, 120, 3), dtype=np.uint8)
    frame[:, :, 0] = (rows * 13 + columns * 7) % 255
    frame[:, :, 1] = (rows * 5 + columns * 17) % 255
    frame[:, :, 2] = (rows * 19 + columns * 3) % 255
    return frame


def _snapshot_data(frame: np.ndarray) -> str:
    success, encoded = cv2.imencode(".jpg", frame)
    assert success
    return f"data:image/jpeg;base64,{base64.b64encode(encoded.tobytes()).decode()}"


def _redact_person_head(frame: np.ndarray, people):
    return redact_person_head_regions(frame, people)


def _identity_annotator(frame: np.ndarray, people, detections):
    return frame


def _event_input(snapshot_data: str | None = None) -> EventCreate:
    payload = {
        "zone_id": "zone_01",
        "camera_id": "cam_01",
        "event_type": "zone_intrusion",
        "severity": "high",
        "status": "acknowledged",
        "acknowledged_by": "Safety Officer",
        "snapshot_data": snapshot_data,
    }
    if snapshot_data:
        payload["snapshot_people"] = [_snapshot_person()]
    return EventCreate.model_validate(payload)


def _snapshot_person() -> dict:
    return {
        "bbox": [20, 10, 80, 90],
        "confidence": 0.9,
        "foot_point": [50, 90],
        "inside_zone": True,
        "ppe": {
            "hat": {"status": "missing", "confidence": None},
            "vest": {"status": "unknown", "confidence": None},
        },
        "missing_required_ppe": ["hat"],
    }


def test_persists_snapshot_without_face_blur_and_sets_server_owned_metadata(db_session, tmp_path):
    frame = _patterned_frame()
    event_in = EventCreate.model_validate(
        {
            "zone_id": "zone_01",
            "camera_id": "cam_01",
            "event_type": "zone_intrusion",
            "severity": "high",
            "status": "acknowledged",
            "acknowledged_by": "Safety Officer",
            "snapshot_data": _snapshot_data(frame),
            "snapshot_people": [_snapshot_person()],
            "privacy_blurred": False,
            "snapshot_path": "/snapshots/client-supplied.jpg",
        }
    )
    service = EventService(
        db_session,
        snapshot_redactor=_redact_person_head,
        snapshot_annotator=_identity_annotator,
        snapshot_dir=tmp_path,
    )

    event = service.create_event(event_in)

    persisted_file = tmp_path / event.snapshot_path.rsplit("/", 1)[-1]
    persisted = cv2.imread(str(persisted_file), cv2.IMREAD_COLOR)
    assert event.privacy_blurred is True
    assert persisted_file.exists()
    assert event.snapshot_path != "/snapshots/client-supplied.jpg"
    assert persisted is not None


def test_default_yunet_adapter_does_not_blur_without_detected_face(db_session, tmp_path):
    event = EventService(db_session, snapshot_annotator=_identity_annotator, snapshot_dir=tmp_path).create_event(
        _event_input(_snapshot_data(_patterned_frame()))
    )

    persisted = cv2.imread(str(tmp_path / event.snapshot_path.rsplit("/", 1)[-1]), cv2.IMREAD_COLOR)
    assert event.privacy_blurred is True
    assert persisted is not None


def test_persists_boxes_after_redaction_using_review_frame_metadata(db_session, tmp_path):
    frame = _patterned_frame()
    event_in = EventCreate.model_validate(
        {
            "zone_id": "zone_01",
            "camera_id": "cam_01",
            "event_type": "zone_intrusion",
            "severity": "high",
            "status": "acknowledged",
            "acknowledged_by": "Safety Officer",
            "snapshot_data": _snapshot_data(frame),
            "snapshot_people": [_snapshot_person()],
            "snapshot_detections": [
                {
                    "class_id": 0,
                    "class_name": "hat",
                    "bbox": [25, 15, 45, 35],
                    "confidence": 0.8,
                    "person_index": 0,
                }
            ],
        }
    )
    recorded: dict[str, object] = {}
    source = cv2.imdecode(
        np.frombuffer(base64.b64decode(event_in.snapshot_data.split(",", 1)[-1]), dtype=np.uint8),
        cv2.IMREAD_COLOR,
    )
    assert source is not None

    def annotate(redacted, people, detections):
        recorded["redaction_input_unchanged"] = np.array_equal(redacted, source)
        recorded["people"] = people
        recorded["detections"] = detections
        annotated = redacted.copy()
        annotated[70:90, 95:115] = (1, 2, 3)
        return annotated

    event = EventService(
        db_session,
        snapshot_redactor=_redact_person_head,
        snapshot_annotator=annotate,
        snapshot_dir=tmp_path,
    ).create_event(event_in)

    persisted = cv2.imread(str(tmp_path / event.snapshot_path.rsplit("/", 1)[-1]), cv2.IMREAD_COLOR)
    assert recorded == {
        "redaction_input_unchanged": True,
        "people": [{"bbox": [20, 10, 80, 90], "confidence": 0.9, "inside_zone": True}],
        "detections": [
            {
                "class_id": 0,
                "class_name": "hat",
                "bbox": [25, 15, 45, 35],
                "confidence": 0.8,
                "person_index": 0,
            }
        ],
    }
    assert persisted is not None
    assert np.allclose(persisted[80, 105], [1, 2, 3], atol=15)


def test_privacy_failure_creates_neither_event_nor_snapshot(db_session, tmp_path):
    def fail_redaction(_: np.ndarray, people):
        raise PrivacyRedactionError("no candidate")

    service = EventService(db_session, snapshot_redactor=fail_redaction, snapshot_dir=tmp_path)

    with pytest.raises(EventPrivacyError, match="snapshot was not saved"):
        service.create_event(_event_input(_snapshot_data(_patterned_frame())))

    assert db_session.query(SafetyEvent).count() == 0
    assert list(tmp_path.iterdir()) == []


def test_database_failure_removes_the_redacted_snapshot(db_session, tmp_path, monkeypatch):
    service = EventService(db_session, snapshot_redactor=_redact_person_head, snapshot_dir=tmp_path)

    def fail_commit():
        raise RuntimeError("database is unavailable")

    monkeypatch.setattr(db_session, "commit", fail_commit)

    with pytest.raises(EventPersistenceError):
        service.create_event(_event_input(_snapshot_data(_patterned_frame())))

    assert list(tmp_path.iterdir()) == []


def test_snapshot_uses_the_configured_storage_provider(db_session):
    class RecordingStorage:
        def __init__(self):
            self.content = None

        def put(self, content: bytes) -> str:
            self.content = content
            return "snapshots/provider-owned.jpg"

        def get(self, key: str) -> bytes:
            raise AssertionError("event creation must not read the snapshot")

        def delete(self, key: str) -> None:
            raise AssertionError("successful event creation must not delete the snapshot")

        def check_connection(self) -> None:
            pass

    storage = RecordingStorage()

    event = EventService(
        db_session,
        snapshot_redactor=_redact_person_head,
        snapshot_annotator=_identity_annotator,
        snapshot_storage=storage,
    ).create_event(_event_input(_snapshot_data(_patterned_frame())))

    assert event.snapshot_path == "/snapshots/provider-owned.jpg"
    assert storage.content is not None
    assert cv2.imdecode(np.frombuffer(storage.content, dtype=np.uint8), cv2.IMREAD_COLOR) is not None


def test_events_without_snapshots_are_not_marked_as_blurred(db_session, tmp_path):
    event = EventService(db_session, snapshot_redactor=_redact_person_head, snapshot_dir=tmp_path).create_event(
        _event_input()
    )

    assert event.snapshot_path is None
    assert event.privacy_blurred is False


def test_unredacted_legacy_snapshot_cannot_be_acknowledged(db_session, tmp_path):
    legacy_event = SafetyEvent(
        zone_id="zone_01",
        camera_id="cam_01",
        event_type="zone_intrusion",
        snapshot_path="/snapshots/legacy.jpg",
        privacy_blurred=False,
        status="unacknowledged",
    )
    db_session.add(legacy_event)
    db_session.commit()

    with pytest.raises(EventPrivacyError, match="unredacted snapshot"):
        EventService(db_session, snapshot_dir=tmp_path).update_event(
            legacy_event.id,
            EventUpdate(status="acknowledged"),
        )
