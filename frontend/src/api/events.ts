import type {EventBatchPayload, EventBatchResponse, EventPayload, SafetyEvent} from "../types";
import {apiUrl} from "./config";
import {getAccessToken} from "./auth";

export async function loadAcknowledgedEvents(): Promise<SafetyEvent[]> {
  const response = await fetch(apiUrl("/events?status=acknowledged&limit=50"), {headers: authHeaders()});
  if (!response.ok) throw new Error(`Không thể tải nhật ký (HTTP ${response.status})`);
  return response.json() as Promise<SafetyEvent[]>;
}

export async function saveReviewedEvent(payload: EventPayload): Promise<SafetyEvent> {
  const response = await fetch(apiUrl("/events"), {
    method: "POST",
    headers: {"Content-Type": "application/json", ...authHeaders()},
    body: JSON.stringify(payload)
  });
  if (!response.ok) throw new Error(await readErrorMessage(response));
  return response.json() as Promise<SafetyEvent>;
}

export async function saveReviewedEventBatch(payload: EventBatchPayload): Promise<EventBatchResponse> {
  const response = await fetch(apiUrl("/event-batches"), {
    method: "POST",
    headers: {"Content-Type": "application/json", ...authHeaders()},
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await readErrorMessage(response));
  return response.json() as Promise<EventBatchResponse>;
}

export async function loadAreaEvents(): Promise<SafetyEvent[]> {
  const response = await fetch(apiUrl("/events?limit=50"), {headers: authHeaders()});
  if (!response.ok) throw new Error(`KhÃ´ng thá»ƒ táº£i nháº­t kÃ½ khu vá»±c (HTTP ${response.status})`);
  return response.json() as Promise<SafetyEvent[]>;
}

export async function updateAreaEvent(eventId: number, status: "resolved" | "false_alarm"): Promise<SafetyEvent> {
  const response = await fetch(apiUrl(`/events/${eventId}`), {
    method: "PATCH",
    headers: {"Content-Type": "application/json", ...authHeaders()},
    body: JSON.stringify({status}),
  });
  if (!response.ok) throw new Error(await readErrorMessage(response));
  return response.json() as Promise<SafetyEvent>;
}

function authHeaders(): HeadersInit {
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
