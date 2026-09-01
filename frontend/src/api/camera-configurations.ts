import type {CameraConfiguration, CameraConfigurationUpdate} from "../types";
import {getAccessToken} from "./auth";
import {apiUrl} from "./config";
import {fetchQuery, invalidateQueries, peekQuery, revalidateQuery, setQueryData} from "./query-cache";

const LIST_KEY = "camera-configurations:list";
const TTL_MS = 60_000;

export interface QueryOptions { forceRefresh?: boolean }

export function getCachedCameraConfigurations(): CameraConfiguration[] | undefined {
  return peekQuery(LIST_KEY);
}

export function getCachedCameraConfiguration(cameraId: string): CameraConfiguration | undefined {
  return peekQuery(configurationKey(cameraId));
}

export async function listCameraConfigurations(options: QueryOptions = {}): Promise<CameraConfiguration[]> {
  const loader = async () => {
    const payload = await request<CameraConfiguration[] | {configurations: CameraConfiguration[]}>("/camera-configurations");
    const configurations = Array.isArray(payload) ? payload : payload.configurations;
    configurations.forEach(configuration => setQueryData(configurationKey(configuration.camera_id), configuration, TTL_MS));
    return configurations;
  };
  return options.forceRefresh ? revalidateQuery(LIST_KEY, loader) : fetchQuery(LIST_KEY, loader, TTL_MS);
}

export function loadCameraConfiguration(cameraId: string, options: QueryOptions = {}): Promise<CameraConfiguration> {
  const key = configurationKey(cameraId);
  const loader = () => request<CameraConfiguration>(`/camera-configurations/${encodeURIComponent(cameraId)}`);
  return options.forceRefresh ? revalidateQuery(key, loader) : fetchQuery(key, loader, TTL_MS);
}

export async function saveCameraConfiguration(cameraId: string, update: CameraConfigurationUpdate): Promise<CameraConfiguration> {
  const persisted = await request<CameraConfiguration>(`/camera-configurations/${encodeURIComponent(cameraId)}`, {
    method: "PUT",
    body: JSON.stringify(update),
  });
  setQueryData(configurationKey(cameraId), persisted, TTL_MS);
  const cached = peekQuery<CameraConfiguration[]>(LIST_KEY);
  if (cached) {
    const exists = cached.some(item => item.camera_id === cameraId);
    const next = exists
      ? cached.map(item => item.camera_id === cameraId ? persisted : item)
      : [...cached, persisted];
    setQueryData(LIST_KEY, next, TTL_MS);
  }
  else invalidateQueries(LIST_KEY);
  invalidateQueries("media-assets:list");
  return persisted;
}

function configurationKey(cameraId: string): string {
  return `camera-configurations:${cameraId}`;
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
