import enum

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models.ppe_requirement import PpeRequirement
from backend.app.schemas.ppe_requirement import (
    PpeRequirementResponse,
    PpeRequirementUpdate,
)


class PpeStatus(enum.StrEnum):
    PRESENT = "present"
    MISSING = "missing"
    UNKNOWN = "unknown"


def should_alert_for_missing_ppe(
    *,
    required: bool,
    status: PpeStatus,
    person_confidence: float,
    threshold: float,
    association_is_valid: bool,
) -> bool:
    return required and status is PpeStatus.MISSING and person_confidence >= threshold and association_is_valid


class PpeRequirementPersistenceError(RuntimeError):
    pass


class PpeRequirementService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, camera_id: str, zone_id: str) -> PpeRequirementResponse:
        requirement = self._find(camera_id, zone_id)
        if requirement is None:
            return PpeRequirementResponse(
                camera_id=camera_id,
                zone_id=zone_id,
                helmet_required=False,
                safety_glasses_required=False,
                gloves_required=False,
                is_configured=False,
                updated_at=None,
            )
        return PpeRequirementResponse.model_validate(requirement)

    def save(
        self,
        camera_id: str,
        zone_id: str,
        update: PpeRequirementUpdate,
    ) -> PpeRequirementResponse:
        try:
            requirement = self._find(camera_id, zone_id)
            if requirement is None:
                requirement = PpeRequirement(camera_id=camera_id, zone_id=zone_id)
                self._db.add(requirement)

            requirement.helmet_required = update.helmet_required
            requirement.safety_glasses_required = update.safety_glasses_required
            requirement.gloves_required = update.gloves_required
            self._db.commit()
        except SQLAlchemyError as exc:
            self._db.rollback()
            raise PpeRequirementPersistenceError("Could not save PPE requirements") from exc
        return PpeRequirementResponse.model_validate(requirement)

    def count(self) -> int:
        return self._db.scalar(select(func.count()).select_from(PpeRequirement)) or 0

    def _find(self, camera_id: str, zone_id: str) -> PpeRequirement | None:
        return self._db.scalar(
            select(PpeRequirement).where(
                PpeRequirement.camera_id == camera_id,
                PpeRequirement.zone_id == zone_id,
            )
        )
