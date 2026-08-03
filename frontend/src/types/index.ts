export type MachineState = "running" | "stopped";
export type ReviewStatus = "acknowledged" | "false_alarm";

export interface ZonePoint {
  x: number;
  y: number;
}

export interface PersonDetection {
  bbox: [number, number, number, number];
  confidence: number;
  foot_point?: [number, number];
  inside_zone: boolean;
  safety_shirt: boolean;
}

export interface InferenceRule {
  person_inside_zone: boolean;
  machine_state: MachineState;
  safety_shirt_required: boolean;
}

export interface InferenceResult {
  type: "inference_result";
  frame_id: number;
  video_time: number;
  result: "normal" | "violate";
  review_required: boolean;
  people: PersonDetection[];
  snapshot_data?: string;
  rule: InferenceRule;
}

export interface SafetyEvent {
  id: number;
  timestamp: string;
  zone_id: string;
  camera_id: string;
  event_type: string;
  severity: string;
  status: ReviewStatus;
  acknowledged_by?: string | null;
  snapshot_path?: string | null;
  details?: {
    people?: PersonDetection[];
    video_timestamp_seconds?: number;
    review_result?: string;
  };
}

export interface EventPayload {
  zone_id: string;
  camera_id: string;
  event_type: string;
  severity: string;
  status: ReviewStatus;
  acknowledged_by: string;
  snapshot_data?: string;
  privacy_blurred: boolean;
  details: Record<string, unknown>;
}
