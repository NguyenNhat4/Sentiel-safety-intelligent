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
    assert requirement.helmet_required is False
    assert requirement.safety_glasses_required is False
    assert requirement.gloves_required is False
    assert requirement.is_configured is False
    assert requirement.updated_at is None
    assert service.count() == 0


def test_save_upserts_one_shared_requirement(db_session):
    service = PpeRequirementService(db_session)

    first = service.save(
        "uploaded_video",
        "zone_01",
        PpeRequirementUpdate(
            helmet_required=True,
            safety_glasses_required=False,
            gloves_required=True,
        ),
    )
    second = service.save(
        "uploaded_video",
        "zone_01",
        PpeRequirementUpdate(
            helmet_required=False,
            safety_glasses_required=True,
            gloves_required=False,
        ),
    )

    assert first.is_configured is True
    assert second.helmet_required is False
    assert second.safety_glasses_required is True
    assert second.gloves_required is False
    assert second.updated_at is not None
    assert service.count() == 1


def test_failed_save_preserves_previous_requirement(db_session, monkeypatch):
    service = PpeRequirementService(db_session)
    service.save(
        "uploaded_video",
        "zone_01",
        PpeRequirementUpdate(
            helmet_required=True,
            safety_glasses_required=False,
            gloves_required=False,
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
                helmet_required=False,
                safety_glasses_required=True,
                gloves_required=True,
            ),
        )

    monkeypatch.setattr(db_session, "commit", original_commit)
    db_session.expire_all()
    saved = service.get("uploaded_video", "zone_01")
    assert saved.helmet_required is True
    assert saved.safety_glasses_required is False
    assert saved.gloves_required is False


@pytest.mark.asyncio
async def test_get_api_returns_default_off(db_session):
    response = await get_ppe_requirement("uploaded_video", "zone_01", db_session)

    assert response.model_dump(mode="json") == {
        "camera_id": "uploaded_video",
        "zone_id": "zone_01",
        "helmet_required": False,
        "safety_glasses_required": False,
        "gloves_required": False,
        "is_configured": False,
        "updated_at": None,
    }


@pytest.mark.asyncio
async def test_put_api_saves_and_returns_shared_requirement(db_session):
    saved = await save_ppe_requirement(
        PpeRequirementUpdate(
            helmet_required=True,
            safety_glasses_required=False,
            gloves_required=True,
        ),
        "uploaded_video",
        "zone_01",
        db_session,
    )
    loaded = await get_ppe_requirement("uploaded_video", "zone_01", db_session)

    assert saved.is_configured is True
    assert loaded.helmet_required is True
    assert loaded.safety_glasses_required is False
    assert loaded.gloves_required is True


@pytest.mark.parametrize(
    "validator,payload",
    [
        (
            TypeAdapter(PpeRequirementUpdate),
            {"helmet_required": True, "safety_glasses_required": False},
        ),
        (
            TypeAdapter(PpeRequirementUpdate),
            {
                "helmet_required": "yes",
                "safety_glasses_required": False,
                "gloves_required": False,
            },
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


@pytest.mark.parametrize(
    "required,status,confidence,expected",
    [
        (False, PpeStatus.MISSING, 0.99, False),
        (True, PpeStatus.PRESENT, 0.99, False),
        (True, PpeStatus.UNKNOWN, None, False),
        (True, PpeStatus.MISSING, None, False),
        (True, PpeStatus.MISSING, 0.49, False),
        (True, PpeStatus.MISSING, 0.5, True),
        (True, PpeStatus.MISSING, 0.99, True),
    ],
)
def test_missing_ppe_alert_truth_table(required, status, confidence, expected):
    assert (
        should_alert_for_missing_ppe(
            required=required,
            status=status,
            confidence=confidence,
            threshold=0.5,
        )
        is expected
    )
