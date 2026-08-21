const configuredBackend = (import.meta.env.VITE_BACKEND_URL || "").replace(/\/$/, "");
const configuredStreamer = (import.meta.env.VITE_STREAMER_URL || "").replace(/\/$/, "");
const configuredMedia = (import.meta.env.VITE_MEDIA_PUBLIC_ORIGIN || "").replace(/\/$/, "");

let activeBackendOrigin = configuredBackend;

export function apiUrl(path: string): string {
  return `${activeBackendOrigin}/api/v1${path}`;
}

export function streamerUrl(path: string): string {
  const origin = configuredStreamer || `${window.location.protocol}//${window.location.hostname}:8001`;
  return `${origin}${path}`;
}

export function mediaUrl(path: string): string {
  const origin = configuredMedia || `${window.location.protocol}//${window.location.hostname}:8888`;
  return `${origin}${path}`;
}

export function assetUrl(path?: string | null): string | null {
  if (!path) return null;
  return new URL(path, `${backendOrigin()}/`).toString();
}

export function inferenceWebSocketUrls(): string[] {
  if (configuredBackend) return [`${toWebSocketOrigin(configuredBackend)}/api/v1/ws/inference`];
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const hostname = window.location.hostname || "127.0.0.1";
  const candidates = window.location.host
    ? [`${protocol}//${window.location.host}/api/v1/ws/inference`]
    : [];
  candidates.push(`${protocol}//${hostname}:8000/api/v1/ws/inference`);
  return [...new Set(candidates)];
}

export function setBackendFromSocket(socketUrl: string): void {
  if (configuredBackend) return;
  const backendUrl = new URL(socketUrl);
  backendUrl.protocol = backendUrl.protocol === "wss:" ? "https:" : "http:";
  activeBackendOrigin = backendUrl.origin === window.location.origin ? "" : backendUrl.origin;
}

export function resetBackendForTests(): void {
  activeBackendOrigin = configuredBackend;
}

function backendOrigin(): string {
  return activeBackendOrigin || window.location.origin;
}

function toWebSocketOrigin(origin: string): string {
  const url = new URL(origin);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.origin;
}
