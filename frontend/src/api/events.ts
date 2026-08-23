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

export async function loadAcknowledgedEvents(): Promise<SafetyEvent[]> {
  return loadReviewedEvents("acknowledged");
}

export async function loadReviewedEvents(status: ReviewStatus): Promise<SafetyEvent[]> {
  const response = await fetch(
    apiUrl(`/events?status=${encodeURIComponent(status)}&limit=50`),
    {headers: authorizationHeaders()},
  );
  if (!response.ok) throw new Error(`Không thể tải nhật ký (HTTP ${response.status})`);
  return response.json() as Promise<SafetyEvent[]>;
}

export async function loadEventDetail(eventId: number): Promise<EventDetail> {
  const response = await fetch(
    apiUrl(`/events/${encodeURIComponent(String(eventId))}`),
    {headers: authorizationHeaders()},
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
  return response.json() as Promise<SafetyEvent>;
}

export async function saveReviewedEventBatch(payload: EventBatchPayload): Promise<EventBatchResponse> {
  const response = await fetch(apiUrl("/event-batches"), {
    method: "POST",
    headers: {"Content-Type": "application/json", ...authorizationHeaders()},
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await readErrorMessage(response));
  return response.json() as Promise<EventBatchResponse>;
}

export async function loadAreaEvents(): Promise<SafetyEvent[]> {
  const response = await fetch(apiUrl("/events?limit=50"), {headers: authorizationHeaders()});
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
  return response.json() as Promise<SafetyEvent>;
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
