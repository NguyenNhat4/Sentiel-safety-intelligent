import base64

import cv2
import numpy as np

from backend.app.schemas.analysis import FrameInferenceRequest, PpeObservation
from backend.app.schemas.ppe_requirement import PpeRequirementResponse
from backend.app.services.frame_inference_service import FrameInferenceService


def jpeg_data_url() -> str:
    encoded, buffer = cv2.imencode(".jpg", np.zeros((120, 160, 3), dtype=np.uint8))
    assert encoded
    return f"data:image/jpeg;base64,{base64.b64encode(buffer.tobytes()).decode()}"


def request() -> FrameInferenceRequest:
    return FrameInferenceRequest(
        image_data=jpeg_data_url(),
        zone_points=[
            {"x": 0.1, "y": 0.1},
            {"x": 0.9, "y": 0.1},
            {"x": 0.9, "y": 0.9},
            {"x": 0.1, "y": 0.9},
        ],
        machine_state="stopped",
    )


def test_required_explicitly_missing_ppe_requests_review():
    service = FrameInferenceService(
        person_model_path="unused.pt",
        ppe_observer=lambda frame, people: [
            {
                "helmet": PpeObservation(status="missing", confidence=0.91),
                "safety_glasses": PpeObservation(status="unknown", confidence=None),
                "gloves": PpeObservation(status="present", confidence=0.88),
            }
        ],
        requirement_loader=lambda camera_id, zone_id: PpeRequirementResponse(
            camera_id=camera_id,
            zone_id=zone_id,
            helmet_required=True,
            safety_glasses_required=False,
            gloves_required=False,
            updated_at=None,
        ),
    )
    service._detect_people = lambda frame: [(40, 10, 40, 80, 0.95)]

    result = service.infer(request())

    assert result.people[0].ppe.helmet.status == "missing"
    assert result.people[0].missing_required_ppe == ["helmet"]
    assert result.rule["ppe_requirements"]["helmet_required"] is True
    assert result.review_required is True
    assert result.result == "violate"


def test_off_requirement_suppresses_missing_ppe_alert_without_removing_observation():
    service = FrameInferenceService(
        person_model_path="unused.pt",
        ppe_observer=lambda frame, people: [
            {
                "helmet": PpeObservation(status="missing", confidence=0.91),
                "safety_glasses": PpeObservation(status="unknown", confidence=None),
                "gloves": PpeObservation(status="unknown", confidence=None),
            }
        ],
        requirement_loader=lambda camera_id, zone_id: PpeRequirementResponse(
            camera_id=camera_id,
            zone_id=zone_id,
            helmet_required=False,
            safety_glasses_required=False,
            gloves_required=False,
            updated_at=None,
        ),
    )
    service._detect_people = lambda frame: [(40, 10, 40, 80, 0.95)]

    result = service.infer(request())

    assert result.people[0].ppe.helmet.status == "missing"
    assert result.people[0].missing_required_ppe == []
    assert result.review_required is False
    assert result.result == "normal"


def test_qualified_absence_of_required_helmet_creates_alert_and_exposes_all_detections():
    service = FrameInferenceService(
        person_model_path="unused.pt",
        ppe_observer=lambda frame, people: {
            "people": [
                {
                    "helmet": PpeObservation(status="unknown", confidence=None),
                    "safety_glasses": PpeObservation(status="unknown", confidence=None),
                    "gloves": PpeObservation(status="unknown", confidence=None),
                }
            ],
            "detections": [
                {
                    "class_id": 7,
                    "class_name": "tool",
                    "bbox": [90, 20, 120, 70],
                    "confidence": 0.79,
                    "person_index": None,
                }
            ],
        },
        requirement_loader=lambda camera_id, zone_id: PpeRequirementResponse(
            camera_id=camera_id,
            zone_id=zone_id,
            helmet_required=True,
            safety_glasses_required=False,
            gloves_required=False,
            updated_at=None,
        ),
    )
    service._detect_people = lambda frame: [(40, 10, 40, 80, 0.95)]

    result = service.infer(request())

    assert result.people[0].ppe.helmet.status == "missing"
    assert result.people[0].ppe.helmet.confidence is None
    assert result.people[0].missing_required_ppe == ["helmet"]
    assert result.detections[0].class_id == 7
    assert result.detections[0].class_name == "tool"
    assert result.detections[0].person_index is None
    assert result.review_required is True


def test_low_confidence_person_without_helmet_remains_unknown():
    service = FrameInferenceService(
        person_model_path="unused.pt",
        ppe_observer=lambda frame, people: {
            "people": [
                {
                    "helmet": PpeObservation(status="unknown", confidence=None),
                    "safety_glasses": PpeObservation(status="unknown", confidence=None),
                    "gloves": PpeObservation(status="unknown", confidence=None),
                }
            ],
            "detections": [],
        },
        requirement_loader=lambda camera_id, zone_id: PpeRequirementResponse(
            camera_id=camera_id,
            zone_id=zone_id,
            helmet_required=True,
            safety_glasses_required=False,
            gloves_required=False,
            updated_at=None,
        ),
    )
    service._detect_people = lambda frame: [(40, 10, 40, 80, 0.2)]

    result = service.infer(request())

    assert result.people[0].ppe.helmet.status == "unknown"
    assert result.people[0].missing_required_ppe == []
    assert result.review_required is False


def test_frame_without_zone_still_returns_person_and_detection_boxes():
    service = FrameInferenceService(
        person_model_path="unused.pt",
        ppe_observer=lambda frame, people: {
            "people": [
                {
                    "helmet": PpeObservation(status="present", confidence=0.9),
                    "safety_glasses": PpeObservation(status="unknown", confidence=None),
                    "gloves": PpeObservation(status="unknown", confidence=None),
                }
            ],
            "detections": [
                {
                    "class_id": 10,
                    "class_name": "helmet",
                    "bbox": [45, 15, 65, 35],
                    "confidence": 0.9,
                    "person_index": 0,
                }
            ],
        },
    )
    service._detect_people = lambda frame: [(40, 10, 40, 80, 0.95)]
    no_zone = request().model_copy(update={"zone_points": []})

    result = service.infer(no_zone)

    assert result.people[0].inside_zone is False
    assert result.people[0].bbox == [40, 10, 80, 90]
    assert result.detections[0].class_name == "helmet"


def test_fewer_observations_than_people_safely_handled():
    service = FrameInferenceService(
        person_model_path="unused.pt",
        ppe_observer=lambda frame, people: [],  # returns 0 observations for 2 detected people
        requirement_loader=lambda camera_id, zone_id: PpeRequirementResponse(
            camera_id=camera_id,
            zone_id=zone_id,
            helmet_required=False,
            safety_glasses_required=False,
            gloves_required=False,
            updated_at=None,
        ),
    )
    service._detect_people = lambda frame: [(40, 10, 40, 80, 0.95), (100, 10, 40, 80, 0.9)]

    result = service.infer(request())

    assert len(result.people) == 2
    assert result.people[0].ppe.helmet.status == "missing"
    assert result.people[1].ppe.helmet.status == "missing"

