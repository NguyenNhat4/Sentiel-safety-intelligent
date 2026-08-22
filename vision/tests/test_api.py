import numpy as np

from vision.api import PpeVisionFacade


def test_ppe_detection_is_associated_only_with_the_containing_person():
    people = [(10, 10, 30, 80, 0.9), (60, 10, 30, 80, 0.9)]

    assert PpeVisionFacade._best_person_for_ppe("hat", [20, 15, 30, 25], people) == 0
    assert PpeVisionFacade._best_person_for_ppe("hat", [70, 15, 80, 25], people) == 1
    assert PpeVisionFacade._best_person_for_ppe("hat", [45, 15, 55, 25], people) is None


def test_ppe_facade_exposes_only_canonical_person_hat_and_vest():
    class FakeBox:
        def __init__(self, class_id: int) -> None:
            self.cls = np.array([class_id])
            self.conf = np.array([0.8])
            # Hat/vest center at (15, 15); person 0..100 x 0..100
            # Hat: cy=15 <= 0+40%*100=40 ✓  Vest: cy=15 <= 0+85%*100=85 ✓
            self.xyxy = np.array([[10, 10, 20, 20]])

    class FakeModel:
        names = {0: "hat", 1: "nohat", 2: "novest", 3: "person", 4: "vest"}

        def __init__(self):
            self.calls = 0

        def predict(self, frame, classes, conf, imgsz, verbose):
            assert conf == 0.2
            assert imgsz == 960
            self.calls += 1
            assert classes == [0, 3, 4]
            result = type("Result", (), {})()
            result.names = self.names
            result.boxes = [FakeBox(class_id) for class_id in range(5)]
            return [result]

    facade = PpeVisionFacade("unused.pt")
    model = FakeModel()
    facade._model = model

    # Person (x=0, y=0, w=100, h=100) — large enough for hat at y=15 (top 40%=40) and vest at y=15 (top 85%=85)
    result = facade.observe(np.zeros((100, 100, 3), dtype=np.uint8), [(0, 0, 100, 100, 0.9)])

    assert [(item["class_id"], item["class_name"]) for item in result["detections"]] == [
        (3, "person"),
        (0, "hat"),
        (4, "vest"),
    ]
    assert all(item["person_index"] == 0 for item in result["detections"])
    assert result["people"][0]["hat"] == {"status": "present", "confidence": 0.8}
    assert result["people"][0]["vest"] == {"status": "present", "confidence": 0.8}
    assert model.calls == 1


def test_stateless_safety_analysis_uses_model_person_as_canonical_in_one_call():
    class FakeBox:
        def __init__(self, class_id: int, bbox: list[int], confidence: float) -> None:
            self.cls = np.array([class_id])
            self.conf = np.array([confidence])
            self.xyxy = np.array([bbox])
            self.id = None

    class FakeModel:
        names = {0: "hat", 1: "nohat", 2: "novest", 3: "person", 4: "vest"}

        def __init__(self):
            self.calls = []

        def predict(self, frame, **kwargs):
            self.calls.append(kwargs)
            result = type("Result", (), {})()
            result.names = self.names
            result.boxes = [
                FakeBox(3, [10, 10, 40, 90], 0.92),
                FakeBox(4, [15, 35, 35, 75], 0.84),
            ]
            return [result]

    facade = PpeVisionFacade("unused.pt")
    model = FakeModel()
    facade._model = model

    result = facade.analyze(np.zeros((100, 100, 3), dtype=np.uint8), None, now=0.0)

    assert result["canonical_people"] == [(10, 10, 30, 80, 0.92, 1)]
    assert result["people"][0]["vest"] == {"status": "present", "confidence": 0.84}
    assert [item["class_name"] for item in result["detections"]] == ["person", "vest"]
    assert model.calls == [{"classes": [0, 3, 4], "conf": 0.2, "imgsz": 960, "verbose": False}]


