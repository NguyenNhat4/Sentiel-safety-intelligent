import type {
  EventBatchPayload,
  EventBatchResponse,
  EventDetail,
  EventPayload,
  ReviewStatus,
  SafetyEvent,
} from "../types";
import {getAccessToken} from "./auth";
import {apiUrl} from "./config";

const SAFETY_EVENT_UPDATE_NAME = "sentinel:safety-event-update";
const SAFETY_EVENT_UPDATE_CHANNEL = "sentinel:safety-events";

export interface SafetyEventUpdate {
  eventIds: number[];
  cameraIds: string[];
}

let eventUpdateChannel: BroadcastChannel | null | undefined;

export async function loadAcknowledgedEvents(): Promise<SafetyEvent[]> {
  return loadReviewedEvents("acknowledged");
}

export async function loadReviewedEvents(status: ReviewStatus): Promise<SafetyEvent[]> {
  const response = await fetch(
    apiUrl(`/events?status=${encodeURIComponent(status)}&limit=50`),
    {cache: "no-store", headers: authorizationHeaders()},
  );
  if (!response.ok) throw new Error(`Không thể tải nhật ký (HTTP ${response.status})`);
  return response.json() as Promise<SafetyEvent[]>;
}

export async function loadPendingEvents(signal?: AbortSignal): Promise<SafetyEvent[]> {
  const response = await fetch(apiUrl("/events?status=unacknowledged&limit=200"), {
    cache: "no-store",
    headers: authorizationHeaders(),
    signal,
  });
  if (!response.ok) throw new Error(`Không thể tải cảnh báo chờ xử lý (HTTP ${response.status})`);
  return response.json() as Promise<SafetyEvent[]>;
}

export async function loadCameraEvents(cameraId: string): Promise<SafetyEvent[]> {
  const response = await fetch(
    apiUrl(`/events?camera_id=${encodeURIComponent(cameraId)}&limit=50`),
    {cache: "no-store", headers: authorizationHeaders()},
  );
  if (!response.ok) throw new Error(`Không thể tải log Camera (HTTP ${response.status})`);
  return response.json() as Promise<SafetyEvent[]>;
}

export async function loadEventDetail(eventId: number): Promise<EventDetail> {
  const response = await fetch(
    apiUrl(`/events/${encodeURIComponent(String(eventId))}`),
    {cache: "no-store", headers: authorizationHeaders()},
  );
  if (!response.ok) throw new Error(`Không thể tải chi tiết sự kiện (HTTP ${response.status})`);
  return response.json() as Promise<EventDetail>;
}

export async function saveReviewedEvent(payload: EventPayload): Promise<SafetyEvent> {
  const response = await fetch(apiUrl("/events"), {
    method: "POST",
    headers: {"Content-Type": "application/json", ...authorizationHeaders()},
    body: JSON.stringify(payload)
  });
  if (!response.ok) throw new Error(await readErrorMessage(response));
  const event = await response.json() as SafetyEvent;
  publishSafetyEventUpdate([event]);
  return event;
}

export async function saveReviewedEventBatch(payload: EventBatchPayload): Promise<EventBatchResponse> {
  const response = await fetch(apiUrl("/event-batches"), {
    method: "POST",
    headers: {"Content-Type": "application/json", ...authorizationHeaders()},
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await readErrorMessage(response));
  const batch = await response.json() as EventBatchResponse;
  publishSafetyEventUpdate(batch.events);
  return batch;
}

export async function loadAreaEvents(): Promise<SafetyEvent[]> {
  const response = await fetch(apiUrl("/events?limit=50"), {
    cache: "no-store",
    headers: authorizationHeaders(),
  });
  if (!response.ok) throw new Error(`Không thể tải nhật ký khu vực (HTTP ${response.status})`);
  return response.json() as Promise<SafetyEvent[]>;
}

export async function updateAreaEvent(eventId: number, status: "resolved" | "false_alarm"): Promise<SafetyEvent> {
  const response = await fetch(apiUrl(`/events/${eventId}`), {
    method: "PATCH",
    headers: {"Content-Type": "application/json", ...authorizationHeaders()},
    body: JSON.stringify({status}),
  });
  if (!response.ok) throw new Error(await readErrorMessage(response));
  const event = await response.json() as SafetyEvent;
  publishSafetyEventUpdate([event]);
  return event;
}

export function subscribeToSafetyEventUpdates(listener: (update: SafetyEventUpdate) => void): () => void {
  const handleWindowUpdate = (event: Event) => listener((event as CustomEvent<SafetyEventUpdate>).detail);
  const handleChannelUpdate = (event: MessageEvent<SafetyEventUpdate>) => listener(event.data);
  window.addEventListener(SAFETY_EVENT_UPDATE_NAME, handleWindowUpdate);
  const channel = getEventUpdateChannel();
  channel?.addEventListener("message", handleChannelUpdate);
  return () => {
    window.removeEventListener(SAFETY_EVENT_UPDATE_NAME, handleWindowUpdate);
    channel?.removeEventListener("message", handleChannelUpdate);
  };
}

function publishSafetyEventUpdate(events: SafetyEvent[]): void {
  if (!events.length) return;
  const update: SafetyEventUpdate = {
    eventIds: [...new Set(events.map(event => event.id))],
    cameraIds: [...new Set(events.map(event => event.camera_id))],
  };
  window.dispatchEvent(new CustomEvent<SafetyEventUpdate>(SAFETY_EVENT_UPDATE_NAME, {detail: update}));
  getEventUpdateChannel()?.postMessage(update);
}

function getEventUpdateChannel(): BroadcastChannel | null {
  if (eventUpdateChannel !== undefined) return eventUpdateChannel;
  eventUpdateChannel = typeof BroadcastChannel === "function"
    ? new BroadcastChannel(SAFETY_EVENT_UPDATE_CHANNEL)
    : null;
  return eventUpdateChannel;
}

function authorizationHeaders(): Record<string, string> {
  const token = getAccessToken();
  return token ? {Authorization: `Bearer ${token}`} : {};
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json() as {detail?: string};
    return body.detail || `Không thể lưu kết quả xác minh (HTTP ${response.status})`;
  } catch {
    return `Không thể lưu kết quả xác minh (HTTP ${response.status})`;
  }
}
