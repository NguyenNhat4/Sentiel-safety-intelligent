from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from ultralytics.engine.results import Results

from backend.app.core.database import Base
from backend.app.models.vision_tracking_state import VisionTrackingState
from backend.app.services.vision_tracking_state_service import (
    ExpiredVisionTrackingStateError,
    InvalidVisionTrackingStateError,
    StaleVisionFrameError,
    VisionTrackingStateConflictError,
    VisionTrackingStateService,
)
from vision.api import PpeVisionFacade


def tracking_state(frame_id: int = 0) -> dict:
    return {
        "schema_version": "bytetrack_ppe_state_v1",
        "tracker": {"frame_id": frame_id, "last_track_id": 0, "tracked": [], "lost": []},
        "smoother": {"temporal_frames": 3, "tracks": []},
    }


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_process_frame_creates_and_monotonically_advances_state(session_factory, monkeypatch):
    service = VisionTrackingStateService(session_factory=session_factory)
    calls = []
    metrics = []
    monkeypatch.setattr(
        "backend.app.services.vision_tracking_state_service.record_operational_event",
        lambda event_type, **fields: metrics.append((event_type, fields)),
    )

    def infer(revision, state):
        calls.append((revision, state))
        return {"frame": revision + 1}, tracking_state(revision + 1)

    assert service.process_frame("session-1", 1, infer) == {"frame": 1}
    assert service.process_frame("session-1", 2, infer) == {"frame": 2}

    assert calls == [(0, None), (1, tracking_state(1))]
    with session_factory() as db:
        row = db.get(VisionTrackingState, "session-1")
        assert (row.revision, row.last_frame_id, row.state_payload) == (2, 2, tracking_state(2))
    assert [event for event, _fields in metrics] == ["vision_tracking_state_persisted"] * 2
    assert metrics[-1][1]["payload_bytes"] > 0
    assert "state_payload" not in metrics[-1][1]


def test_process_frame_rejects_stale_frame_without_remote_inference(session_factory):
    service = VisionTrackingStateService(session_factory=session_factory)
    service.process_frame("session-1", 7, lambda revision, state: (None, tracking_state(1)))

    with pytest.raises(StaleVisionFrameError):
        service.process_frame(
            "session-1",
            7,
            lambda revision, state: pytest.fail("stale frame reached remote inference"),
        )


def test_process_frame_retries_once_from_the_winning_revision(session_factory):
    service = VisionTrackingStateService(session_factory=session_factory)
    service.process_frame("session-1", 1, lambda revision, state: (None, tracking_state(1)))
    seen_revisions = []

    def infer(revision, state):
        seen_revisions.append(revision)
        if revision == 1:
            with session_factory.begin() as db:
                db.execute(
                    update(VisionTrackingState)
                    .where(VisionTrackingState.monitoring_session_id == "session-1")
                    .values(revision=2, last_frame_id=2, state_payload=tracking_state(2))
                )
        return revision, tracking_state(revision + 1)

    assert service.process_frame("session-1", 3, infer) == 2
    assert seen_revisions == [1, 2]
    with session_factory() as db:
        row = db.get(VisionTrackingState, "session-1")
        assert (row.revision, row.last_frame_id) == (3, 3)


def test_process_frame_fails_closed_after_a_second_conflict(session_factory):
    service = VisionTrackingStateService(session_factory=session_factory)
    service.process_frame("session-1", 1, lambda revision, state: (None, tracking_state(1)))

    def always_loses(revision, state):
        with session_factory.begin() as db:
            db.execute(
                update(VisionTrackingState)
                .where(VisionTrackingState.monitoring_session_id == "session-1")
                .values(revision=revision + 1, last_frame_id=revision + 1, state_payload=tracking_state(revision + 1))
            )
        return None, tracking_state(revision + 1)

    with pytest.raises(VisionTrackingStateConflictError):
        service.process_frame("session-1", 10, always_loses)


def test_service_rejects_invalid_state_before_commit(session_factory):
    service = VisionTrackingStateService(session_factory=session_factory)
    invalid = tracking_state()
    invalid["tracker"]["last_track_id"] = -1

    with pytest.raises(InvalidVisionTrackingStateError):
        service.process_frame("session-1", 1, lambda revision, state: (None, invalid))

    with session_factory() as db:
        assert db.get(VisionTrackingState, "session-1") is None


