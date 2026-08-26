from types import SimpleNamespace

import numpy as np
from ultralytics.engine.results import Boxes, Results
from ultralytics.trackers.basetrack import TrackState

from vision.api import PpeTemporalSmoother, PpeVisionFacade
from vision.tracking_state import (
    create_bytetrack,
    export_bytetrack_state,
    restore_bytetrack_state,
)


class FakeValue:
    def __init__(self, value):
        self.value = value

    def item(self):
        return self.value

    def __float__(self):
        return float(self.value)

    def __int__(self):
        return int(self.value)


class FakeRow:
    def __init__(self, values):
        self.values = values

    def tolist(self):
        return self.values


class FakeBox:
    def __init__(self, class_id, xyxy, *, track_id=None):
        self.cls = [FakeValue(class_id)]
        self.id = None if track_id is None else [FakeValue(track_id)]
        self.xyxy = [FakeRow(xyxy)]
        self.conf = [FakeValue(0.9)]


class FakeModel:
    names = {0: "hat", 1: "nohat", 2: "novest", 3: "person", 4: "vest"}

    def __init__(self):
        self.calls = []

    def track(self, frame, **kwargs):
        self.calls.append(kwargs)
        return [
            SimpleNamespace(
                names=self.names,
                boxes=[
                    FakeBox(3, [10, 20, 30, 80], track_id=7),
                    FakeBox(0, [12, 21, 22, 31]),
                ],
            )
        ]


def test_unified_safety_inference_tracks_people_and_ppe_in_one_call():
    models = []

    def factory(_path):
        model = FakeModel()
        models.append(model)
        return model

    facade = PpeVisionFacade("unused.pt", model_factory=factory)
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    first = facade.analyze(frame, "session-a", now=0.0)
    second = facade.analyze(frame, "session-a", now=0.5)
    other = facade.analyze(frame, "session-b", now=0.5)

    assert (
        first["canonical_people"]
        == second["canonical_people"]
        == other["canonical_people"]
        == [(10, 20, 20, 60, 0.9, 7)]
    )
    assert first["people"][0]["hat"] == {"status": "present", "confidence": 0.9}
    assert [item["class_name"] for item in first["detections"]] == ["person", "hat"]
    assert len(models) == 2
    assert models[0].calls[0]["persist"] is True
    assert models[0].calls[0]["tracker"] == "bytetrack.yaml"
    assert models[0].calls[0]["classes"] == [0, 3, 4]
    assert models[0].calls[0]["conf"] == 0.2
    assert models[0].calls[0]["imgsz"] == 960
    assert models[0].calls[0]["rect"] is False
    assert len(models[0].calls) == 2


def test_smoother_holds_present_during_grace_period():
    """After N confirmed-present frames, a single 'missing' frame is smoothed to 'present'."""
    smoother = PpeTemporalSmoother(temporal_frames=3)
    track_id = 1

    # 3 frames where model detects hat
    for _ in range(3):
        hat, vest = smoother.smooth(track_id, raw_hat=True, raw_vest=False)
        assert hat is True

    # Frame 4: model misses hat — still within grace period
    hat, _ = smoother.smooth(track_id, raw_hat=False, raw_vest=False)
    assert hat is True, "Grace period should hold 'present' for one missed frame"


def test_smoother_transitions_to_missing_after_grace_exceeded():
    """After grace_frames consecutive misses, hat transitions to 'missing'."""
    smoother = PpeTemporalSmoother(temporal_frames=3)
    track_id = 2

    # Establish presence
    for _ in range(3):
        smoother.smooth(track_id, raw_hat=True, raw_vest=False)

    # 3 grace frames — still 'present'
    for _ in range(3):
        hat, _ = smoother.smooth(track_id, raw_hat=False, raw_vest=False)
        assert hat is True, "Should remain present within grace period"

    # 4th miss — exceeds grace, must transition to missing
    hat, _ = smoother.smooth(track_id, raw_hat=False, raw_vest=False)
    assert hat is False, "Should report missing after grace period is exceeded"


def test_smoother_fresh_track_not_contaminated_by_other_tracks():
    """A new track_id starts without any history from other tracks."""
    smoother = PpeTemporalSmoother(temporal_frames=3)

    # Track 10 sees hat for 5 frames
    for _ in range(5):
        smoother.smooth(10, raw_hat=True, raw_vest=False)

    # Track 99 is brand new and must build its own three-frame absence history.
    states = [smoother.smooth(99, raw_hat=False, raw_vest=False)[0] for _ in range(3)]
    assert states == [None, None, False]


