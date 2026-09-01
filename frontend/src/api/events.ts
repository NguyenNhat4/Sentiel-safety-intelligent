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
import {fetchQuery, invalidateQueries, peekQuery, revalidateQuery, setQueryData} from "./query-cache";

const SAFETY_EVENT_UPDATE_NAME = "sentinel:safety-event-update";
const SAFETY_EVENT_UPDATE_CHANNEL = "sentinel:safety-events";

export interface SafetyEventUpdate {
  eventIds: number[];
  cameraIds: string[];
}

let eventUpdateChannel: BroadcastChannel | null | undefined;

const PENDING_KEY = "events:unacknowledged";
const AREA_KEY = "events:area";
const PENDING_TTL_MS = 10_000;
const REVIEWED_TTL_MS = 30_000;

export function getCachedReviewedEvents(status: ReviewStatus): SafetyEvent[] | undefined {
  return peekQuery(reviewedKey(status));
}

export function getCachedPendingEvents(): SafetyEvent[] | undefined {
  return peekQuery(PENDING_KEY);
}

export function getCachedCameraEvents(cameraId: string): SafetyEvent[] | undefined {
  return peekQuery(cameraKey(cameraId));
}

export function getCachedEventDetail(eventId: number): EventDetail | undefined {
  return peekQuery(detailKey(eventId));
}

export function getCachedAreaEvents(): SafetyEvent[] | undefined {
  return peekQuery(AREA_KEY);
}

export async function loadAcknowledgedEvents(): Promise<SafetyEvent[]> {
  return loadReviewedEvents("acknowledged");
}

export async function loadReviewedEvents(status: ReviewStatus, options: {forceRefresh?: boolean} = {}): Promise<SafetyEvent[]> {
  const key = reviewedKey(status);
  const loader = async () => {
    const response = await fetch(
      apiUrl(`/events?status=${encodeURIComponent(status)}&limit=50`),
      {cache: "no-store", headers: authorizationHeaders()},
    );
    if (!response.ok) throw new Error(`Không thể tải nhật ký (HTTP ${response.status})`);
    return response.json() as Promise<SafetyEvent[]>;
  };
  return options.forceRefresh ? revalidateQuery(key, loader) : fetchQuery(key, loader, REVIEWED_TTL_MS);
}

export async function loadPendingEvents(options: {forceRefresh?: boolean} = {}): Promise<SafetyEvent[]> {
  const loader = async () => {
    const response = await fetch(apiUrl("/events?status=unacknowledged&limit=200"), {
      cache: "no-store",
      headers: authorizationHeaders(),
    });
    if (!response.ok) throw new Error(`Không thể tải cảnh báo chờ xử lý (HTTP ${response.status})`);
    return response.json() as Promise<SafetyEvent[]>;
  };
  return options.forceRefresh ? revalidateQuery(PENDING_KEY, loader) : fetchQuery(PENDING_KEY, loader, PENDING_TTL_MS);
}

export async function loadCameraEvents(cameraId: string, options: {forceRefresh?: boolean} = {}): Promise<SafetyEvent[]> {
  const key = cameraKey(cameraId);
  const loader = async () => {
    const response = await fetch(
      apiUrl(`/events?camera_id=${encodeURIComponent(cameraId)}&limit=50`),
      {cache: "no-store", headers: authorizationHeaders()},
    );
    if (!response.ok) throw new Error(`Không thể tải log Camera (HTTP ${response.status})`);
    return response.json() as Promise<SafetyEvent[]>;
  };
  return options.forceRefresh ? revalidateQuery(key, loader) : fetchQuery(key, loader, PENDING_TTL_MS);
}

export async function loadEventDetail(eventId: number, options: {forceRefresh?: boolean} = {}): Promise<EventDetail> {
  const key = detailKey(eventId);
  const loader = async () => {
    const response = await fetch(
      apiUrl(`/events/${encodeURIComponent(String(eventId))}`),
      {cache: "no-store", headers: authorizationHeaders()},
    );
    if (!response.ok) throw new Error(`Không thể tải chi tiết sự kiện (HTTP ${response.status})`);
    return response.json() as Promise<EventDetail>;
  };
  return options.forceRefresh ? revalidateQuery(key, loader) : fetchQuery(key, loader, REVIEWED_TTL_MS);
}

