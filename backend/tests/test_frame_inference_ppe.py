import base64
from uuid import uuid4

import cv2
import numpy as np

from backend.app.core.config import Settings
from backend.app.schemas.analysis import FrameInferenceRequest, PpeObservation
from backend.app.schemas.monitoring_zone import MonitoringZone
from backend.app.schemas.ppe_requirement import PpeRequirementResponse
from backend.app.services.frame_inference_service import FrameInferenceService


def jpeg_data_url() -> str:
    encoded, buffer = cv2.imencode(".jpg", np.zeros((120, 160, 3), dtype=np.uint8))
    assert encoded
    return f"data:image/jpeg;base64,{base64.b64encode(buffer.tobytes()).decode()}"


def request(*, with_zone: bool = True, machine_state: str = "running") -> FrameInferenceRequest:
    return FrameInferenceRequest(
        image_data=jpeg_data_url(),
        zone_points=[
            {"x": 0.1, "y": 0.1},
            {"x": 0.9, "y": 0.1},
            {"x": 0.9, "y": 0.9},
            {"x": 0.1, "y": 0.9},
        ]
        if with_zone
        else [],
        machine_state=machine_state,
    )


def test_default_inference_uses_only_the_safety_model(monkeypatch):
    monkeypatch.setattr(
        "backend.app.core.config.get_settings",
        lambda: Settings(ppe_model_path="models/yolo11m_safety.pt"),
    )

    service = FrameInferenceService()

    assert service._model_path == "models/yolo11m_safety.pt"


def test_person_detection_confidence_is_forwarded_to_main_and_fallback_detectors(monkeypatch):
    adapter_calls = []

    class FakeAdapter:
        @staticmethod
        def analyze(frame, monitoring_session_id, now):
            return {"canonical_people": [], "people": [], "detections": []}

        @staticmethod
        def observe(frame, people):
            return {"people": [], "detections": []}

        @staticmethod
        def preload():
            return None

    def fake_adapter(
        model_path,
        person_confidence_threshold,
        ppe_confidence_threshold,
        inference_image_size,
        temporal_frames,
    ):
        adapter_calls.append(
            (
                model_path,
                person_confidence_threshold,
                ppe_confidence_threshold,
                inference_image_size,
                temporal_frames,
            )
        )
        return FakeAdapter()

    monkeypatch.setattr(
        "backend.app.core.config.get_settings",
        lambda: Settings(
            _env_file=None,
            ppe_model_path="models/yolo11m_safety.pt",
            person_detection_confidence=0.42,
            ppe_detection_confidence=0.23,
            yolo_inference_image_size=960,
            ppe_temporal_frames=10,
        ),
    )
    monkeypatch.setattr(
        "backend.app.services.frame_inference_service.get_ppe_vision_adapter",
        fake_adapter,
    )

    class FakeModel:
        def __init__(self):
            self.calls = []

        def predict(self, frame, **kwargs):
            self.calls.append(kwargs)
            result = type("Result", (), {"boxes": []})()
            return [result]

    service = FrameInferenceService()
    model = FakeModel()
    service._fallback_model = model

    assert service._detect_people(np.zeros((10, 10, 3), dtype=np.uint8)) == []
    assert adapter_calls == [("models/yolo11m_safety.pt", 0.42, 0.23, 960, 10)]
    assert model.calls == [{"classes": [3], "conf": 0.42, "imgsz": 960, "verbose": False}]


def test_remote_provider_routes_inference_through_http_adapter(monkeypatch):
    class FakeRemoteAdapter:
        def analyze(self, frame, monitoring_session_id, now):
            return {"canonical_people": [], "people": [], "detections": []}

        def preload(self):
            return None

    remote_adapter = FakeRemoteAdapter()
    monkeypatch.setattr(
        "backend.app.core.config.get_settings",
        lambda: Settings(
            vision_provider="remote",
            vision_remote_url="https://vision.example",
            vision_remote_api_key="secret-token",
        ),
    )
    monkeypatch.setattr(
        "backend.app.services.frame_inference_service.get_remote_vision_adapter",
        lambda **kwargs: remote_adapter,
    )

    service = FrameInferenceService()

    assert service._vision_analyzer == remote_adapter.analyze
    assert service._model_preloader == remote_adapter.preload


