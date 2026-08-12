import type {MonitoringZone, MonitoringZoneCollection} from "../types";
import {apiUrl} from "./config";

export async function loadMonitoringZones(cameraId: string): Promise<MonitoringZoneCollection> {
  const response = await fetch(apiUrl(`/cameras/${encodeURIComponent(cameraId)}/monitoring-zones`));
  if (!response.ok) throw new Error(`Không thể tải cấu hình vùng (HTTP ${response.status})`);
  return response.json() as Promise<MonitoringZoneCollection>;
}

export async function saveMonitoringZones(
  cameraId: string,
  expectedRevision: number,
  zones: MonitoringZone[],
): Promise<MonitoringZoneCollection> {
  const response = await fetch(apiUrl(`/cameras/${encodeURIComponent(cameraId)}/monitoring-zones`), {
    method: "PUT",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({expected_revision: expectedRevision, zones}),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => undefined) as {detail?: {code?: string; zone_ids?: string[]}} | undefined;
    if (response.status === 409 && body?.detail?.code === "revision_conflict") {
      throw new Error("Cấu hình vùng đã thay đổi ở nơi khác. Hãy tải lại và hòa giải thay đổi.");
    }
    if (response.status === 422 && body?.detail?.code === "zone_geometry_conflict") {
      throw new Error(`Các vùng đang xung đột: ${body.detail.zone_ids?.join(", ") ?? "không xác định"}`);
    }
    throw new Error(`Không thể lưu cấu hình vùng (HTTP ${response.status})`);
  }
  return response.json() as Promise<MonitoringZoneCollection>;
}
