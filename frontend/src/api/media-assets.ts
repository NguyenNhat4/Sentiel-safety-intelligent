import type {MediaAsset} from "../types";
import {getAccessToken} from "./auth";
import {apiUrl} from "./config";

export async function listMediaAssets(): Promise<MediaAsset[]> {
  const payload = await request<MediaAsset[] | {assets: MediaAsset[]}>("/media-assets");
  return Array.isArray(payload) ? payload : payload.assets;
}

export function uploadMediaAsset(displayName: string, file: File): Promise<MediaAsset> {
  const body = new FormData();
  body.append("display_name", displayName);
  body.append("file", file);
  return request<MediaAsset>("/media-assets", {method: "POST", body});
}

export function deleteMediaAsset(assetId: string): Promise<void> {
  return request<void>(`/media-assets/${encodeURIComponent(assetId)}`, {method: "DELETE"});
}

export async function loadMediaContent(assetId: string, signal?: AbortSignal): Promise<Blob> {
  const token = getAccessToken();
  if (!token) throw new Error("Phiên đăng nhập đã hết hạn.");
  const response = await fetch(apiUrl(`/media-assets/${encodeURIComponent(assetId)}/content`), {
    headers: {Authorization: `Bearer ${token}`},
    signal,
  });
  if (!response.ok) throw new Error(await responseError(response, "Không thể tải nội dung media"));
  return response.blob();
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getAccessToken();
  if (!token) throw new Error("Phiên đăng nhập đã hết hạn.");
  const response = await fetch(apiUrl(path), {
    ...init,
    headers: {Authorization: `Bearer ${token}`, ...init.headers},
  });
  if (!response.ok) throw new Error(await responseError(response, "Không thể hoàn tất yêu cầu media"));
  return response.status === 204 ? undefined as T : response.json() as Promise<T>;
}

async function responseError(response: Response, fallback: string): Promise<string> {
  try {
    const body = await response.json() as {detail?: string | {message?: string}};
    return typeof body.detail === "string" ? body.detail : body.detail?.message || `${fallback} (HTTP ${response.status})`;
  } catch {
    return `${fallback} (HTTP ${response.status})`;
  }
}
