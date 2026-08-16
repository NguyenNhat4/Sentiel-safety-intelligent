from types import SimpleNamespace

import numpy as np

from vision.api import PpeVisionFacade


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
    assert models[0].calls[0]["device"] == "cpu"
    assert len(models[0].calls) == 2