def test_unified_analyzer_supplies_canonical_people_and_ppe_with_one_call():
    calls = 0

    def analyze(frame, monitoring_session_id, now):
        nonlocal calls
        calls += 1
        assert monitoring_session_id is None
        return {
            "canonical_people": [(40, 10, 40, 80, 0.95, 1)],
            "people": [
                {
                    "hat": {"status": "present", "confidence": 0.91},
                    "vest": {"status": "present", "confidence": 0.88},
                }
            ],
            "detections": [
                {
                    "class_id": 3,
                    "class_name": "person",
                    "bbox": [40, 10, 80, 90],
                    "confidence": 0.95,
                    "person_index": 0,
                },
                {
                    "class_id": 0,
                    "class_name": "hat",
                    "bbox": [45, 15, 65, 35],
                    "confidence": 0.91,
                    "person_index": 0,
                },
            ],
        }

    service = FrameInferenceService(
        vision_analyzer=analyze,
        requirement_loader=lambda camera_id, zone_id: PpeRequirementResponse(
            camera_id=camera_id,
            zone_id=zone_id,
            profile="hat_vest_v1",
            hat_required=False,
            vest_required=False,
            updated_at=None,
        ),
    )

    result = service.infer(request())

    assert calls == 1
    assert result.people[0].bbox == [40, 10, 80, 90]
    assert result.people[0].ppe.hat.status == "present"
    assert [item.class_name for item in result.detections] == ["person", "hat"]


def test_decoded_camera_frame_skips_jpeg_round_trip(monkeypatch):
    received_shapes = []

    def analyze(frame, monitoring_session_id, now):
        received_shapes.append(frame.shape)
        return {"canonical_people": [], "people": [], "detections": []}

    monkeypatch.setattr(
        "backend.app.core.config.get_settings",
        lambda: Settings(inference_frame_width=640, inference_frame_height=360),
    )
    service = FrameInferenceService(
        vision_analyzer=analyze,
        requirement_loader=lambda camera_id, zone_id: PpeRequirementResponse(
            camera_id=camera_id,
            zone_id=zone_id,
            profile="hat_vest_v1",
            hat_required=False,
            vest_required=False,
            updated_at=None,
        ),
    )
    monkeypatch.setattr(
        service,
        "_decode_frame",
        lambda _: (_ for _ in ()).throw(AssertionError("decoded camera frames must not be decoded again")),
    )
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    camera_request = FrameInferenceRequest(image_data="", machine_state="stopped")

    result = service.infer_decoded_frame(camera_request, frame)

    assert result.result == "normal"
    assert received_shapes == [(360, 640, 3)]


def test_inference_resize_preserves_original_frame_coordinates(monkeypatch):
    def analyze(frame, monitoring_session_id, now):
        return {
            "canonical_people": [(100, 50, 200, 250, 0.9, 1)],
            "people": [
                {
                    "hat": {"status": "present", "confidence": 0.9},
                    "vest": {"status": "present", "confidence": 0.9},
                }
            ],
            "detections": [
                {
                    "class_id": 3,
                    "class_name": "person",
                    "bbox": [100, 50, 300, 300],
                    "confidence": 0.9,
                    "person_index": 0,
                }
            ],
        }

    monkeypatch.setattr(
        "backend.app.core.config.get_settings",
        lambda: Settings(inference_frame_width=640, inference_frame_height=360),
    )
    service = FrameInferenceService(
        vision_analyzer=analyze,
        requirement_loader=lambda camera_id, zone_id: PpeRequirementResponse(
            camera_id=camera_id,
            zone_id=zone_id,
            profile="hat_vest_v1",
            hat_required=False,
            vest_required=False,
            updated_at=None,
        ),
    )

    result = service.infer_decoded_frame(
        FrameInferenceRequest(image_data="", machine_state="stopped"),
        np.zeros((720, 1280, 3), dtype=np.uint8),
    )

    assert result.people[0].bbox == [200, 100, 600, 600]
    assert result.people[0].foot_point == [400, 600]
    assert result.detections[0].bbox == [200, 100, 600, 600]


