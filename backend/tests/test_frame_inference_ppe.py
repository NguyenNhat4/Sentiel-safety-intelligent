import base64

import cv2
import numpy as np

from backend.app.core.config import Settings
from backend.app.schemas.analysis import FrameInferenceRequest, PpeObservation
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


def test_qualified_absence_of_required_hat_creates_alert_and_exposes_all_detections():
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
    assert result.detections[0].class_id == 4
    assert result.detections[0].class_name == "vest"
    assert result.detections[0].person_index is None
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
