import type {EventPayload, SafetyEvent} from "../types";
import {apiUrl} from "./config";

export async function loadAcknowledgedEvents(): Promise<SafetyEvent[]> {
  const response = await fetch(apiUrl("/events?status=acknowledged&limit=50"));
  if (!response.ok) throw new Error(`Không thể tải nhật ký (HTTP ${response.status})`);
  return response.json() as Promise<SafetyEvent[]>;
}

export async function saveReviewedEvent(payload: EventPayload): Promise<SafetyEvent> {
  const response = await fetch(apiUrl("/events"), {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });
  if (!response.ok) throw new Error(await readErrorMessage(response));
  return response.json() as Promise<SafetyEvent>;
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json() as {detail?: string};
    return body.detail || `Không thể lưu kết quả xác minh (HTTP ${response.status})`;
  } catch {
    return `Không thể lưu kết quả xác minh (HTTP ${response.status})`;
  }
}