def test_preload_models_warms_the_unified_safety_model(monkeypatch):
    service = FrameInferenceService(model_path="unused.pt")
    loaded = []
    monkeypatch.setattr(service, "_model_preloader", lambda: loaded.append("unified"))

    service.preload_models()

    assert loaded == ["unified"]


def test_required_explicitly_missing_ppe_requests_review():
    service = FrameInferenceService(
        model_path="unused.pt",
        ppe_observer=lambda frame, people: [
            {
                "hat": PpeObservation(status="missing", confidence=0.91),
                "vest": PpeObservation(status="present", confidence=0.88),
            }
        ],
        requirement_loader=lambda camera_id, zone_id: PpeRequirementResponse(
            camera_id=camera_id,
            zone_id=zone_id,
            profile="hat_vest_v1",
            hat_required=True,
            vest_required=False,
            updated_at=None,
        ),
    )
    service._detect_people = lambda frame: [(40, 10, 40, 80, 0.95)]

    result = service.infer(request())

    assert result.people[0].ppe.hat.status == "missing"
    assert result.people[0].missing_required_ppe == ["hat"]
    assert result.rule["ppe_requirements"]["hat_required"] is True
    assert result.review_required is True
    assert result.result == "violate"


def test_off_requirement_suppresses_missing_ppe_alert_without_removing_observation():
    service = FrameInferenceService(
        model_path="unused.pt",
        ppe_observer=lambda frame, people: [
            {
                "hat": PpeObservation(status="missing", confidence=0.91),
                "vest": PpeObservation(status="unknown", confidence=None),
            }
        ],
        requirement_loader=lambda camera_id, zone_id: PpeRequirementResponse(
            camera_id=camera_id,
            zone_id=zone_id,
            profile="hat_vest_v1",
            hat_required=False,
            vest_required=False,
            updated_at=None,
        ),
    )
    service._detect_people = lambda frame: [(40, 10, 40, 80, 0.95)]

    result = service.infer(request(with_zone=False, machine_state="stopped"))

    assert result.people[0].ppe.hat.status == "missing"
    assert result.people[0].missing_required_ppe == []
    assert result.review_required is False
    assert result.result == "normal"


def test_restricted_area_detection_alerts_immediately_for_any_detected_person():
    service = FrameInferenceService(
        model_path="unused.pt",
        ppe_observer=lambda frame, people: [],
        requirement_loader=lambda camera_id, zone_id: PpeRequirementResponse(
            camera_id=camera_id,
            zone_id=zone_id,
            profile="hat_vest_v1",
            hat_required=False,
            vest_required=False,
            restricted_area_detection_enabled=True,
            updated_at=None,
        ),
    )
    service._detect_people = lambda frame: [(40, 10, 40, 80, 0.95)]

    result = service.infer(request())

    assert result.result == "violate"
    assert result.review_required is True
    assert result.rule["restricted_area_alert"] is True
    assert result.people[0].active_violations[0].rule_key == "restricted_area_person"


def test_qualified_absence_creates_alert_but_drops_unassociated_detection():
    service = FrameInferenceService(
        model_path="unused.pt",
        ppe_observer=lambda frame, people: {
            "people": [
                {
                    "hat": PpeObservation(status="unknown", confidence=None),
                    "vest": PpeObservation(status="unknown", confidence=None),
                }
            ],
            "detections": [
                {
                    "class_id": 4,
                    "class_name": "vest",
                    "bbox": [90, 20, 120, 70],
                    "confidence": 0.79,
                    "person_index": None,
                }
            ],
        },
        requirement_loader=lambda camera_id, zone_id: PpeRequirementResponse(
            camera_id=camera_id,
            zone_id=zone_id,
            profile="hat_vest_v1",
            hat_required=True,
            vest_required=False,
            updated_at=None,
        ),
    )
    service._detect_people = lambda frame: [(40, 10, 40, 80, 0.95)]

    result = service.infer(request())

    assert result.people[0].ppe.hat.status == "missing"
    assert result.people[0].ppe.hat.confidence is None
    assert result.people[0].missing_required_ppe == ["hat"]
    assert result.detections == []
    assert result.review_required is True