def test_smoother_purge_track_clears_state():
    """After purge_track, the track behaves as if it never existed."""
    smoother = PpeTemporalSmoother(temporal_frames=3)
    track_id = 5

    # Build presence history
    for _ in range(5):
        smoother.smooth(track_id, raw_hat=True, raw_vest=False)

    smoother.purge_track(track_id)
    assert track_id not in smoother.active_tracks()

    # After purge, first miss starts a fresh confirmation window.
    hat, _ = smoother.smooth(track_id, raw_hat=False, raw_vest=False)
    assert hat is None
    assert track_id in smoother.active_tracks()


def test_smoother_confirms_initial_absence_on_third_consecutive_frame():
    smoother = PpeTemporalSmoother(temporal_frames=3)
    track_id = 7

    states = [smoother.smooth(track_id, raw_hat=False, raw_vest=False)[0] for _ in range(3)]

    assert states == [None, None, False]


def test_smoother_requires_confirmed_presence_before_applying_grace():
    smoother = PpeTemporalSmoother(temporal_frames=3)

    assert smoother.smooth(11, raw_hat=True, raw_vest=False)[0] is True
    assert smoother.smooth(11, raw_hat=False, raw_vest=False)[0] is None


def test_smoother_keeps_hat_and_vest_histories_independent():
    smoother = PpeTemporalSmoother(temporal_frames=3)
    for _ in range(3):
        smoother.smooth(12, raw_hat=True, raw_vest=False)

    hat, vest = smoother.smooth(12, raw_hat=False, raw_vest=False)

    assert hat is True
    assert vest is False


def test_smoother_present_recovery_resets_the_missing_streak():
    smoother = PpeTemporalSmoother(temporal_frames=3)
    for _ in range(3):
        smoother.smooth(13, raw_hat=True, raw_vest=False)
    for _ in range(2):
        assert smoother.smooth(13, raw_hat=False, raw_vest=False)[0] is True

    assert smoother.smooth(13, raw_hat=True, raw_vest=False)[0] is True
    for _ in range(3):
        assert smoother.smooth(13, raw_hat=False, raw_vest=False)[0] is True
    assert smoother.smooth(13, raw_hat=False, raw_vest=False)[0] is False


def test_smoother_purges_track_after_lost_track_grace():
    smoother = PpeTemporalSmoother(temporal_frames=3)
    smoother.smooth(14, raw_hat=True, raw_vest=False)

    for _ in range(3):
        smoother.advance_tracks(set())
        assert 14 in smoother.active_tracks()
    smoother.advance_tracks(set())

    assert 14 not in smoother.active_tracks()


def test_smoother_rejects_invalid_frame_thresholds():
    with np.testing.assert_raises(ValueError):
        PpeTemporalSmoother(temporal_frames=0)


def test_one_temporal_value_controls_all_smoothing_windows():
    for temporal_frames in (3, 4, 5, 10):
        smoother = PpeTemporalSmoother(temporal_frames=temporal_frames)

        fresh_states = [smoother.smooth(100, raw_hat=False, raw_vest=False)[0] for _ in range(temporal_frames)]
        assert fresh_states == [None] * (temporal_frames - 1) + [False]

        for _ in range(temporal_frames):
            smoother.smooth(200, raw_hat=True, raw_vest=False)
        held_states = [smoother.smooth(200, raw_hat=False, raw_vest=False)[0] for _ in range(temporal_frames + 1)]
        assert held_states == [True] * temporal_frames + [False]

        smoother.smooth(300, raw_hat=True, raw_vest=False)
        for _ in range(temporal_frames):
            smoother.advance_tracks(set())
            assert 300 in smoother.active_tracks()
        smoother.advance_tracks(set())
        assert 300 not in smoother.active_tracks()


