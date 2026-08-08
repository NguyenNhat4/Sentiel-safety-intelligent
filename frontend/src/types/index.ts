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
  ppe: {
    helmet: PpeObservation;
    safety_glasses: PpeObservation;
    gloves: PpeObservation;
  };
  missing_required_ppe: Array<"helmet" | "safety_glasses" | "gloves">;
}

export interface PpeObservation {
  status: "present" | "missing" | "unknown";
  confidence: number | null;
}

export interface ModelDetection {
  class_id: number;
  class_name: string;
  bbox: [number, number, number, number];
  confidence: number;
  person_index: number | null;
}

export interface InferenceRule {
  person_inside_zone: boolean;
  machine_state: MachineState;
  safety_shirt_required: boolean;
  camera_id: string;
  zone_id: string;
  ppe_requirements: PpeRequirementUpdate;
  ppe_alert: boolean;
}

export interface InferenceResult {
  type: "inference_result";
  frame_id: number;
  video_time: number;
  result: "normal" | "violate";
  review_required: boolean;
  people: PersonDetection[];
  detections?: ModelDetection[];
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
  details: Record<string, unknown>;
}

export interface PpeRequirementUpdate {
  helmet_required: boolean;
  safety_glasses_required: boolean;
  gloves_required: boolean;
}

export interface PpeRequirement extends PpeRequirementUpdate {
  camera_id: string;
  zone_id: string;
  is_configured: boolean;
  updated_at: string | null;
}
