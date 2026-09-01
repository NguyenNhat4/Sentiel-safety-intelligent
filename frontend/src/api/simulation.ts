import type {CameraSession} from "../types";
import {getAccessToken} from "./auth";
import {apiUrl} from "./config";
import {fetchQuery, peekQuery, revalidateQuery, setQueryData} from "./query-cache";

const SESSIONS_KEY = "camera-sessions:list";
const SESSIONS_TTL_MS = 3_000;

export function getCachedCameraSessions(): CameraSession[] | undefined {
  return peekQuery(SESSIONS_KEY);
}

export async function listCameraSessions(options: {forceRefresh?: boolean} = {}): Promise<CameraSession[]> {
  const loader = async () => {
    const payload = await request<CameraSession[] | {sessions: CameraSession[]}>("/camera-sessions");
    return Array.isArray(payload) ? payload : payload.sessions;
  };
  return options.forceRefresh ? revalidateQuery(SESSIONS_KEY, loader) : fetchQuery(SESSIONS_KEY, loader, SESSIONS_TTL_MS);
}

export interface SimulationRunResult { sessions: CameraSession[]; errors: Record<string, string>; }

export async function runSimulation(): Promise<SimulationRunResult> {
  const result = await request<SimulationRunResult>("/simulation-runs", {method: "POST"});
  mergeSessions(result.sessions);
  return result;
}

export async function replayCamera(cameraId: string): Promise<CameraSession> {
  const session = await request<CameraSession>(`/camera-sessions/${encodeURIComponent(cameraId)}/replay`, {method: "POST"});
  mergeSessions([session]);
  return session;
}

export function cacheCameraSessions(sessions: CameraSession[]): void {
  mergeSessions(sessions);
}

function mergeSessions(sessions: CameraSession[]): void {
  const current = peekQuery<CameraSession[]>(SESSIONS_KEY) ?? [];
  const cameras = new Set(sessions.map(session => session.camera_id));
  setQueryData(SESSIONS_KEY, [...current.filter(session => !cameras.has(session.camera_id)), ...sessions], SESSIONS_TTL_MS);
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