def test_service_rejects_unsupported_persisted_contract_version(session_factory):
    service = VisionTrackingStateService(session_factory=session_factory)
    service.process_frame("session-1", 1, lambda revision, state: (None, tracking_state(1)))
    with session_factory.begin() as db:
        db.execute(
            update(VisionTrackingState)
            .where(VisionTrackingState.monitoring_session_id == "session-1")
            .values(contract_version="safety_vision_v999")
        )

    with pytest.raises(InvalidVisionTrackingStateError, match="unsupported version"):
        service.process_frame(
            "session-1",
            2,
            lambda revision, state: pytest.fail("unsupported state reached remote inference"),
        )


def test_service_rejects_oversized_state_before_commit(session_factory):
    service = VisionTrackingStateService(session_factory=session_factory, max_state_bytes=64)

    with pytest.raises(InvalidVisionTrackingStateError, match="size limit"):
        service.process_frame("session-1", 1, lambda revision, state: (None, tracking_state(1)))

    with session_factory() as db:
        assert db.get(VisionTrackingState, "session-1") is None


def test_expired_state_is_deleted_and_does_not_silently_restart(session_factory):
    service = VisionTrackingStateService(session_factory=session_factory)
    service.process_frame("expired", 1, lambda revision, state: (None, tracking_state(1)))
    with session_factory.begin() as db:
        db.execute(
            update(VisionTrackingState)
            .where(VisionTrackingState.monitoring_session_id == "expired")
            .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )

    with pytest.raises(ExpiredVisionTrackingStateError):
        service.process_frame(
            "expired",
            2,
            lambda revision, state: pytest.fail("expired state reached remote inference"),
        )

    with session_factory() as db:
        assert db.get(VisionTrackingState, "expired") is None


def test_end_session_and_expiry_remove_technical_state(session_factory):
    service = VisionTrackingStateService(session_factory=session_factory)
    service.process_frame("ended", 1, lambda revision, state: (None, tracking_state(1)))
    service.process_frame("expired", 1, lambda revision, state: (None, tracking_state(1)))
    service.end_session("ended")
    with session_factory.begin() as db:
        db.execute(
            update(VisionTrackingState)
            .where(VisionTrackingState.monitoring_session_id == "expired")
            .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )

    assert service.cleanup_expired(limit=10) == 1
    with session_factory() as db:
        assert db.get(VisionTrackingState, "ended") is None
        assert db.get(VisionTrackingState, "expired") is None


def test_persisted_state_survives_replica_alternation_and_restart(session_factory):
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    class Predictor:
        names = {0: "hat", 1: "nohat", 2: "novest", 3: "person", 4: "vest"}

        def __init__(self, frames):
            self._frames = iter(frames)

        def predict(self, image, **kwargs):
            return [
                Results(
                    image,
                    path="frame.jpg",
                    names=self.names,
                    boxes=np.asarray(next(self._frames), dtype=np.float32),
                )
            ]

    person = [10, 20, 30, 80, 0.9, 3]
    person_hat = [person, [12, 21, 22, 31, 0.9, 0]]
    replica_a = PpeVisionFacade(
        "unused.pt",
        model_factory=lambda _: Predictor([person_hat, person_hat]),
        temporal_frames=3,
    )
    replica_b = PpeVisionFacade(
        "unused.pt",
        model_factory=lambda _: Predictor([person_hat, [person]]),
        temporal_frames=3,
    )
    restarted_a = PpeVisionFacade(
        "unused.pt",
        model_factory=lambda _: Predictor([[person]]),
        temporal_frames=3,
    )
    service = VisionTrackingStateService(session_factory=session_factory)
    replicas = [replica_a, replica_b, replica_a, replica_b, restarted_a]
    results = []

    for frame_id, replica in enumerate(replicas, start=1):
        results.append(
            service.process_frame(
                "session-1",
                frame_id,
                lambda revision, state, replica=replica: replica.analyze_with_state(frame, state),
            )
        )

    assert [result["canonical_people"][0][5] for result in results] == [1] * 5
    assert [result["people"][0]["hat"]["status"] for result in results] == ["present"] * 5
    with session_factory() as db:
        row = db.get(VisionTrackingState, "session-1")
        assert (row.revision, row.last_frame_id) == (5, 5)
