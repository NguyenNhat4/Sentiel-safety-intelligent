import type {MediaAsset, MediaStorageBackend} from "../types";
import {getAccessToken} from "./auth";
import {apiUrl} from "./config";

export async function listMediaAssets(): Promise<MediaAsset[]> {
  const payload = await request<MediaAsset[] | {assets: MediaAsset[]}>("/media-assets");
  return Array.isArray(payload) ? payload : payload.assets;
}

export async function uploadMediaAsset(displayName: string, file: File): Promise<MediaAsset> {
  const preparedResponse = await authorizedFetch("/media-assets/upload-requests", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({display_name: displayName, filename: file.name, content_type: file.type, size_bytes: file.size}),
  });
  if (preparedResponse.status === 409) return uploadMediaAssetThroughBackend(displayName, file);
  if (!preparedResponse.ok) throw new Error(await responseError(preparedResponse, "Không thể chuẩn bị tải media"));
  const prepared = await preparedResponse.json() as {asset: MediaAsset; upload_url: string; fields: Record<string, string>};
  const directBody = new FormData();
  Object.entries(prepared.fields).forEach(([key, value]) => directBody.append(key, value));
  directBody.append("Content-Type", file.type);
  directBody.append("file", file);
  const uploaded = await fetch(prepared.upload_url, {method: "POST", body: directBody});
  if (!uploaded.ok) throw new Error(`Không thể tải media trực tiếp lên bucket (HTTP ${uploaded.status})`);
  return request<MediaAsset>(`/media-assets/${encodeURIComponent(prepared.asset.id)}/complete`, {method: "POST"});
}

function uploadMediaAssetThroughBackend(displayName: string, file: File): Promise<MediaAsset> {
  const body = new FormData();
  body.append("display_name", displayName);
  body.append("file", file);
  return request<MediaAsset>("/media-assets", {method: "POST", body});
}

export function deleteMediaAsset(assetId: string): Promise<void> {
  return request<void>(`/media-assets/${encodeURIComponent(assetId)}`, {method: "DELETE"});
}

export async function loadMediaContent(assetId: string, signal?: AbortSignal): Promise<Blob> {
  const response = await authorizedFetch(`/media-assets/${encodeURIComponent(assetId)}/content`, {signal});
  if (!response.ok) throw new Error(await responseError(response, "Không thể tải nội dung media"));
  return response.blob();
}

export async function loadMediaSource(assetId: string, storageBackend?: MediaStorageBackend, signal?: AbortSignal): Promise<{url: string; revoke: boolean}> {
  if (storageBackend === "filesystem") {
    return {url: URL.createObjectURL(await loadMediaContent(assetId, signal)), revoke: true};
  }
  const response = await authorizedFetch(`/media-assets/${encodeURIComponent(assetId)}/playback-url`, {signal});
  if (response.ok) return {url: ((await response.json()) as {url: string}).url, revoke: false};
  if (response.status !== 409) throw new Error(await responseError(response, "Không thể tải nội dung media"));
  return {url: URL.createObjectURL(await loadMediaContent(assetId, signal)), revoke: true};
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await authorizedFetch(path, init);
  if (!response.ok) throw new Error(await responseError(response, "Không thể hoàn tất yêu cầu media"));
  return response.status === 204 ? undefined as T : response.json() as Promise<T>;
}

async function authorizedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const token = getAccessToken();
  if (!token) throw new Error("Phiên đăng nhập đã hết hạn.");
  return fetch(apiUrl(path), {
    ...init,
    headers: {Authorization: `Bearer ${token}`, ...init.headers},
  });
}

async function responseError(response: Response, fallback: string): Promise<string> {
  try {
    const body = await response.json() as {detail?: string | {message?: string}};
    return typeof body.detail === "string" ? body.detail : body.detail?.message || `${fallback} (HTTP ${response.status})`;
  } catch {
    return `${fallback} (HTTP ${response.status})`;
  }
}
