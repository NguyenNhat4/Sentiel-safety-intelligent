import type {PpeRequirement, PpeRequirementUpdate} from "../types";
import {apiUrl} from "./config";

export async function loadPpeRequirements(
  cameraId: string,
  zoneId: string
): Promise<PpeRequirement> {
  const response = await fetch(requirementUrl(cameraId, zoneId));
  if (!response.ok) throw new Error(await readErrorMessage(response, "Không thể tải cấu hình PPE"));
  return response.json() as Promise<PpeRequirement>;
}

export async function savePpeRequirements(
  cameraId: string,
  zoneId: string,
  requirement: PpeRequirementUpdate
): Promise<PpeRequirement> {
  const response = await fetch(requirementUrl(cameraId, zoneId), {
    method: "PUT",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(requirement)
  });
  if (!response.ok) throw new Error(await readErrorMessage(response, "Không thể lưu cấu hình PPE"));
  return response.json() as Promise<PpeRequirement>;
}

function requirementUrl(cameraId: string, zoneId: string): string {
  return apiUrl(`/ppe-requirements/${encodeURIComponent(cameraId)}/${encodeURIComponent(zoneId)}`);
}

async function readErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const body = await response.json() as {detail?: string};
    return body.detail || `${fallback} (HTTP ${response.status})`;
  } catch {
    return `${fallback} (HTTP ${response.status})`;
  }
}