def test_low_confidence_person_without_hat_remains_unknown():
    service = FrameInferenceService(
        model_path="unused.pt",
        ppe_observer=lambda frame, people: {
            "people": [
                {
                    "hat": PpeObservation(status="unknown", confidence=None),
                    "vest": PpeObservation(status="unknown", confidence=None),
                }
            ],
            "detections": [],
        },
        requirement_loader=lambda camera_id, zone_id: PpeRequirementResponse(
            camera_id=camera_id,
            zone_id=zone_id,
            profile="hat_vest_v1",
            hat_required=True,
            vest_required=False,
            updated_at=None,
        ),
    )
    service._detect_people = lambda frame: [(40, 10, 40, 80, 0.2)]

    result = service.infer(request(with_zone=False, machine_state="stopped"))

    assert result.people[0].ppe.hat.status == "unknown"
    assert result.people[0].missing_required_ppe == []
    assert result.review_required is False


def test_frame_without_zone_still_returns_person_and_detection_boxes():
    service = FrameInferenceService(
        model_path="unused.pt",
        ppe_observer=lambda frame, people: {
            "people": [
                {
                    "hat": PpeObservation(status="present", confidence=0.9),
                    "vest": PpeObservation(status="unknown", confidence=None),
                }
            ],
            "detections": [
                {
                    "class_id": 0,
                    "class_name": "hat",
                    "bbox": [45, 15, 65, 35],
                    "confidence": 0.9,
                    "person_index": 0,
                }
            ],
        },
        requirement_loader=lambda camera_id, zone_id: PpeRequirementResponse(
            camera_id=camera_id,
            zone_id=zone_id,
            profile="hat_vest_v1",
            hat_required=False,
            vest_required=False,
            updated_at=None,
        ),
    )
    service._detect_people = lambda frame: [(40, 10, 40, 80, 0.95)]
    no_zone = request().model_copy(update={"zone_points": []})

    result = service.infer(no_zone)

    assert result.people[0].inside_zone is False
    assert result.people[0].bbox == [40, 10, 80, 90]
    assert result.detections[0].class_name == "hat"


def test_fewer_observations_than_people_safely_handled():
    service = FrameInferenceService(
        model_path="unused.pt",
        ppe_observer=lambda frame, people: [],  # returns 0 observations for 2 detected people
        requirement_loader=lambda camera_id, zone_id: PpeRequirementResponse(
            camera_id=camera_id,
            zone_id=zone_id,
            profile="hat_vest_v1",
            hat_required=False,
            vest_required=False,
            updated_at=None,
        ),
    )
    service._detect_people = lambda frame: [(40, 10, 40, 80, 0.95), (100, 10, 40, 80, 0.9)]

    result = service.infer(request())

    assert len(result.people) == 2
    assert result.people[0].ppe.hat.status == "missing"
    assert result.people[1].ppe.hat.status == "missing"


def test_temporally_confirmed_ppe_absence_opens_review_without_second_debounce():
    service = FrameInferenceService(
        vision_analyzer=lambda frame, monitoring_session_id, now: {
            "canonical_people": [(40, 10, 40, 80, 0.95, 7)],
            "people": [
                {
                    "hat": {"status": "unknown", "confidence": None},
                    "vest": {"status": "present", "confidence": 0.88},
                }
            ],
            "detections": [],
            "absence_confirmed": [{"hat": True, "vest": False}],
        },
        requirement_loader=lambda camera_id, zone_id: PpeRequirementResponse(
            camera_id=camera_id,
            zone_id=zone_id,
            profile="hat_vest_v1",
            hat_required=True,
            vest_required=False,
            updated_at=None,
        ),
    )
    tracked_request = request(with_zone=False).model_copy(update={"monitoring_session_id": uuid4(), "frame_id": 1})

    result = service.infer(tracked_request)

    assert result.people[0].ppe.hat.status == "missing"
    assert result.result == "violate"
    assert result.review_required is True
    assert result.people[0].active_violations[0].rule_key == "missing_ppe:hat"


