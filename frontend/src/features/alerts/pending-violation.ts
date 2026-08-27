import type {SafetyEvent} from "../../types";

export function isZoneAlert(alert: SafetyEvent): boolean {
  return alert.event_type === "zone_intrusion" || alert.event_type === "missing_ppe_and_intrusion";
}

export function cameraLabel(cameraId: string): string {
  const number = cameraId.match(/^cam_(\d+)$/)?.[1];
  return number ? `Camera ${Number(number)}` : cameraId;
}

export function zoneLabel(alert: SafetyEvent): string {
  const result = alert.details?.pending_review;
  const zoneId = result?.people.flatMap(person => person.active_violations ?? [])
    .find(item => item.zone_id && item.zone_id !== "camera_wide")?.zone_id ?? alert.zone_id;
  return `Vùng ${zoneId}`;
}

export function missingPpeLabel(alert: SafetyEvent): string {
  const keys = alert.details?.violations ?? [];
  const labels = keys.filter(key => key.startsWith("missing_ppe:"))
    .map(key => key.endsWith(":hat") ? "mũ bảo hộ" : key.endsWith(":vest") ? "áo phản quang" : "PPE");
  return labels.length ? `Thiếu ${labels.join(" và ")}` : "Thiếu PPE";
}