def test_facade_applies_smoothing_across_tracked_frames_without_emitting_missing():
    class SequencedModel:
        names = FakeModel.names

        def __init__(self):
            self.hat_presence = iter([True, True, True, False, False, False, False])

        def track(self, frame, **kwargs):
            boxes = [FakeBox(3, [10, 20, 30, 80], track_id=7)]
            if next(self.hat_presence):
                boxes.append(FakeBox(0, [12, 21, 22, 31]))
            return [SimpleNamespace(names=self.names, boxes=boxes)]

    model = SequencedModel()
    facade = PpeVisionFacade("unused.pt", model_factory=lambda _path: model, temporal_frames=3)
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    statuses = [
        facade.analyze(frame, "session-smoothing", now=float(index))["people"][0]["hat"]["status"] for index in range(7)
    ]

    assert statuses == ["present", "present", "present", "present", "present", "present", "unknown"]


def test_facade_marks_initial_absence_confirmed_only_on_third_frame():
    class MissingHatModel:
        names = FakeModel.names

        @staticmethod
        def track(frame, **kwargs):
            return [
                SimpleNamespace(
                    names=FakeModel.names,
                    boxes=[FakeBox(3, [10, 20, 30, 80], track_id=7)],
                )
            ]

    facade = PpeVisionFacade(
        "unused.pt",
        model_factory=lambda _path: MissingHatModel(),
        temporal_frames=3,
    )
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    results = [facade.analyze(frame, "session-initial-miss", now=float(index)) for index in range(3)]

    assert [result["people"][0]["hat"]["status"] for result in results] == ["unknown"] * 3
    assert [result["absence_confirmed"][0]["hat"] for result in results] == [False, False, True]


def test_facade_retains_smoothing_history_during_short_track_loss():
    class SequencedModel:
        names = FakeModel.names

        def __init__(self):
            self.frames = iter(["present", "present", "present", "absent", "missing"])

        def track(self, frame, **kwargs):
            state = next(self.frames)
            if state == "absent":
                boxes = []
            else:
                boxes = [FakeBox(3, [10, 20, 30, 80], track_id=7)]
                if state == "present":
                    boxes.append(FakeBox(0, [12, 21, 22, 31]))
            return [SimpleNamespace(names=self.names, boxes=boxes)]

    model = SequencedModel()
    facade = PpeVisionFacade("unused.pt", model_factory=lambda _path: model, temporal_frames=3)
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    for index in range(3):
        facade.analyze(frame, "session-track-loss", now=float(index))
    assert facade.analyze(frame, "session-track-loss", now=3.0)["people"] == []
    resumed = facade.analyze(frame, "session-track-loss", now=4.0)

    assert resumed["people"][0]["hat"]["status"] == "present"


def test_facade_session_expiry_and_explicit_end_clear_smoothing_state():
    facade = PpeVisionFacade("unused.pt", session_ttl_seconds=5.0)
    facade._sessions["expired"] = (object(), 0.0)
    facade._smoothers["expired"] = PpeTemporalSmoother()
    facade._expire_sessions(now=5.0)

    assert "expired" not in facade._sessions
    assert "expired" not in facade._smoothers

    facade._sessions["ended"] = (object(), 6.0)
    facade._smoothers["ended"] = PpeTemporalSmoother()
    facade.end_session("ended")

    assert "ended" not in facade._sessions
    assert "ended" not in facade._smoothers


def _update_tracker(tracker, x: float):
    detections = (
        Boxes(
            np.array([[x, 10, x + 20, 60, 0.9, 3]], dtype=np.float32),
            orig_shape=(100, 100),
        )
        .cpu()
        .numpy()
    )
    return tracker.update(detections, np.zeros((100, 100, 3), dtype=np.uint8))


def test_bytetrack_state_round_trip_matches_uninterrupted_continuation():
    uninterrupted = create_bytetrack()
    for x in (10.0, 11.0):
        _update_tracker(uninterrupted, x)
    expected = _update_tracker(uninterrupted, 12.0)

    split = create_bytetrack()
    for x in (10.0, 11.0):
        _update_tracker(split, x)
    restored = restore_bytetrack_state(export_bytetrack_state(split))
    actual = _update_tracker(restored, 12.0)

    np.testing.assert_allclose(actual, expected, rtol=0.0, atol=1e-6)
    assert actual[0, 4] == expected[0, 4] == 1
    assert restored.frame_id == uninterrupted.frame_id == 3


def test_bytetrack_export_excludes_terminal_tracks_from_lost_pool():
    tracker = create_bytetrack()
    _update_tracker(tracker, 10.0)
    terminal_track = tracker.tracked_stracks[0]
    terminal_track.mark_removed()
    tracker.tracked_stracks = []
    tracker.lost_stracks = [terminal_track]
    tracker.removed_stracks = [terminal_track]

    state = export_bytetrack_state(tracker)

    assert terminal_track.state == TrackState.Removed
    assert state["lost"] == []


