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
