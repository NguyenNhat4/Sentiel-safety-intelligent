export type VisionWorkerTarget = "cpu" | "gpu";

const WORKER_BASES: Record<VisionWorkerTarget, string> = {
  cpu: "/vision-worker-cpu-api",
  gpu: "/vision-worker-gpu-api"
};
const CONTRACT_VERSION = "safety_vision_v1";
const REQUEST_TIMEOUT_MS = 30_000;

export type PpeStatus = "present" | "unknown";
export type DetectionClass = "hat" | "person" | "vest";

export interface VisionWorkerHealth {
  status: "healthy";
  contract_version: "safety_vision_v1";
  model_version: string;
}

export interface VisionWorkerDetection {
  class_id: 0 | 3 | 4;
  class_name: DetectionClass;
  bbox: [number, number, number, number];
  confidence: number;
  person_index: number | null;
}

export interface VisionWorkerInference {
  contract_version: "safety_vision_v1";
  request_id: string;
  model_version: string;
  canonical_people: Array<{
    bbox: [number, number, number, number];
    confidence: number;
    track_id: number;
  }>;
  people: Array<{
    hat: {status: PpeStatus; confidence: number | null};
    vest: {status: PpeStatus; confidence: number | null};
  }>;
  detections: VisionWorkerDetection[];
}

export interface InferVisionWorkerInput {
  image: Blob;
  fileName?: string;
  apiKey?: string;
  monitoringSessionId?: string;
  requestId?: string;
}

export interface LatencySummary {
  count: number;
  latest: number | null;
  mean: number | null;
  p50: number | null;
  p95: number | null;
  fps: number | null;
}

type Fetcher = typeof fetch;

export class VisionWorkerContractError extends Error {
  constructor(message = "Vision worker returned an invalid safety_vision_v1 response") {
    super(message);
    this.name = "VisionWorkerContractError";
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isBbox(value: unknown, format: "xywh" | "xyxy"): value is [number, number, number, number] {
  if (!Array.isArray(value) || value.length !== 4 || !value.every(isNumber)) return false;
  const [a, b, c, d] = value;
  return a >= 0 && b >= 0 && (format === "xywh" ? c > 0 && d > 0 : c > a && d > b);
}

function isConfidence(value: unknown): value is number {
  return isNumber(value) && value >= 0 && value <= 1;
}

function isObservation(value: unknown): boolean {
  return (
    isRecord(value) &&
    (value.status === "present" || value.status === "unknown") &&
    (value.confidence === null || isConfidence(value.confidence))
  );
}

function parseHealth(value: unknown): VisionWorkerHealth {
  if (
    !isRecord(value) ||
    value.status !== "healthy" ||
    value.contract_version !== CONTRACT_VERSION ||
    typeof value.model_version !== "string" ||
    value.model_version.length === 0
  ) {
    throw new VisionWorkerContractError("Vision worker health contract is invalid");
  }
  return value as unknown as VisionWorkerHealth;
}

function parseInference(value: unknown, expectedRequestId: string): VisionWorkerInference {
  if (
    !isRecord(value) ||
    value.contract_version !== CONTRACT_VERSION ||
    value.request_id !== expectedRequestId ||
    typeof value.model_version !== "string" ||
    value.model_version.length === 0 ||
    !Array.isArray(value.canonical_people) ||
    !Array.isArray(value.people) ||
    !Array.isArray(value.detections) ||
    value.canonical_people.length !== value.people.length
  ) {
    throw new VisionWorkerContractError();
  }

  const people = value.people;
  const validCanonicalPeople = value.canonical_people.every(
    (person) =>
      isRecord(person) &&
      isBbox(person.bbox, "xywh") &&
      isConfidence(person.confidence) &&
      Number.isInteger(person.track_id) &&
      (person.track_id as number) >= 1
  );
  const validPeople = people.every(
    (person) => isRecord(person) && isObservation(person.hat) && isObservation(person.vest)
  );
  const classMap = {0: "hat", 3: "person", 4: "vest"} as const;
  const validDetections = value.detections.every((detection) => {
    if (!isRecord(detection) || !(detection.class_id === 0 || detection.class_id === 3 || detection.class_id === 4)) {
      return false;
    }
    const personIndex = detection.person_index;
    return (
      detection.class_name === classMap[detection.class_id] &&
      isBbox(detection.bbox, "xyxy") &&
      isConfidence(detection.confidence) &&
      (personIndex === null ||
        (Number.isInteger(personIndex) &&
          (personIndex as number) >= 0 &&
          (personIndex as number) < people.length))
    );
  });

  if (!validCanonicalPeople || !validPeople || !validDetections) {
    throw new VisionWorkerContractError();
  }
  return value as unknown as VisionWorkerInference;
}

async function requireOk(response: Response): Promise<unknown> {
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new Error(`Vision worker returned HTTP ${response.status} without JSON`);
  }
  if (response.ok) return body;
  const detail = isRecord(body) && typeof body.detail === "string" ? body.detail : `HTTP ${response.status}`;
  throw new Error(detail);
}

export async function checkVisionWorker(
  target: VisionWorkerTarget,
  fetcher: Fetcher = fetch
): Promise<VisionWorkerHealth> {
  const response = await fetcher(`${WORKER_BASES[target]}/ping`, {
    headers: {Accept: "application/json"},
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS)
  });
  return parseHealth(await requireOk(response));
}

export async function inferVisionWorker(
  target: VisionWorkerTarget,
  input: InferVisionWorkerInput,
  fetcher: Fetcher = fetch
): Promise<VisionWorkerInference> {
  const requestId = input.requestId ?? crypto.randomUUID();
  const form = new FormData();
  form.set("request_id", requestId);
  const monitoringSessionId = input.monitoringSessionId?.trim();
  if (monitoringSessionId) form.set("monitoring_session_id", monitoringSessionId);
  form.set("image", input.image, input.fileName ?? (input.image instanceof File ? input.image.name : "frame.jpg"));

  const headers = new Headers({Accept: "application/json"});
  const apiKey = input.apiKey?.trim();
  if (apiKey) headers.set("Authorization", `Bearer ${apiKey}`);

  const response = await fetcher(`${WORKER_BASES[target]}/v1/infer`, {
    method: "POST",
    headers,
    body: form,
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS)
  });
  return parseInference(await requireOk(response), requestId);
}

function percentile(sortedValues: number[], quantile: number): number {
  return sortedValues[Math.min(sortedValues.length - 1, Math.ceil(sortedValues.length * quantile) - 1)];
}

export function summarizeLatencies(samples: number[]): LatencySummary {
  if (samples.length === 0) {
    return {count: 0, latest: null, mean: null, p50: null, p95: null, fps: null};
  }
  const sorted = [...samples].sort((left, right) => left - right);
  const mean = Math.round(samples.reduce((total, sample) => total + sample, 0) / samples.length);
  return {
    count: samples.length,
    latest: Math.round(samples[samples.length - 1]),
    mean,
    p50: Math.round(percentile(sorted, 0.5)),
    p95: Math.round(percentile(sorted, 0.95)),
    fps: Number((1000 / mean).toFixed(1))
  };
}