def test_smoother_state_round_trip_preserves_presence_and_missing_streaks():
    uninterrupted = PpeTemporalSmoother(temporal_frames=3)
    split = PpeTemporalSmoother(temporal_frames=3)
    for raw_hat, raw_vest in ((True, False), (True, True), (True, True), (False, False)):
        uninterrupted.smooth(7, raw_hat=raw_hat, raw_vest=raw_vest)
        split.smooth(7, raw_hat=raw_hat, raw_vest=raw_vest)
    split.advance_tracks(set())
    uninterrupted.advance_tracks(set())

    restored = PpeTemporalSmoother.from_state(split.export_state())

    assert restored.export_state() == uninterrupted.export_state()
    assert restored.smooth(7, raw_hat=False, raw_vest=False) == uninterrupted.smooth(
        7,
        raw_hat=False,
        raw_vest=False,
    )


def test_portable_facade_state_preserves_ids_and_antiflicker_across_fresh_workers():
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    class PredictSequence:
        names = FakeModel.names

        def __init__(self, detections):
            self._detections = iter(detections)

        def predict(self, image, **kwargs):
            boxes = next(self._detections)
            return [Results(image, path="frame.jpg", names=self.names, boxes=np.asarray(boxes, dtype=np.float32))]

    frames = [
        [[10, 20, 30, 80, 0.9, 3], [12, 21, 22, 31, 0.9, 0]],
        [[11, 20, 31, 80, 0.9, 3], [13, 21, 23, 31, 0.9, 0]],
        [[12, 20, 32, 80, 0.9, 3], [14, 21, 24, 31, 0.9, 0]],
        [[13, 20, 33, 80, 0.9, 3]],
        [[14, 20, 34, 80, 0.9, 3]],
    ]
    uninterrupted = PpeVisionFacade(
        "unused.pt",
        model_factory=lambda _: PredictSequence(frames),
        temporal_frames=3,
    )
    expected = [uninterrupted.analyze_with_state(frame, None)]
    for _ in frames[1:]:
        expected.append(uninterrupted.analyze_with_state(frame, expected[-1][1]))

    first_worker = PpeVisionFacade(
        "unused.pt",
        model_factory=lambda _: PredictSequence(frames[:3]),
        temporal_frames=3,
    )
    state = None
    actual = []
    for _ in frames[:3]:
        result, state = first_worker.analyze_with_state(frame, state)
        actual.append((result, state))
    restarted_worker = PpeVisionFacade(
        "unused.pt",
        model_factory=lambda _: PredictSequence(frames[3:]),
        temporal_frames=3,
    )
    for _ in frames[3:]:
        result, state = restarted_worker.analyze_with_state(frame, state)
        actual.append((result, state))

    assert [item[0]["canonical_people"][0][5] for item in actual] == [
        item[0]["canonical_people"][0][5] for item in expected
    ]
    assert (
        [item[0]["people"][0]["hat"]["status"] for item in actual]
        == [item[0]["people"][0]["hat"]["status"] for item in expected]
        == ["present"] * 5
    )
    assert actual[-1][1] == expected[-1][1]


def test_portable_facade_keeps_alternating_session_states_isolated():
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    class AlternatingPredictor:
        names = FakeModel.names

        def predict(self, image, **kwargs):
            return [
                Results(
                    image,
                    path="frame.jpg",
                    names=self.names,
                    boxes=np.asarray([[10, 20, 30, 80, 0.9, 3]], dtype=np.float32),
                )
            ]

    facade = PpeVisionFacade(
        "unused.pt",
        model_factory=lambda _: AlternatingPredictor(),
        temporal_frames=3,
    )
    states = {"a": None, "b": None}
    track_ids = {"a": [], "b": []}

    for session_id in ("a", "b", "a", "b"):
        result, states[session_id] = facade.analyze_with_state(frame, states[session_id])
        track_ids[session_id].append(result["canonical_people"][0][5])

    assert track_ids == {"a": [1, 1], "b": [1, 1]}
    assert states["a"]["tracker"]["frame_id"] == 2
    assert states["b"]["tracker"]["frame_id"] == 2