def test_initial_ppe_absence_stays_unknown_until_third_consecutive_frame():
    confirmations = iter([False, False, True])

    def analyze(frame, monitoring_session_id, now):
        return {
            "canonical_people": [(40, 10, 40, 80, 0.95, 7)],
            "people": [
                {
                    "hat": {"status": "unknown", "confidence": None},
                    "vest": {"status": "present", "confidence": 0.88},
                }
            ],
            "detections": [],
            "absence_confirmed": [{"hat": next(confirmations), "vest": False}],
        }

    service = FrameInferenceService(
        vision_analyzer=analyze,
        requirement_loader=lambda camera_id, zone_id: PpeRequirementResponse(
            camera_id=camera_id,
            zone_id=zone_id,
            profile="hat_vest_v1",
            hat_required=True,
            vest_required=False,
            updated_at=None,
        ),
    )
    session_id = uuid4()

    results = [
        service.infer(
            request(with_zone=False).model_copy(update={"monitoring_session_id": session_id, "frame_id": frame_id})
        )
        for frame_id in range(1, 4)
    ]

    assert [result.people[0].ppe.hat.status for result in results] == ["unknown", "unknown", "missing"]
    assert [result.result for result in results] == ["normal", "normal", "violate"]
    assert [result.review_required for result in results] == [False, False, True]


def test_zone_intrusion_still_uses_the_global_four_frame_debounce():
    service = FrameInferenceService(
        vision_analyzer=lambda frame, monitoring_session_id, now: {
            "canonical_people": [(40, 10, 40, 80, 0.95, 7)],
            "people": [
                {
                    "hat": {"status": "present", "confidence": 0.91},
                    "vest": {"status": "present", "confidence": 0.88},
                }
            ],
            "detections": [],
        },
        requirement_loader=lambda camera_id, zone_id: PpeRequirementResponse(
            camera_id=camera_id,
            zone_id=zone_id,
            profile="hat_vest_v1",
            hat_required=False,
            vest_required=False,
            updated_at=None,
        ),
    )
    session_id = uuid4()
    results = [
        service.infer(request().model_copy(update={"monitoring_session_id": session_id, "frame_id": frame_id}))
        for frame_id in range(1, 5)
    ]

    assert [result.result for result in results] == ["violate"] * 4
    assert [result.review_required for result in results] == [False, False, False, True]
    assert results[-1].people[0].active_violations[0].rule_key == "zone_intrusion"


def test_requirements_by_zone_evaluates_ppe_when_machine_running():
    def analyze(frame, monitoring_session_id, now):
        return {
            "canonical_people": [(40, 10, 40, 80, 0.95, 1)],
            "people": [
                {
                    "hat": {"status": "missing", "confidence": None},
                    "vest": {"status": "present", "confidence": 0.9},
                }
            ],
            "detections": [],
        }

    service = FrameInferenceService(vision_analyzer=analyze)
    req = request(with_zone=False, machine_state="running")
    req.zones = [
        MonitoringZone(
            zone_id="zone_01",
            display_name="Zone 01",
            points=[
                {"x": 0.1, "y": 0.1},
                {"x": 0.9, "y": 0.1},
                {"x": 0.9, "y": 0.9},
                {"x": 0.1, "y": 0.9},
            ],
            enabled=True,
            order=0,
        )
    ]
    req.monitoring_session_id = None
    requirements_by_zone = {
        "zone_01": PpeRequirementResponse(
            camera_id="cam_1",
            zone_id="zone_01",
            profile="hat_vest_v1",
            hat_required=True,
            vest_required=False,
            updated_at=None,
        )
    }

    result = service.infer_decoded_frame(
        req,
        np.zeros((120, 160, 3), dtype=np.uint8),
        requirements_by_zone=requirements_by_zone,
    )

    assert result.result == "violate"
    assert result.people[0].missing_required_ppe == ["hat"]
    assert result.people[0].active_violations[0].rule_key == "missing_ppe:hat"