export async function saveReviewedEvent(payload: EventPayload): Promise<SafetyEvent> {
  const response = await fetch(apiUrl("/events"), {
    method: "POST",
    headers: {"Content-Type": "application/json", ...authorizationHeaders()},
    body: JSON.stringify(payload)
  });
  if (!response.ok) throw new Error(await readErrorMessage(response));
  const event = await response.json() as SafetyEvent;
  updateEventCaches(event);
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
  batch.events.forEach(updateEventCaches);
  publishSafetyEventUpdate(batch.events);
  return batch;
}

export async function loadAreaEvents(options: {forceRefresh?: boolean} = {}): Promise<SafetyEvent[]> {
  const loader = async () => {
    const response = await fetch(apiUrl("/events?limit=50"), {
      cache: "no-store",
      headers: authorizationHeaders(),
    });
    if (!response.ok) throw new Error(`Không thể tải nhật ký khu vực (HTTP ${response.status})`);
    return response.json() as Promise<SafetyEvent[]>;
  };
  return options.forceRefresh ? revalidateQuery(AREA_KEY, loader) : fetchQuery(AREA_KEY, loader, PENDING_TTL_MS);
}

export async function updateAreaEvent(eventId: number, status: "resolved" | "false_alarm"): Promise<SafetyEvent> {
  const response = await fetch(apiUrl(`/events/${eventId}`), {
    method: "PATCH",
    headers: {"Content-Type": "application/json", ...authorizationHeaders()},
    body: JSON.stringify({status}),
  });
  if (!response.ok) throw new Error(await readErrorMessage(response));
  const event = await response.json() as SafetyEvent;
  updateEventCaches(event);
  publishSafetyEventUpdate([event]);
  return event;
}

export function subscribeToSafetyEventUpdates(listener: (update: SafetyEventUpdate) => void): () => void {
  const notify = (update: SafetyEventUpdate) => {
    invalidateQueries("events:");
    invalidateQueries("statistics:");
    listener(update);
  };
  const handleWindowUpdate = (event: Event) => notify((event as CustomEvent<SafetyEventUpdate>).detail);
  const handleChannelUpdate = (event: MessageEvent<SafetyEventUpdate>) => notify(event.data);
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
  invalidateQueries("events:");
  invalidateQueries("statistics:");
  const update: SafetyEventUpdate = {
    eventIds: [...new Set(events.map(event => event.id))],
    cameraIds: [...new Set(events.map(event => event.camera_id))],
  };
  window.dispatchEvent(new CustomEvent<SafetyEventUpdate>(SAFETY_EVENT_UPDATE_NAME, {detail: update}));
  getEventUpdateChannel()?.postMessage(update);
}

function updateEventCaches(event: SafetyEvent): void {
  updateEventList(PENDING_KEY, event, PENDING_TTL_MS, item => item.status === "unacknowledged");
  updateEventList(cameraKey(event.camera_id), event, PENDING_TTL_MS, () => true);
  updateEventList(AREA_KEY, event, PENDING_TTL_MS, () => true);
  if (event.status === "acknowledged" || event.status === "false_alarm") {
    updateEventList(reviewedKey(event.status), event, REVIEWED_TTL_MS, () => true);
  }
  invalidateQueries(`events:detail:${event.id}`);
}

function updateEventList(key: string, event: SafetyEvent, ttlMs: number, include: (event: SafetyEvent) => boolean): void {
  const cached = peekQuery<SafetyEvent[]>(key);
  if (!cached) return;
  const remaining = cached.filter(item => item.id !== event.id);
  setQueryData(key, include(event) ? [event, ...remaining] : remaining, ttlMs);
}

function reviewedKey(status: ReviewStatus): string { return `events:${status}`; }
function cameraKey(cameraId: string): string { return `events:camera:${cameraId}`; }
function detailKey(eventId: number): string { return `events:detail:${eventId}`; }

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
