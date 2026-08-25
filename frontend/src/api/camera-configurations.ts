import type {CameraConfiguration, CameraConfigurationUpdate} from "../types";
import {getAccessToken} from "./auth";
import {apiUrl} from "./config";

export async function listCameraConfigurations(signal?: AbortSignal): Promise<CameraConfiguration[]> {
  const payload = await request<CameraConfiguration[] | {configurations: CameraConfiguration[]}>("/camera-configurations", {signal});
  return Array.isArray(payload) ? payload : payload.configurations;
}

export function loadCameraConfiguration(cameraId: string, signal?: AbortSignal): Promise<CameraConfiguration> {
  return request<CameraConfiguration>(`/camera-configurations/${encodeURIComponent(cameraId)}`, {signal});
}

export function saveCameraConfiguration(cameraId: string, update: CameraConfigurationUpdate): Promise<CameraConfiguration> {
  return request<CameraConfiguration>(`/camera-configurations/${encodeURIComponent(cameraId)}`, {
    method: "PUT",
    body: JSON.stringify(update),
  });
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getAccessToken();
  if (!token) throw new Error("Phiên đăng nhập đã hết hạn.");
  const response = await fetch(apiUrl(path), {
    ...init,
    headers: {"Content-Type": "application/json", Authorization: `Bearer ${token}`, ...init.headers},
  });
  if (!response.ok) {
    let detail = `Không thể tải cấu hình camera (HTTP ${response.status})`;
    try {
      const body = await response.json() as {detail?: string | {code?: string; message?: string; zone_ids?: string[]}};
      if (typeof body.detail === "string") detail = body.detail;
      else if (body.detail?.code === "configuration_conflict") detail = "Cấu hình đã thay đổi hoặc media đang được camera khác sử dụng. Hãy tải lại trước khi lưu.";
      else if (body.detail?.code === "zone_geometry_conflict") detail = `Các vùng đang xung đột: ${body.detail.zone_ids?.join(", ") || "không xác định"}.`;
      else detail = body.detail?.message || detail;
    } catch { /* non-JSON error */ }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}