def test_person_confidence_is_configurable_independently_from_ppe_confidence():
    class FakeBox:
        def __init__(self, class_id: int, bbox: list[int], confidence: float) -> None:
            self.cls = np.array([class_id])
            self.conf = np.array([confidence])
            self.xyxy = np.array([bbox])
            self.id = None

    class FakeModel:
        names = {0: "hat", 1: "nohat", 2: "novest", 3: "person", 4: "vest"}

        def __init__(self):
            self.calls = []

        def predict(self, frame, **kwargs):
            self.calls.append(kwargs)
            result = type("Result", (), {})()
            result.names = self.names
            result.boxes = [
                FakeBox(3, [10, 10, 40, 90], 0.30),
                FakeBox(4, [15, 35, 35, 75], 0.30),
            ]
            return [result]

    facade = PpeVisionFacade(
        "unused.pt",
        confidence_threshold=0.35,
        person_confidence_threshold=0.25,
    )
    model = FakeModel()
    facade._model = model

    result = facade.analyze(np.zeros((100, 100, 3), dtype=np.uint8), None, now=0.0)

    assert result["canonical_people"] == [(10, 10, 30, 80, 0.30, 1)]
    assert [item["class_name"] for item in result["detections"]] == ["person"]
    assert result["people"][0]["vest"] == {"status": "unknown", "confidence": None}
    assert model.calls == [{"classes": [0, 3, 4], "conf": 0.25, "imgsz": 960, "verbose": False}]


def test_ppe_facade_rejects_invalid_confidence_thresholds():
    with np.testing.assert_raises_regex(ValueError, "confidence_threshold"):
        PpeVisionFacade("unused.pt", confidence_threshold=0.0)
    with np.testing.assert_raises_regex(ValueError, "person_confidence_threshold"):
        PpeVisionFacade("unused.pt", person_confidence_threshold=1.1)
    with np.testing.assert_raises_regex(ValueError, "inference_image_size"):
        PpeVisionFacade("unused.pt", inference_image_size=641)
    with np.testing.assert_raises_regex(ValueError, "temporal_frames"):
        PpeVisionFacade("unused.pt", temporal_frames=0)


def test_ppe_facade_drops_unassociated_hat_when_no_person_is_detected():
    class FakeBox:
        cls = np.array([0])
        conf = np.array([0.79])
        xyxy = np.array([[10, 10, 20, 20]])

    class FakeModel:
        names = {0: "hat", 1: "nohat", 2: "novest", 3: "person", 4: "vest"}

        def predict(self, frame, classes, conf, imgsz, verbose):
            assert imgsz == 960
            result = type("Result", (), {})()
            result.names = self.names
            result.boxes = [FakeBox()]
            return [result]

    facade = PpeVisionFacade("unused.pt")
    facade._model = FakeModel()

    result = facade.observe(np.zeros((40, 40, 3), dtype=np.uint8), [])

    assert result == {"people": [], "detections": []}


def test_ppe_model_person_supports_association_without_replacing_canonical_person():
    class FakeBox:
        def __init__(self, class_id: int, bbox: list[int]) -> None:
            self.cls = np.array([class_id])
            self.conf = np.array([0.8])
            self.xyxy = np.array([bbox])

    class FakeModel:
        names = {0: "hat", 1: "nohat", 2: "novest", 3: "person", 4: "vest"}

        def predict(self, frame, classes, conf, imgsz, verbose):
            assert imgsz == 960
            result = type("Result", (), {})()
            result.names = self.names
            result.boxes = [
                # Model-person overlaps canonical person (10,10,40,90)
                FakeBox(3, [8, 5, 50, 95]),
                # Hat center (22, 15): person x=10..40 ✓, cy=15 <= 10+0.40*80=42 ✓
                FakeBox(0, [15, 10, 30, 20]),
            ]
            return [result]

    facade = PpeVisionFacade("unused.pt")
    facade._model = FakeModel()

    # Canonical person: x=10, y=10, w=30, h=80 → x1=10..40, y1=10..90
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
            "bbox": [15, 10, 30, 20],
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


# ---------------------------------------------------------------------------
# US-29: Geometric validation tests
# ---------------------------------------------------------------------------


def test_hat_in_top_40_percent_is_valid():
    """Hat whose center is within the top 40% of person bbox passes geometry."""
    # Person bbox: x1=0, y1=0, x2=100, y2=100 → top 40% ends at y=40
    assert PpeVisionFacade._is_valid_hat_geometry([0, 0, 100, 100], 50.0, 30.0) is True
    assert PpeVisionFacade._is_valid_hat_geometry([0, 0, 100, 100], 50.0, 40.0) is True


