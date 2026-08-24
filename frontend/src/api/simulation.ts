import type {CameraSession} from "../types";
import {getAccessToken} from "./auth";
import {apiUrl} from "./config";

export async function listCameraSessions(signal?: AbortSignal): Promise<CameraSession[]> {
  const payload = await request<CameraSession[] | {sessions: CameraSession[]}>("/camera-sessions", {signal});
  return Array.isArray(payload) ? payload : payload.sessions;
}

export interface SimulationRunResult { sessions: CameraSession[]; errors: Record<string, string>; }

export function runSimulation(): Promise<SimulationRunResult> {
  return request<SimulationRunResult>("/simulation-runs", {method: "POST"});
}

export function replayCamera(cameraId: string): Promise<CameraSession> {
  return request<CameraSession>(`/camera-sessions/${encodeURIComponent(cameraId)}/replay`, {method: "POST"});
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getAccessToken();
  if (!token) throw new Error("Phiên đăng nhập đã hết hạn.");
  const response = await fetch(apiUrl(path), {
    ...init,
    headers: {"Content-Type": "application/json", Authorization: `Bearer ${token}`, ...init.headers},
  });
  if (!response.ok) {
    let detail = `Không thể điều khiển mô phỏng (HTTP ${response.status})`;
    try { detail = ((await response.json()) as {detail?: string}).detail || detail; } catch { /* non-JSON error */ }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}
