from types import SimpleNamespace

import numpy as np

from vision.api import PersonTrackingFacade


class FakeValue:
    def __init__(self, value):
        self.value = value

    def item(self):
        return self.value

    def __float__(self):
        return float(self.value)


class FakeRow:
    def __init__(self, values):
        self.values = values

    def tolist(self):
        return self.values


class FakeBox:
    def __init__(self, track_id, xyxy):
        self.id = [FakeValue(track_id)]
        self.xyxy = [FakeRow(xyxy)]
        self.conf = [FakeValue(0.9)]


class FakeModel:
    def __init__(self):
        self.calls = []

    def track(self, frame, **kwargs):
        self.calls.append(kwargs)
        return [SimpleNamespace(boxes=[FakeBox(7, [10, 20, 30, 80])])]


def test_tracking_uses_bytetrack_and_persists_within_a_session():
    models = []

    def factory(_path):
        model = FakeModel()
        models.append(model)
        return model

    facade = PersonTrackingFacade("unused.pt", model_factory=factory)
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    first = facade.track("session-a", frame, now=0.0)
    second = facade.track("session-a", frame, now=0.5)
    other = facade.track("session-b", frame, now=0.5)

    assert first == second == other == [(10, 20, 20, 60, 0.9, 7)]
    assert len(models) == 2
    assert models[0].calls[0]["persist"] is True
    assert models[0].calls[0]["tracker"] == "bytetrack.yaml"


def test_tracking_preload_initializes_the_first_session_model_and_tracker_dependencies():
    models = []
    tracker_dependency_loads = []

    def factory(_path):
        model = FakeModel()
        models.append(model)
        return model

    facade = PersonTrackingFacade(
        "unused.pt",
        model_factory=factory,
        tracker_dependency_loader=lambda: tracker_dependency_loads.append(True),
    )

    facade.preload()

    assert len(models) == 1
    assert tracker_dependency_loads == [True]

    facade.track("session-a", np.zeros((100, 100, 3), dtype=np.uint8), now=0.0)
    assert len(models) == 1
