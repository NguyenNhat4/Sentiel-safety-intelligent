from datetime import UTC, datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models.monitoring_zone import MonitoringZoneCollection, MonitoringZoneRecord
from backend.app.schemas.monitoring_zone import (
    MonitoringZone,
    MonitoringZoneCollectionResponse,
    MonitoringZoneCollectionUpdate,
)


class MonitoringZoneConflictError(RuntimeError):
    pass


class MonitoringZoneGeometryError(ValueError):
    def __init__(self, first_zone_id: str, second_zone_id: str | None = None):
        self.zone_ids = [first_zone_id] if second_zone_id is None else [first_zone_id, second_zone_id]
        super().__init__("Invalid or conflicting zone geometry")


class MonitoringZonePersistenceError(RuntimeError):
    pass


def validate_zone_geometry(zones: list[MonitoringZone]) -> None:
    for zone in zones:
        if not _is_simple_polygon(zone):
            raise MonitoringZoneGeometryError(zone.zone_id)
    active = [zone for zone in zones if zone.enabled]
    for index, first in enumerate(active):
        for second in active[index + 1 :]:
            if _polygons_conflict(first, second):
                raise MonitoringZoneGeometryError(first.zone_id, second.zone_id)


class MonitoringZoneService:
    def __init__(self, db: Session):
        self.db = db

    def get(self, camera_id: str) -> MonitoringZoneCollectionResponse:
        collection = self.db.get(MonitoringZoneCollection, camera_id)
        if collection is None:
            return MonitoringZoneCollectionResponse(camera_id=camera_id, revision=0, zones=[], updated_at=None)
        return self._response(collection)

    def save(
        self,
        camera_id: str,
        update: MonitoringZoneCollectionUpdate,
    ) -> MonitoringZoneCollectionResponse:
        validate_zone_geometry(update.zones)
        collection = self.db.get(MonitoringZoneCollection, camera_id)
        current = self.get(camera_id)
        desired_dump = [zone.model_dump(mode="json") for zone in sorted(update.zones, key=lambda item: item.order)]
        current_dump = [zone.model_dump(mode="json") for zone in current.zones]
        if desired_dump == current_dump:
            return current
        if update.expected_revision != current.revision:
            raise MonitoringZoneConflictError("Monitoring zone revision is stale")
        if collection is None:
            collection = MonitoringZoneCollection(camera_id=camera_id, revision=0)
            self.db.add(collection)
        existing = {record.normalized_zone_id: record for record in collection.zones}
        desired_ids: set[str] = set()
        for zone in update.zones:
            normalized_id = zone.zone_id.casefold()
            desired_ids.add(normalized_id)
            record = existing.get(normalized_id)
            if record is None:
                record = MonitoringZoneRecord(camera_id=camera_id, normalized_zone_id=normalized_id)
                collection.zones.append(record)
            record.zone_id = zone.zone_id
            record.display_name = zone.display_name
            record.points = [point.model_dump() for point in zone.points]
            record.machine_state = zone.machine_state
            record.enabled = zone.enabled
            record.order = zone.order
        for normalized_id, record in existing.items():
            if normalized_id not in desired_ids:
                record.enabled = False
        collection.revision = current.revision + 1
        collection.updated_at = datetime.now(UTC)
        try:
            self.db.commit()
            self.db.refresh(collection)
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise MonitoringZonePersistenceError("Could not save monitoring zones") from exc
        return self._response(collection)

    @staticmethod
    def _response(collection: MonitoringZoneCollection) -> MonitoringZoneCollectionResponse:
        zones = [
            MonitoringZone(
                zone_id=record.zone_id,
                display_name=record.display_name,
                points=record.points,
                machine_state=record.machine_state,
                enabled=record.enabled,
                order=record.order,
            )
            for record in sorted(collection.zones, key=lambda item: item.order)
        ]
        return MonitoringZoneCollectionResponse(
            camera_id=collection.camera_id,
            revision=collection.revision,
            zones=zones,
            updated_at=collection.updated_at,
        )


def _is_simple_polygon(zone: MonitoringZone) -> bool:
    points = [(point.x, point.y) for point in zone.points]
    area = sum(
        points[index][0] * points[(index + 1) % 4][1] - points[(index + 1) % 4][0] * points[index][1]
        for index in range(4)
    )
    if abs(area) <= 1e-12:
        return False
    return not (
        _segments_intersect(points[0], points[1], points[2], points[3])
        or _segments_intersect(points[1], points[2], points[3], points[0])
    )


def _polygons_conflict(first: MonitoringZone, second: MonitoringZone) -> bool:
    first_points = [(point.x, point.y) for point in first.points]
    second_points = [(point.x, point.y) for point in second.points]
    for first_index in range(4):
        for second_index in range(4):
            if _segments_intersect(
                first_points[first_index],
                first_points[(first_index + 1) % 4],
                second_points[second_index],
                second_points[(second_index + 1) % 4],
            ):
                return True
    return _point_in_polygon(first_points[0], second_points) or _point_in_polygon(second_points[0], first_points)


def _segments_intersect(a, b, c, d) -> bool:
    orientations = (_orientation(a, b, c), _orientation(a, b, d), _orientation(c, d, a), _orientation(c, d, b))
    if orientations[0] * orientations[1] < 0 and orientations[2] * orientations[3] < 0:
        return True
    return any(
        orientation == 0 and _on_segment(start, point, end)
        for orientation, start, point, end in (
            (orientations[0], a, c, b),
            (orientations[1], a, d, b),
            (orientations[2], c, a, d),
            (orientations[3], c, b, d),
        )
    )


def _orientation(a, b, c) -> int:
    value = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    if abs(value) <= 1e-12:
        return 0
    return 1 if value > 0 else -1


def _on_segment(a, point, b) -> bool:
    return (
        min(a[0], b[0]) - 1e-12 <= point[0] <= max(a[0], b[0]) + 1e-12
        and min(a[1], b[1]) - 1e-12 <= point[1] <= max(a[1], b[1]) + 1e-12
    )


def _point_in_polygon(point, polygon) -> bool:
    inside = False
    for index, first in enumerate(polygon):
        second = polygon[(index + 1) % len(polygon)]
        if _orientation(first, second, point) == 0 and _on_segment(first, point, second):
            return True
        if (first[1] > point[1]) != (second[1] > point[1]):
            boundary_x = (second[0] - first[0]) * (point[1] - first[1]) / (second[1] - first[1]) + first[0]
            if point[0] < boundary_x:
                inside = not inside
    return inside
