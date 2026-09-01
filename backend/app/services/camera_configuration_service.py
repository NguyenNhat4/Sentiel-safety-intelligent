from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models.camera_configuration import CameraConfiguration
from backend.app.models.media_asset import MediaAsset, MediaAssetStatus
from backend.app.models.monitoring_zone import MonitoringZoneCollection, MonitoringZoneRecord
from backend.app.models.ppe_requirement import PpeRequirement
from backend.app.schemas.camera_configuration import (
    CameraConfigurationResponse,
    CameraConfigurationUpdate,
    CameraConfigurationZone,
)
from backend.app.schemas.ppe_requirement import PpeRequirementUpdate
from backend.app.services.monitoring_zone_service import validate_zone_geometry

CAMERA_IDS = ("cam_1", "cam_2", "cam_3", "cam_4")


class CameraConfigurationNotFoundError(LookupError):
    pass


class CameraConfigurationConflictError(RuntimeError):
    pass


class CameraConfigurationInvalidError(ValueError):
    pass


class CameraConfigurationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[CameraConfigurationResponse]:
        return [self.get(camera_id) for camera_id in CAMERA_IDS]

    def get(self, camera_id: str) -> CameraConfigurationResponse:
        self._validate_camera_id(camera_id)
        configuration = self.db.get(CameraConfiguration, camera_id)
        collection = self.db.get(MonitoringZoneCollection, camera_id)
        requirements = {
            item.zone_id: item
            for item in self.db.scalars(select(PpeRequirement).where(PpeRequirement.camera_id == camera_id))
        }
        zones = [] if collection is None else sorted(collection.zones, key=lambda item: item.order)
        return CameraConfigurationResponse(
            camera_id=camera_id,
            camera_name=configuration.asset.display_name if configuration and configuration.asset else None,
            revision=configuration.revision if configuration else (collection.revision if collection else 0),
            asset_id=configuration.asset_id if configuration else None,
            machine_state=configuration.machine_state if configuration else "stopped",
            ppe_requirements=PpeRequirementUpdate(
                profile="hat_vest_v1",
                hat_required=configuration.hat_required if configuration else False,
                vest_required=configuration.vest_required if configuration else False,
            ),
            zones=[self._zone_response(record, requirements.get(record.zone_id)) for record in zones],
            updated_at=configuration.updated_at if configuration else (collection.updated_at if collection else None),
        )

    def save(self, camera_id: str, payload: CameraConfigurationUpdate) -> CameraConfigurationResponse:
        self._validate_camera_id(camera_id)
        validate_zone_geometry(payload.monitoring_zones())
        try:
            configuration = self.db.get(CameraConfiguration, camera_id, with_for_update=True)
            current_revision = configuration.revision if configuration else 0
            if payload.expected_revision != current_revision:
                raise CameraConfigurationConflictError("Camera configuration revision is stale")
            if payload.asset_id is not None:
                asset = self.db.get(MediaAsset, str(payload.asset_id), with_for_update=True)
                if asset is None or asset.status != MediaAssetStatus.READY.value:
                    raise CameraConfigurationInvalidError("A READY media asset is required")
                assigned = self.db.scalar(
                    select(CameraConfiguration.camera_id).where(
                        CameraConfiguration.asset_id == str(payload.asset_id),
                        CameraConfiguration.camera_id != camera_id,
                    )
                )
                if assigned:
                    raise CameraConfigurationConflictError("Media asset is assigned to another camera")
            if configuration is None:
                configuration = CameraConfiguration(camera_id=camera_id)
                self.db.add(configuration)
            configuration.asset_id = str(payload.asset_id) if payload.asset_id is not None else None
            configuration.machine_state = payload.machine_state
            configuration.hat_required = payload.ppe_requirements.hat_required
            configuration.vest_required = payload.ppe_requirements.vest_required
            configuration.revision = current_revision + 1
            configuration.updated_at = datetime.now(UTC)

            collection = self.db.get(MonitoringZoneCollection, camera_id)
            if collection is None:
                collection = MonitoringZoneCollection(camera_id=camera_id)
                self.db.add(collection)
            self.db.query(MonitoringZoneRecord).filter(MonitoringZoneRecord.camera_id == camera_id).delete(
                synchronize_session=False
            )
            self.db.query(PpeRequirement).filter(PpeRequirement.camera_id == camera_id).delete(
                synchronize_session=False
            )
            collection.revision = configuration.revision
            collection.updated_at = configuration.updated_at
            for zone in payload.zones:
                self.db.add(
                    MonitoringZoneRecord(
                        camera_id=camera_id,
                        zone_id=zone.zone_id,
                        normalized_zone_id=zone.zone_id.casefold(),
                        display_name=zone.display_name,
                        points=[point.model_dump() for point in zone.points],
                        machine_state=payload.machine_state,
                        enabled=zone.enabled,
                        order=zone.order,
                    )
                )
                requirement = zone.ppe_requirements
                self.db.add(
                    PpeRequirement(
                        camera_id=camera_id,
                        zone_id=zone.zone_id,
                        hat_required=requirement.hat_required,
                        vest_required=requirement.vest_required,
                        restricted_area_detection_enabled=requirement.restricted_area_detection_enabled,
                        zone_intrusion_enabled=requirement.zone_intrusion_enabled,
                    )
                )
            self.db.commit()
            self.db.expire_all()
        except CameraConfigurationConflictError:
            self.db.rollback()
            raise
        except CameraConfigurationInvalidError:
            self.db.rollback()
            raise
        except IntegrityError as exc:
            self.db.rollback()
            raise CameraConfigurationConflictError("Media asset is assigned to another camera") from exc
        except SQLAlchemyError:
            self.db.rollback()
            raise
        return self.get(camera_id)

    @staticmethod
    def _validate_camera_id(camera_id: str) -> None:
        if camera_id not in CAMERA_IDS:
            raise CameraConfigurationNotFoundError("Camera configuration not found")

    @staticmethod
    def _zone_response(record: MonitoringZoneRecord, requirement: PpeRequirement | None) -> CameraConfigurationZone:
        rules = PpeRequirementUpdate(
            profile="hat_vest_v1",
            hat_required=requirement.hat_required if requirement else False,
            vest_required=requirement.vest_required if requirement else False,
            restricted_area_detection_enabled=(requirement.restricted_area_detection_enabled if requirement else False),
            zone_intrusion_enabled=requirement.zone_intrusion_enabled if requirement else True,
        )
        return CameraConfigurationZone(
            zone_id=record.zone_id,
            display_name=record.display_name,
            points=record.points,
            enabled=record.enabled,
            order=record.order,
            ppe_requirements=rules,
        )
