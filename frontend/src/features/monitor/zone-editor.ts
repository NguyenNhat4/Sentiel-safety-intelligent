import type {MonitoringZone, ZonePoint} from "../../types";

export function createZoneDraft(zones: MonitoringZone[]): MonitoringZone {
  const used = new Set(zones.map(zone => zone.zone_id.toLowerCase()));
  let number = zones.length + 1;
  while (used.has(`zone_${number}`)) number += 1;
  return {
    zone_id: `zone_${number}`,
    display_name: `Vùng ${number}`,
    points: [],
    machine_state: "stopped",
    enabled: true,
    order: zones.reduce((highest, zone) => Math.max(highest, zone.order), -1) + 1,
  };
}

export function findZonePointAt(
  zones: MonitoringZone[],
  position: ZonePoint,
  size: Pick<DOMRect, "width" | "height">,
): {zoneId: string; pointIndex: number} | null {
  for (const zone of zones) {
    const pointIndex = zone.points.findIndex(point => {
      const dx = (point.x - position.x) * size.width;
      const dy = (point.y - position.y) * size.height;
      return Math.hypot(dx, dy) <= 18;
    });
    if (pointIndex !== -1) return {zoneId: zone.zone_id, pointIndex};
  }
  return null;
}

export function zoneGeometryConflict(zones: MonitoringZone[]): [string, string] | null {
  for (const zone of zones) {
    if (zone.points.length === 4 && !isSimple(zone.points)) return [zone.zone_id, zone.zone_id];
  }
  const active = zones.filter(zone => zone.enabled && zone.points.length === 4);
  for (let index = 0; index < active.length; index += 1) {
    for (let second = index + 1; second < active.length; second += 1) {
      if (polygonsConflict(active[index].points, active[second].points)) {
        return [active[index].zone_id, active[second].zone_id];
      }
    }
  }
  return null;
}

function isSimple(points: ZonePoint[]): boolean {
  const area = points.reduce((sum, point, index) => {
    const next = points[(index + 1) % points.length];
    return sum + point.x * next.y - next.x * point.y;
  }, 0);
  return Math.abs(area) > 1e-12
    && !segmentsIntersect(points[0], points[1], points[2], points[3])
    && !segmentsIntersect(points[1], points[2], points[3], points[0]);
}

function polygonsConflict(first: ZonePoint[], second: ZonePoint[]): boolean {
  for (let one = 0; one < 4; one += 1) {
    for (let two = 0; two < 4; two += 1) {
      if (segmentsIntersect(first[one], first[(one + 1) % 4], second[two], second[(two + 1) % 4])) return true;
    }
  }
  return pointInPolygon(first[0], second) || pointInPolygon(second[0], first);
}

function segmentsIntersect(a: ZonePoint, b: ZonePoint, c: ZonePoint, d: ZonePoint): boolean {
  const values = [orientation(a, b, c), orientation(a, b, d), orientation(c, d, a), orientation(c, d, b)];
  if (values[0] * values[1] < 0 && values[2] * values[3] < 0) return true;
  return (values[0] === 0 && onSegment(a, c, b))
    || (values[1] === 0 && onSegment(a, d, b))
    || (values[2] === 0 && onSegment(c, a, d))
    || (values[3] === 0 && onSegment(c, b, d));
}

function orientation(a: ZonePoint, b: ZonePoint, c: ZonePoint): number {
  const value = (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
  return Math.abs(value) <= 1e-12 ? 0 : value > 0 ? 1 : -1;
}

function onSegment(a: ZonePoint, point: ZonePoint, b: ZonePoint): boolean {
  return point.x >= Math.min(a.x, b.x) - 1e-12 && point.x <= Math.max(a.x, b.x) + 1e-12
    && point.y >= Math.min(a.y, b.y) - 1e-12 && point.y <= Math.max(a.y, b.y) + 1e-12;
}

function pointInPolygon(point: ZonePoint, polygon: ZonePoint[]): boolean {
  let inside = false;
  for (let index = 0; index < polygon.length; index += 1) {
    const first = polygon[index];
    const second = polygon[(index + 1) % polygon.length];
    if (orientation(first, second, point) === 0 && onSegment(first, point, second)) return true;
    else if ((first.y > point.y) !== (second.y > point.y)) {
      const boundaryX = (second.x - first.x) * (point.y - first.y) / (second.y - first.y) + first.x;
      if (point.x < boundaryX) inside = !inside;
    }
  }
  return inside;
}
