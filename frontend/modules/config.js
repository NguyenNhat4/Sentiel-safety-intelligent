export const SAMPLE_INTERVAL_SECONDS = 0.5;
export const JPEG_QUALITY = 0.82;
export const PREVIEW_CANDIDATES = [0.05, 0.5, 1, 2, 3, 4, 5, 7, 10];

let apiBase = `${defaultBackendHttpOrigin()}/api/v1`;

export function getApiBase() {
  return apiBase;
}

export function resolveBackendUrl(path) {
  if (!path) return null;
  return new URL(path, `${new URL(apiBase).origin}/`).toString();
}

export function setApiBaseFromSocket(socketUrl) {
  const backendUrl = new URL(socketUrl);
  backendUrl.protocol = backendUrl.protocol === "wss:" ? "https:" : "http:";
  apiBase = `${backendUrl.origin}/api/v1`;
}

export function inferenceWebSocketUrls() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const hostname = window.location.hostname || "127.0.0.1";
  const candidates = [];
  if (window.location.host) candidates.push(`${protocol}//${window.location.host}/api/v1/ws/inference`);
  candidates.push(`${protocol}//${hostname}:8000/api/v1/ws/inference`);
  return [...new Set(candidates)];
}

function defaultBackendHttpOrigin() {
  if (["http:", "https:"].includes(window.location.protocol)) return window.location.origin;
  return "http://127.0.0.1:8000";
}