def test_hat_below_40_percent_is_rejected():
    """Hat center below 40% threshold is discarded (e.g. at knee/waist level)."""
    # center_y=60 > 0 + 0.40*100 = 40
    assert PpeVisionFacade._is_valid_hat_geometry([0, 0, 100, 100], 50.0, 60.0) is False


def test_hat_outside_person_bbox_is_rejected():
    """Hat completely outside person bbox horizontally is discarded."""
    # Person from x=10 to x=50; hat center at x=80
    assert PpeVisionFacade._is_valid_hat_geometry([10, 0, 50, 100], 80.0, 10.0) is False


def test_hat_above_person_bbox_is_rejected():
    """Hat center above the person's top edge must fail closed."""
    assert PpeVisionFacade._is_valid_hat_geometry([10, 10, 50, 100], 30.0, 5.0) is False


def test_vest_inside_person_torso_is_valid():
    """Vest center inside person bbox and within top 85% passes geometry."""
    # center_y=50 <= 0 + 0.85*100 = 85
    assert PpeVisionFacade._is_valid_vest_geometry([0, 0, 100, 100], 50.0, 50.0) is True
    assert PpeVisionFacade._is_valid_vest_geometry([0, 0, 100, 100], 50.0, 85.0) is True


def test_vest_below_85_percent_is_rejected():
    """Vest center in the bottom 15% (leg area) is discarded."""
    # center_y=90 > 0 + 0.85*100 = 85
    assert PpeVisionFacade._is_valid_vest_geometry([0, 0, 100, 100], 50.0, 90.0) is False


def test_vest_outside_person_bbox_is_rejected():
    """Vest center outside person bbox is discarded."""
    assert PpeVisionFacade._is_valid_vest_geometry([10, 0, 50, 100], 80.0, 50.0) is False


def test_vest_above_person_bbox_is_rejected():
    """Vest center above the person's top edge must fail closed."""
    assert PpeVisionFacade._is_valid_vest_geometry([10, 10, 50, 100], 30.0, 5.0) is False


def test_invalid_person_bbox_rejects_ppe_geometry():
    assert PpeVisionFacade._is_valid_hat_geometry([10, 10, 10, 100], 10.0, 10.0) is False
    assert PpeVisionFacade._is_valid_vest_geometry([10, 100, 50, 10], 30.0, 50.0) is False


def test_overlapping_people_use_best_anatomical_region_instead_of_list_order():
    large_person = (0, 0, 100, 200, 0.95)
    small_person = (25, 0, 50, 100, 0.90)
    hat_bbox = [35, 10, 65, 30]

    assert PpeVisionFacade._best_person_for_ppe("hat", hat_bbox, [large_person, small_person]) == 1
    assert PpeVisionFacade._best_person_for_ppe("hat", hat_bbox, [small_person, large_person]) == 0


def test_cardinality_keeps_highest_confidence_hat():
    """When two hat detections overlap the same person, only the one with higher confidence is kept."""

    class FakeBox:
        def __init__(self, class_id: int, bbox: list[int], conf: float) -> None:
            self.cls = np.array([class_id])
            self.conf = np.array([conf])
            self.xyxy = np.array([bbox])
            self.id = None

    class FakeModel:
        names = {0: "hat", 1: "nohat", 2: "novest", 3: "person", 4: "vest"}

        def predict(self, frame, **kwargs):
            result = type("Result", (), {})()
            result.names = self.names
            result.boxes = [
                # Person: x1=0, y1=0, x2=100, y2=200
                FakeBox(3, [0, 0, 100, 200], 0.95),
                # Hat 1 at top of person — center (50, 30), conf 0.60
                FakeBox(0, [30, 20, 70, 40], 0.60),
                # Hat 2 also at top of person — center (50, 60), conf 0.85
                FakeBox(0, [30, 50, 70, 70], 0.85),
            ]
            return [result]

    facade = PpeVisionFacade("unused.pt")
    facade._model = FakeModel()

    result = facade.analyze(np.zeros((200, 100, 3), dtype=np.uint8), None, now=0.0)

    hat_obs = result["people"][0]["hat"]
    assert hat_obs["status"] == "present"
    assert hat_obs["confidence"] == 0.85, "Should keep the hat with the highest confidence"
    associated_hats = [
        detection
        for detection in result["detections"]
        if detection["class_name"] == "hat" and detection["person_index"] == 0
    ]
    assert len(associated_hats) == 1
    assert associated_hats[0]["confidence"] == 0.85


