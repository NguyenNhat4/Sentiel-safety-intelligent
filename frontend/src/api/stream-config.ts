import {getAccessToken} from "./auth";
import {apiUrl, streamerUrl} from "./config";
import type {StreamConfiguration} from "../types";

export async function getStreamConfiguration(signal?: AbortSignal): Promise<StreamConfiguration> {
  return authenticatedRequest<StreamConfiguration>("/stream-config", {signal});
}

export async function updateStreamConfiguration(mappings: StreamConfiguration["mappings"]): Promise<StreamConfiguration> {
  return authenticatedRequest<StreamConfiguration>("/stream-config", {
    method: "PUT",
    body: JSON.stringify({mappings}),
  });
}

export async function disconnectStream(cameraId: string): Promise<StreamConfiguration> {
  return authenticatedRequest<StreamConfiguration>(`/stream-config/${encodeURIComponent(cameraId)}`, {method: "DELETE"});
}

export async function listStreamerCameras(hlsToken = ""): Promise<string[]> {
  const response = await fetch(streamerUrl("/api/cameras"), {
    headers: {Authorization: `Bearer ${hlsToken}`},
  });
  if (!response.ok) throw new Error(`Không thể tải danh sách camera (HTTP ${response.status})`);
  return await response.json() as string[];
}

export function cameraStreamUrl(cameraId: string): string {
  return streamerUrl(`/stream/${encodeURIComponent(cameraId)}`);
}

async function authenticatedRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getAccessToken();
  if (!token) throw new Error("Phiên đăng nhập đã hết hạn.");
  const response = await fetch(apiUrl(path), {
    ...init,
    headers: {"Content-Type": "application/json", Authorization: `Bearer ${token}`, ...init.headers},
  });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try { detail = ((await response.json()) as {detail?: string}).detail || detail; } catch { /* non-JSON error */ }
    throw new Error(detail);
  }
  return await response.json() as T;
}
