import pytest
from pydantic import TypeAdapter, ValidationError
from sqlalchemy.exc import SQLAlchemyError

from backend.app.api.v1.ppe_requirements import (
    ResourceId,
    get_ppe_requirement,
    save_ppe_requirement,
)
from backend.app.schemas.ppe_requirement import PpeRequirementUpdate
from backend.app.services.ppe_requirement_service import (
    PpeRequirementPersistenceError,
    PpeRequirementService,
    PpeStatus,
    should_alert_for_missing_ppe,
)


def test_missing_requirement_defaults_to_off_without_creating_a_record(db_session):
    service = PpeRequirementService(db_session)

    requirement = service.get("uploaded_video", "zone_01")

    assert requirement.camera_id == "uploaded_video"
    assert requirement.zone_id == "zone_01"
    assert requirement.profile == "hat_vest_v1"
    assert requirement.hat_required is False
    assert requirement.vest_required is False
    assert requirement.restricted_area_detection_enabled is False
    assert requirement.zone_intrusion_enabled is True
    assert requirement.is_configured is False
    assert requirement.updated_at is None
    assert requirement.helmet_required is False
    assert requirement.safety_glasses_required is False
    assert requirement.gloves_required is False
    assert service.count() == 0


def test_save_upserts_one_shared_requirement(db_session):
    service = PpeRequirementService(db_session)

    first = service.save(
        "uploaded_video",
        "zone_01",
        PpeRequirementUpdate(
            profile="hat_vest_v1",
            hat_required=True,
            vest_required=True,
        ),
    )
    second = service.save(
        "uploaded_video",
        "zone_01",
        PpeRequirementUpdate(
            profile="hat_vest_v1",
            hat_required=False,
            vest_required=False,
        ),
    )

    assert first.is_configured is True
    assert second.hat_required is False
    assert second.vest_required is False
    assert second.helmet_required is False
    assert second.safety_glasses_required is False
    assert second.gloves_required is False
    assert second.updated_at is not None
    assert service.count() == 1


def test_save_persists_restricted_area_detection_per_zone(db_session):
    service = PpeRequirementService(db_session)

    saved = service.save(
        "uploaded_video",
        "zone_02",
        PpeRequirementUpdate(
            profile="hat_vest_v1",
            hat_required=False,
            vest_required=False,
            restricted_area_detection_enabled=True,
        ),
    )

    assert saved.restricted_area_detection_enabled is True
    assert service.get("uploaded_video", "zone_01").restricted_area_detection_enabled is False


def test_save_persists_zone_intrusion_switch_per_camera_zone(db_session):
    service = PpeRequirementService(db_session)

    saved = service.save(
        "cam_1",
        "zone_press",
        PpeRequirementUpdate(
            profile="hat_vest_v1",
            hat_required=True,
            vest_required=False,
            zone_intrusion_enabled=False,
        ),
    )

    assert saved.zone_intrusion_enabled is False
    assert service.get("cam_1", "zone_press").zone_intrusion_enabled is False
    assert service.get("cam_2", "zone_press").zone_intrusion_enabled is True


def test_failed_save_preserves_previous_requirement(db_session, monkeypatch):
    service = PpeRequirementService(db_session)
    service.save(
        "uploaded_video",
        "zone_01",
        PpeRequirementUpdate(
            profile="hat_vest_v1",
            hat_required=True,
            vest_required=False,
        ),
    )
    original_commit = db_session.commit

    def fail_commit():
        raise SQLAlchemyError("database details must not escape")

    monkeypatch.setattr(db_session, "commit", fail_commit)
    with pytest.raises(PpeRequirementPersistenceError, match="Could not save PPE requirements"):
        service.save(
            "uploaded_video",
            "zone_01",
            PpeRequirementUpdate(
                profile="hat_vest_v1",
                hat_required=False,
                vest_required=True,
            ),
        )

    monkeypatch.setattr(db_session, "commit", original_commit)
    db_session.expire_all()
    saved = service.get("uploaded_video", "zone_01")
    assert saved.hat_required is True
    assert saved.vest_required is False


@pytest.mark.asyncio
async def test_get_api_returns_default_off(db_session):
    response = await get_ppe_requirement("uploaded_video", "zone_01", db_session)

    assert response.model_dump(mode="json") == {
        "camera_id": "uploaded_video",
        "zone_id": "zone_01",
        "profile": "hat_vest_v1",
        "hat_required": False,
        "vest_required": False,
        "restricted_area_detection_enabled": False,
        "zone_intrusion_enabled": True,
        "is_configured": False,
        "updated_at": None,
        "helmet_required": False,
        "safety_glasses_required": False,
        "gloves_required": False,
    }


@pytest.mark.asyncio
async def test_put_api_saves_and_returns_shared_requirement(db_session):
    saved = await save_ppe_requirement(
        PpeRequirementUpdate(
            profile="hat_vest_v1",
            hat_required=True,
            vest_required=True,
        ),
        "uploaded_video",
        "zone_01",
        db_session,
    )
    loaded = await get_ppe_requirement("uploaded_video", "zone_01", db_session)

    assert saved.is_configured is True
    assert loaded.hat_required is True
    assert loaded.vest_required is True


@pytest.mark.parametrize(
    "validator,payload",
    [
        (
            TypeAdapter(PpeRequirementUpdate),
            {"profile": "hat_vest_v1", "hat_required": True},
        ),
        (
            TypeAdapter(PpeRequirementUpdate),
            {
                "profile": "hat_vest_v1",
                "hat_required": "yes",
                "vest_required": False,
            },
        ),
        (
            TypeAdapter(PpeRequirementUpdate),
            {"profile": "legacy", "hat_required": False, "vest_required": False},
        ),
        (
            TypeAdapter(ResourceId),
            "c" * 51,
        ),
    ],
)
def test_put_api_rejects_invalid_input(validator, payload):
    with pytest.raises(ValidationError):
        validator.validate_python(payload)


def test_legacy_put_payload_maps_helmet_to_hat_and_requires_vest():
    update = TypeAdapter(PpeRequirementUpdate).validate_python(
        {
            "helmet_required": True,
            "safety_glasses_required": True,
            "gloves_required": False,
        }
    )

    assert update.model_dump() == {
        "profile": "hat_vest_v1",
        "hat_required": True,
        "vest_required": True,
        "restricted_area_detection_enabled": False,
        "zone_intrusion_enabled": True,
    }


def test_put_api_rejects_mixed_legacy_and_current_payloads():
    with pytest.raises(ValidationError):
        TypeAdapter(PpeRequirementUpdate).validate_python(
            {
                "profile": "hat_vest_v1",
                "hat_required": True,
                "vest_required": False,
                "helmet_required": True,
                "safety_glasses_required": False,
                "gloves_required": False,
            }
        )


@pytest.mark.parametrize(
    "required,status,person_confidence,association_is_valid,expected",
    [
        (False, PpeStatus.MISSING, 0.99, True, False),
        (True, PpeStatus.PRESENT, 0.99, True, False),
        (True, PpeStatus.UNKNOWN, 0.99, True, False),
        (True, PpeStatus.MISSING, 0.49, True, False),
        (True, PpeStatus.MISSING, 0.5, False, False),
        (True, PpeStatus.MISSING, 0.5, True, True),
        (True, PpeStatus.MISSING, 0.99, True, True),
    ],
)
def test_missing_ppe_alert_truth_table(required, status, person_confidence, association_is_valid, expected):
    assert (
        should_alert_for_missing_ppe(
            required=required,
            status=status,
            person_confidence=person_confidence,
            threshold=0.5,
            association_is_valid=association_is_valid,
        )
        is expected
    )
