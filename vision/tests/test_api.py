import numpy as np

from vision.api import PpeVisionFacade


def test_ppe_detection_is_associated_only_with_the_containing_person():
    people = [(10, 10, 30, 80, 0.9), (60, 10, 30, 80, 0.9)]

    assert PpeVisionFacade._person_containing(25, 25, people) == 0
    assert PpeVisionFacade._person_containing(75, 25, people) == 1
    assert PpeVisionFacade._person_containing(50, 25, people) is None


def test_ppe_facade_exposes_each_sh17_class_with_optional_person_association():
    class FakeBox:
        def __init__(self, class_id: int) -> None:
            self.cls = np.array([class_id])
            self.conf = np.array([0.8])
            self.xyxy = np.array([[10, 10, 20, 20]])

    class FakeModel:
        def predict(self, frame, conf, verbose):
            result = type("Result", (), {})()
            result.names = {
                0: "person",
                1: "ear",
                2: "ear-mufs",
                3: "face",
                4: "face-guard",
                5: "face-mask",
                6: "foot",
                7: "tool",
                8: "glasses",
                9: "gloves",
                10: "helmet",
                11: "hands",
                12: "head",
                13: "medical-suit",
                14: "shoes",
                15: "safety-suit",
                16: "safety-vest",
            }
            result.boxes = [FakeBox(class_id) for class_id in range(17)]
            return [result]

    facade = PpeVisionFacade("unused.pt")
    facade._model = FakeModel()

    result = facade.observe(np.zeros((40, 40, 3), dtype=np.uint8), [(0, 0, 30, 30, 0.9)])

    assert [(item["class_id"], item["class_name"]) for item in result["detections"]] == list(
        enumerate(
            [
                "person",
                "ear",
                "ear-mufs",
                "face",
                "face-guard",
                "face-mask",
                "foot",
                "tool",
                "glasses",
                "gloves",
                "helmet",
                "hands",
                "head",
                "medical-suit",
                "shoes",
                "safety-suit",
                "safety-vest",
            ]
        )
    )
    assert all(item["person_index"] == 0 for item in result["detections"])
    assert result["people"][0]["helmet"] == {"status": "present", "confidence": 0.8}


def test_ppe_facade_keeps_unassociated_detection_when_no_person_is_detected():
    class FakeBox:
        cls = np.array([7])
        conf = np.array([0.79])
        xyxy = np.array([[10, 10, 20, 20]])

    class FakeModel:
        def predict(self, frame, conf, verbose):
            result = type("Result", (), {})()
            result.names = {7: "tool"}
            result.boxes = [FakeBox()]
            return [result]

    facade = PpeVisionFacade("unused.pt")
    facade._model = FakeModel()

    result = facade.observe(np.zeros((40, 40, 3), dtype=np.uint8), [])

    assert result == {
        "people": [],
        "detections": [
            {"class_id": 7, "class_name": "tool", "bbox": [10, 10, 20, 20], "confidence": 0.79, "person_index": None}
        ],
    }
