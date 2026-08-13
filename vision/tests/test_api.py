import numpy as np

from vision.api import PpeVisionFacade


def test_ppe_detection_is_associated_only_with_the_containing_person():
    people = [(10, 10, 30, 80, 0.9), (60, 10, 30, 80, 0.9)]

    assert PpeVisionFacade._person_containing(25, 25, people) == 0
    assert PpeVisionFacade._person_containing(75, 25, people) == 1
    assert PpeVisionFacade._person_containing(50, 25, people) is None


def test_ppe_facade_exposes_only_canonical_person_hat_and_vest():
    class FakeBox:
        def __init__(self, class_id: int) -> None:
            self.cls = np.array([class_id])
            self.conf = np.array([0.8])
            self.xyxy = np.array([[10, 10, 20, 20]])

    class FakeModel:
        names = {0: "hat", 1: "nohat", 2: "novest", 3: "person", 4: "vest"}

        def __init__(self):
            self.calls = 0

        def predict(self, frame, classes, conf, verbose):
            self.calls += 1
            assert classes == [0, 3, 4]
            result = type("Result", (), {})()
            result.names = self.names
            result.boxes = [FakeBox(class_id) for class_id in range(5)]
            return [result]

    facade = PpeVisionFacade("unused.pt")
    model = FakeModel()
    facade._model = model

    result = facade.observe(np.zeros((40, 40, 3), dtype=np.uint8), [(0, 0, 30, 30, 0.9)])

    assert [(item["class_id"], item["class_name"]) for item in result["detections"]] == [
        (3, "person"),
        (0, "hat"),
        (4, "vest"),
    ]
    assert all(item["person_index"] == 0 for item in result["detections"])
    assert result["people"][0]["hat"] == {"status": "present", "confidence": 0.8}
    assert result["people"][0]["vest"] == {"status": "present", "confidence": 0.8}
    assert model.calls == 1


def test_ppe_facade_keeps_unassociated_hat_when_no_person_is_detected():
    class FakeBox:
        cls = np.array([0])
        conf = np.array([0.79])
        xyxy = np.array([[10, 10, 20, 20]])

    class FakeModel:
        names = {0: "hat", 1: "nohat", 2: "novest", 3: "person", 4: "vest"}

        def predict(self, frame, classes, conf, verbose):
            result = type("Result", (), {})()
            result.names = self.names
            result.boxes = [FakeBox()]
            return [result]

    facade = PpeVisionFacade("unused.pt")
    facade._model = FakeModel()

    result = facade.observe(np.zeros((40, 40, 3), dtype=np.uint8), [])

    assert result == {
        "people": [],
        "detections": [
            {"class_id": 0, "class_name": "hat", "bbox": [10, 10, 20, 20], "confidence": 0.79, "person_index": None}
        ],
    }


def test_ppe_model_person_supports_association_without_replacing_canonical_person():
    class FakeBox:
        def __init__(self, class_id: int, bbox: list[int]) -> None:
            self.cls = np.array([class_id])
            self.conf = np.array([0.8])
            self.xyxy = np.array([bbox])

    class FakeModel:
        names = {0: "hat", 1: "nohat", 2: "novest", 3: "person", 4: "vest"}

        def predict(self, frame, classes, conf, verbose):
            result = type("Result", (), {})()
            result.names = self.names
            result.boxes = [
                FakeBox(3, [8, 5, 50, 95]),
                FakeBox(0, [36, 10, 46, 20]),
            ]
            return [result]

    facade = PpeVisionFacade("unused.pt")
    facade._model = FakeModel()

    result = facade.observe(np.zeros((100, 100, 3), dtype=np.uint8), [(10, 10, 30, 80, 0.9)])

    assert result["detections"] == [
        {
            "class_id": 3,
            "class_name": "person",
            "bbox": [10, 10, 40, 90],
            "confidence": 0.9,
            "person_index": 0,
        },
        {
            "class_id": 0,
            "class_name": "hat",
            "bbox": [36, 10, 46, 20],
            "confidence": 0.8,
            "person_index": 0,
        },
    ]


def test_ppe_facade_rejects_an_unexpected_checkpoint_mapping():
    class FakeModel:
        names = {0: "person", 1: "hat", 2: "vest"}

    facade = PpeVisionFacade("unused.pt")
    facade._model = FakeModel()

    with np.testing.assert_raises_regex(RuntimeError, "class mapping"):
        facade.preload()


def test_ppe_facade_requires_exact_checkpoint_label_casing():
    class FakeModel:
        names = {0: "Hat", 1: "nohat", 2: "novest", 3: "person", 4: "vest"}

    facade = PpeVisionFacade("unused.pt")
    facade._model = FakeModel()

    with np.testing.assert_raises_regex(RuntimeError, "class mapping"):
        facade.preload()