def test_cardinality_keeps_highest_confidence_vest():
    class FakeBox:
        def __init__(self, class_id: int, bbox: list[int], conf: float) -> None:
            self.cls = np.array([class_id])
            self.conf = np.array([conf])
            self.xyxy = np.array([bbox])
            self.id = None

    class FakeModel:
        names = {0: "hat", 1: "nohat", 2: "novest", 3: "person", 4: "vest"}

        def predict(self, frame, **kwargs):
            result = type("Result", (), {})()
            result.names = self.names
            result.boxes = [
                FakeBox(3, [0, 0, 100, 200], 0.95),
                FakeBox(4, [20, 50, 80, 130], 0.61),
                FakeBox(4, [25, 45, 75, 125], 0.87),
            ]
            return [result]

    facade = PpeVisionFacade("unused.pt")
    facade._model = FakeModel()

    result = facade.analyze(np.zeros((200, 100, 3), dtype=np.uint8), None, now=0.0)

    associated_vests = [
        detection
        for detection in result["detections"]
        if detection["class_name"] == "vest" and detection["person_index"] == 0
    ]
    assert result["people"][0]["vest"] == {"status": "present", "confidence": 0.87}
    assert len(associated_vests) == 1
    assert associated_vests[0]["confidence"] == 0.87


def test_hat_outside_person_bbox_is_dropped_from_public_detections():
    """Hat outside every person bbox must not reach the UI payload."""

    class FakeBox:
        def __init__(self, class_id: int, bbox: list[int]) -> None:
            self.cls = np.array([class_id])
            self.conf = np.array([0.8])
            self.xyxy = np.array([bbox])
            self.id = None

    class FakeModel:
        names = {0: "hat", 1: "nohat", 2: "novest", 3: "person", 4: "vest"}

        def predict(self, frame, **kwargs):
            result = type("Result", (), {})()
            result.names = self.names
            result.boxes = [
                # Person: x1=0, y1=0, x2=50, y2=100
                FakeBox(3, [0, 0, 50, 100]),
                # Hat center at (80, 10) — outside person horizontally
                FakeBox(0, [70, 5, 90, 15]),
            ]
            return [result]

    facade = PpeVisionFacade("unused.pt")
    facade._model = FakeModel()

    result = facade.analyze(np.zeros((100, 100, 3), dtype=np.uint8), None, now=0.0)

    assert result["people"][0]["hat"]["status"] == "unknown", "Hat outside bbox must not be assigned"
    hat_detections = [d for d in result["detections"] if d["class_name"] == "hat"]
    assert hat_detections == []


def test_geometry_invalid_hat_and_vest_are_dropped_from_public_detections():
    class FakeBox:
        def __init__(self, class_id: int, bbox: list[int]) -> None:
            self.cls = np.array([class_id])
            self.conf = np.array([0.8])
            self.xyxy = np.array([bbox])
            self.id = None

    class FakeModel:
        names = {0: "hat", 1: "nohat", 2: "novest", 3: "person", 4: "vest"}

        def predict(self, frame, **kwargs):
            result = type("Result", (), {})()
            result.names = self.names
            result.boxes = [
                FakeBox(3, [0, 0, 100, 100]),
                FakeBox(0, [40, 55, 60, 75]),  # Hat center is below the top 40%.
                FakeBox(4, [110, 20, 140, 70]),  # Vest is outside the person.
            ]
            return [result]

    facade = PpeVisionFacade("unused.pt")
    facade._model = FakeModel()

    result = facade.analyze(np.zeros((100, 150, 3), dtype=np.uint8), None, now=0.0)

    assert [detection["class_name"] for detection in result["detections"]] == ["person"]
    assert result["people"][0] == {
        "hat": {"status": "unknown", "confidence": None},
        "vest": {"status": "unknown", "confidence": None},
    }
